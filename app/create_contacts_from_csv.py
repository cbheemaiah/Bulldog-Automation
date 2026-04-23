import json
import sys
import os
import pandas as pd
from datetime import datetime
import glob
import logging
import chardet
import argparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import AppConfig
from app.mautic_client import MauticClient
from app.contact_client import ContactClient
from dotenv import load_dotenv

load_dotenv()

def split_name(full_name: str):
    s = (full_name or "").strip()
    if not s:
        return ("Valued", "Contact")
    parts = s.split()
    return parts[0], (" ".join(parts[1:]) if len(parts) > 1 else "")

def main():
    # 0. Parse CLI Arguments
    parser = argparse.ArgumentParser(description="Bulldog: Import contacts from CSV to Mautic.")
    parser.add_argument("--file", type=str, help="Path to a specific CSV file to process (bypasses latest/today check).")
    parser.add_argument("--day", type=int, help="Override the current 'Bulldog Day' and save it to state.")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt (useful for CRON).")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logger = logging.getLogger(__name__)

    logger.info("Starting Bulldog contact creation process...")

    try:
        cfg = AppConfig.load("config.json")
        logger.info("Configuration loaded successfully.")
    except Exception as e:
        logger.critical(f"Failed to load configuration: {e}")
        return

    segment_id = cfg.segment_id
    test_tag_name = cfg.test_tag_name

    if not segment_id:
        logger.error("Aborting: 'segment_id' not found in config.")
        return
    if not test_tag_name:
        logger.error("Aborting: 'test_tag_name' not found in config.")
        return

    # 1. Find the CSV to process
    download_path = None
    manual_file_override = False

    if args.file:
        if os.path.exists(args.file):
            download_path = args.file
            manual_file_override = True
            logger.info(f"Using manual file override: {download_path}")
        else:
            logger.error(f"Aborting: Specified file does not exist: {args.file}")
            return
    else:
        # Latest import logic (CRON mode)
        search_pattern = os.path.join(cfg.input_dir, "bulldog_import_*.csv")
        files = glob.glob(search_pattern)
        if files:
            download_path = max(files, key=os.path.getctime)
            logger.info(f"Found latest CSV file: {download_path}")

    if not download_path or not os.path.exists(download_path) or os.path.getsize(download_path) == 0:
        logger.error("Aborting: No valid CSV file found to process.")
        return

    # Ensure the CSV is from today to prevent reprocessing old data if fetch failed (Only if NOT manual)
    if not manual_file_override:
        today_compact = datetime.now().strftime("%Y%m%d")
        if today_compact not in os.path.basename(download_path):
            logger.error(f"Aborting: The latest CSV ({os.path.basename(download_path)}) is not from today ({today_compact}). Check if fetch_bulldog_csv.py ran successfully.")
            return
    else:
        logger.info("Skipping today-date validation for manual file import.")

    logger.info(f"Processing CSV: {download_path}")

    # Validate CSV format before contacting Mautic
    try:
        with open(download_path, "rb") as f:
            raw_data = f.read()
        result = chardet.detect(raw_data)
        encoding = result["encoding"]
        logger.info(f"Detected encoding: {encoding} (confidence: {result['confidence']})")

        df = pd.read_csv(download_path, encoding=encoding)
        logger.info(f"CSV loaded. Rows: {len(df)}")
    except Exception as e:
        logger.error(f"Aborting: Invalid CSV format in {download_path}. Error: {e}")
        return

    if df.empty:
        logger.error("Aborting: CSV contains no data.")
        return

    if len(df.columns) < 1:
        logger.error("Aborting: CSV must have at least 1 column (Email).")
        return

    if hasattr(cfg, 'limit') and cfg.limit and cfg.limit > 0:
        logger.info(f"Applying limit: {cfg.limit}")
        df = df.head(cfg.limit)

    logger.info("Initializing Mautic client...")
    mautic = MauticClient(cfg.base_url, token_file=cfg.token_file, timeout_seconds=cfg.timeout_seconds)
    contacts = ContactClient(mautic, cfg.create_endpoint)

    # 1. Load Local History
    history_list = []
    if os.path.exists(cfg.history_file):
        try:
            with open(cfg.history_file, "r", encoding="utf-8") as f:
                history_list = json.load(f)
            logger.info(f"Loaded {len(history_list)} items from history.")
        except Exception as e:
            logger.warning(f"Error loading history file: {e}")

    new_history_items = []

    # Helper to make requests using MauticClient
    def mautic_request(method, endpoint, payload=None, params=None):
        return mautic.request_json(method, endpoint, json_body=payload, params=params)

    # 3. Handle Day State and persistence
    state_file = os.path.join(cfg.output_dir, "bulldog_state.json")
    current_day = 0
    last_run_date = ""
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Load existing state
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                state = json.load(f)
                current_day = state.get("day", 0)
                last_run_date = state.get("last_run_date", "")
        except Exception:
            pass

    # Apply Overrides or Logic
    if args.day is not None:
        logger.info(f"Applying manual Day override: Setting day to {args.day}")
        current_day = args.day
        last_run_date = today_str # Mark today as run
        # Save immediately
        with open(state_file, "w") as f:
            json.dump({"day": current_day, "last_run_date": last_run_date}, f)
    elif last_run_date != today_str:
        logger.info("New day detected. Incrementing Bulldog Day counter.")
        current_day += 1
        last_run_date = today_str
        with open(state_file, "w") as f:
            json.dump({"day": current_day, "last_run_date": last_run_date}, f)

    logger.info(f"Current Day State: {current_day} (Target Date: {last_run_date})")

    new_tag_name = f"Digital-Bulldog-Day-{current_day}"
    new_tag_id = None

    logger.info(f"Creating tag: {new_tag_name}")
    try:
        tag_payload = {"tag": new_tag_name, "description": "Auto-generated by Bulldog"}
        res = mautic_request("POST", "api/tags/new", payload=tag_payload)
        
        # Handle response (requests.Response or dict)
        data = res.json() if hasattr(res, 'json') else res
        new_tag_id = data.get("tag", {}).get("id")
    except Exception as e:
        logger.warning(f"Tag creation failed (tag might exist). Error: {e}")
        new_tag_id = None

    # Fallback: If creation failed, search for the tag by name
    if not new_tag_id:
        logger.info(f"Searching for existing tag: {new_tag_name}")
        try:
            res = mautic_request("GET", "api/tags", params={"search": new_tag_name})
            data = res.json() if hasattr(res, 'json') else res
            tags = data.get("tags", {})
            
            # Mautic returns tags as a dict keyed by ID { "123": {...} } or list
            if isinstance(tags, dict):
                for t_id, t_data in tags.items():
                    if t_data.get("tag") == new_tag_name:
                        new_tag_id = t_data.get("id")
                        break
        except Exception as e:
            logger.error(f"Failed to search for existing tag: {e}")

    if not new_tag_id:
        logger.error("Aborting: Failed to retrieve tag ID (could not create or find).")
        return

    logger.info(f"Using Tag ID: {new_tag_id}")

    # 3.1 Record tag for cleanup tracking
    tags_file = os.path.join(cfg.output_dir, "created_tags.json")
    os.makedirs(cfg.output_dir, exist_ok=True)
    existing_tags = []
    if os.path.exists(tags_file):
        try:
            with open(tags_file, "r") as f:
                existing_tags = json.load(f)
        except Exception:
            pass
    
    # Check if this tag ID is already tracked
    if not any(t.get("id") == new_tag_id for t in existing_tags):
        existing_tags.append({"id": new_tag_id, "name": new_tag_name})
        with open(tags_file, "w") as f:
            json.dump(existing_tags, f, indent=2)
        logger.info(f"Recorded tag '{new_tag_name}' (ID: {new_tag_id}) in cleanup tracker.")

    # Build set of emails already processed with this tag ID to prevent duplicates
    # within the same run or if the tag ID is reused.
    processed_with_current_tag = set()
    for item in history_list:
        h_tag = item.get("tag_id")
        h_email = item.get("email")
        if h_tag and h_email and str(h_tag) == str(new_tag_id):
            processed_with_current_tag.add(h_email.strip().lower())

    # 4. Update segments filter tag to the new tag ID
    logger.info(f"Updating segment {segment_id} filter to tag ID {new_tag_id}")
    try:
        seg_payload = {
            "filters": [
                {
                    "glue": "and",
                    "field": "tags",
                    "object": "lead",
                    "type": "tags",
                    "operator": "in",
                    "properties": {
                        "filter": [new_tag_id]
                    }
                },
                {
                    "glue": "and",
                    "field": "tags",
                    "object": "lead",
                    "type": "tags",
                    "operator": "!in",
                    "properties": {
                        "filter": [cfg.exclude_tag_id]
                    }
                },
                {
                    "glue": "and",
                    "field": "tags",
                    "object": "lead",
                    "type": "tags",
                    "operator": "in",
                    "properties": {
                        "filter": [cfg.default_include_tag_id]
                    }
                }
            ]
        }
        mautic_request("PATCH", f"api/segments/{segment_id}/edit", seg_payload)
        logger.info("Segment updated successfully.")
    except Exception as e:
        logger.error(f"Aborting: Error updating segment: {e}")
        return

    # 5. User Confirmation
    if not args.yes:
        print("\n" + "="*50)
        print("PROCEED WITH CONTACT CREATION?")
        print(f"Bulldog Tag: {new_tag_name}")
        print(f"Test Tag:    {test_tag_name}")
        print(f"Segment ID:  {segment_id}")
        print(f"CSV File:    {download_path}")
        print(f"Row Limit:   {cfg.limit if cfg.limit > 0 else 'None'}")
        print("="*50 + "\n")
        
        try:
            confirm = input("Confirm processing? (y/n): ").strip().lower()
            if confirm != 'y':
                logger.info("Aborting by user request.")
                return
        except EOFError:
            logger.error("No interactive terminal detected and --yes flag was not provided. Aborting.")
            return

    # 6. Process Contacts (Retries + CSV)
    
    # Load previous failures
    previous_failures = []
    if os.path.exists(cfg.failed_creation_file):
        try:
            with open(cfg.failed_creation_file, "r", encoding="utf-8") as f:
                previous_failures = json.load(f)
            logger.info(f"Loaded {len(previous_failures)} previous failures.")
        except Exception:
            pass

    current_failures = {} # Key by email to avoid duplicates
    success_count = 0

    def process_contact(email, first, last, rotation_group, source_desc):
        email_key = email.lower()
        if email_key in processed_with_current_tag:
            logger.info(f"Skipping {email} (already processed with tag {new_tag_id})")
            return False

        payload = {
            "email": email,
            "firstname": first,
            "lastname": last,
            "tags": [new_tag_name, test_tag_name, cfg.default_include_tag_name, f"-{cfg.exclude_tag_name}"],
            "rotationgroup": rotation_group
        }

        try:
            cid = contacts.create_contact(payload)
            item = {
                "id": cid, 
                "email": email, 
                "firstname": first, 
                "lastname": last, 
                "rotationgroup": rotation_group,
                "tag_id": new_tag_id,
                "created_at": datetime.now().isoformat()
            }
            
            new_history_items.append(item)
            processed_with_current_tag.add(email_key)

            # Remove from current_failures if it was there (e.g. from retry phase or previous duplicate row)
            if email_key in current_failures:
                del current_failures[email_key]
            
            logger.info(f"[CREATE] OK id={cid} email={email} ({source_desc})")
            return True
        except Exception as e:
            logger.error(f"[CREATE] FAIL email={email} ({source_desc}): {e}")
            current_failures[email_key] = {
                "email": email,
                "firstname": first,
                "lastname": last,
                "rotationgroup": rotation_group,
                "failed_at": datetime.now().isoformat(),
                "error": str(e)
            }
            return False

    try:
        # 6.1 Retry previously failed contacts
        if previous_failures:
            logger.info(f"Retrying {len(previous_failures)} previously failed contacts...")
            for fail in previous_failures:
                if not fail.get("email"): 
                    continue
                if process_contact(fail["email"], fail.get("firstname", ""), fail.get("lastname", ""), fail.get("rotationgroup", 1), "retry"):
                    success_count += 1

        # 6.2 Iterate through the new CSV rows
        logger.info(f"Starting processing of {len(df)} rows from CSV...")
        for idx, row in df.iterrows():
            email_raw = row.iloc[0] if len(row) > 0 else None
            name_cell = row.iloc[1] if len(row) > 1 else None

            if pd.isna(email_raw) or not str(email_raw).strip():
                logger.warning(f"Skipping row {idx}: Missing or empty email.")
                continue

            email = str(email_raw).strip()
            full_name = "" if pd.isna(name_cell) else str(name_cell).strip()
            first, last = split_name(full_name)
            
            rotation_group = idx % 4 + 1
            
            if process_contact(email, first, last, rotation_group, "csv"):
                success_count += 1

    finally:
        # 7. Save Failures (overwrite file with current state of failures)
        try:
            with open(cfg.failed_creation_file, "w", encoding="utf-8") as f:
                json.dump(list(current_failures.values()), f, indent=2)
            if current_failures:
                logger.info(f"Saved {len(current_failures)} failed contacts to {cfg.failed_creation_file}")
        except Exception as e:
            logger.error(f"Error saving failed creations: {e}")

        # Save History
        if new_history_items:
            full_history = []
            if os.path.exists(cfg.history_file):
                try:
                    with open(cfg.history_file, "r", encoding="utf-8") as f:
                        full_history = json.load(f)
                except Exception:
                    pass
            
            full_history.extend(new_history_items)
            os.makedirs(os.path.dirname(cfg.history_file), exist_ok=True)
            with open(cfg.history_file, "w", encoding="utf-8") as f:
                json.dump(full_history, f, indent=2)
            logger.info(f"Added {len(new_history_items)} new contacts to {cfg.history_file}")

    logger.info(f"Processed {success_count} contacts successfully.")

if __name__ == "__main__":
    main()