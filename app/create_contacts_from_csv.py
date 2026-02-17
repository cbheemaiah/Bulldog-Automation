import json
import sys
import os
import pandas as pd

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

def get_tag_names(contact_data):
    """
    Helper to extract tag names from Mautic contact response.
    Handles both list-of-dicts (standard) and dict-of-dicts (legacy) formats.
    """
    raw_tags = contact_data.get("tags") or []
    tags = set()
    if isinstance(raw_tags, list):
        for t in raw_tags:
            if isinstance(t, dict):
                val = t.get("tag")
                if val:
                    tags.add(val)
            elif isinstance(t, str):
                tags.add(t)
    elif isinstance(raw_tags, dict):
        for t in raw_tags.values():
            if isinstance(t, dict):
                val = t.get("tag")
                if val:
                    tags.add(val)
    return tags

def main():
    cfg = AppConfig.load("config.json")

    mautic = MauticClient(cfg.base_url, token_file=cfg.token_file, timeout_seconds=cfg.timeout_seconds)
    contacts = ContactClient(mautic, cfg.create_endpoint, cfg.update_endpoint_template)

    df = pd.read_csv(cfg.csv_path)
    if cfg.limit and cfg.limit > 0:
        df = df.head(cfg.limit)

    # 1. Load Local History for Existence Check
    history_map = {}
    if os.path.exists(cfg.history_file):
        try:
            with open(cfg.history_file, "r", encoding="utf-8") as f:
                history_list = json.load(f)
                for item in history_list:
                    if item.get("email"):
                        history_map[item["email"].strip().lower()] = item
        except Exception as e:
            print(f"Error loading history file: {e}")

    # 2. Load Pending Updates (to append to)
    pending_updates = []
    if os.path.exists(cfg.pending_update_file):
        try:
            with open(cfg.pending_update_file, "r", encoding="utf-8") as f:
                pending_updates = json.load(f)
        except Exception:
            pass

    new_history_items = []
    new_pending_items = []

    for idx, row in df.iterrows():
        email_raw = row.iloc[0] if len(row) > 0 else None
        name_cell = row.iloc[1] if len(row) > 1 else None

        if pd.isna(email_raw) or not str(email_raw).strip():
            print(f"Row {idx}: missing email")
            continue

        email = str(email_raw).strip()
        email_key = email.lower()
        full_name = "" if pd.isna(name_cell) else str(name_cell).strip()
        first, last = split_name(full_name)

        # --- SCENARIO A: Contact Exists Locally ---
        if email_key in history_map:
            existing_info = history_map[email_key]
            cid = existing_info.get("id")
            
            if not cid:
                continue

            try:
                # Fetch current tags from Mautic
                remote_contact = contacts.get_contact_by_id(cid)
                if not remote_contact:
                    print(f"Row {idx}: Contact {cid} in history but not found in Mautic (404). Skipping.")
                    continue

                current_tags = get_tag_names(remote_contact)
                has_test = "Test" in current_tags
                has_warmup = "warmup_campaign" in current_tags

                if has_test and not has_warmup:
                    print(f"Row {idx}: Contact {cid} has 'Test' only. Swapping tags...")
                    contacts.update_contact_tags(cid, ["-Test", "warmup_campaign"])
                    
                    # Add to pending updates list
                    new_pending_items.append(existing_info)
                    print(f"[UPDATE] OK id={cid} email={email} (Test -> warmup_campaign)")
                
                elif has_warmup:
                    print(f"Row {idx}: Contact {cid} already has 'warmup_campaign'. Ignoring.")
                
                else:
                    print(f"Row {idx}: Contact {cid} has tags {current_tags}. No action required.")

            except Exception as e:
                print(f"Row {idx}: Error checking contact {cid}: {e}")
            
            continue

        # --- SCENARIO B: Contact Does Not Exist Locally ---
        payload = {
            "email": email,
            "firstname": first,
            "lastname": last,
            "tags": cfg.default_create_tags,
        }

        try:
            cid = contacts.create_contact(payload)
            item = {"id": cid, "email": email, "firstname": first, "lastname": last}
            
            new_history_items.append(item)
            new_pending_items.append(item)
            
            # Update in-memory map to handle duplicates within the same CSV
            history_map[email_key] = item
            
            print(f"[CREATE] OK id={cid} email={email}")
        except Exception as e:
            print(f"[CREATE] FAIL row={idx} email={email}: {e}")

    # Save Pending Updates
    if new_pending_items:
        pending_updates.extend(new_pending_items)
        os.makedirs(os.path.dirname(cfg.pending_update_file), exist_ok=True)
        with open(cfg.pending_update_file, "w", encoding="utf-8") as f:
            json.dump(pending_updates, f, indent=2)
        print(f"\nAdded {len(new_pending_items)} contacts to {cfg.pending_update_file}")

    # Save History
    history = []
    if os.path.exists(cfg.history_file):
        try:
            with open(cfg.history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            pass
    
    if new_history_items:
        history.extend(new_history_items)
        os.makedirs(os.path.dirname(cfg.history_file), exist_ok=True)
        with open(cfg.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
        print(f"Added {len(new_history_items)} new contacts to {cfg.history_file}")

if __name__ == "__main__":
    main()