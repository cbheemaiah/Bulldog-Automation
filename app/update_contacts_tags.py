import json
import sys
import os
import time

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import AppConfig
from app.mautic_client import MauticClient
from dotenv import load_dotenv

load_dotenv()

def main():
    # Load configuration
    try:
        cfg = AppConfig.load("config.json")
    except Exception as e:
        print(f"Error loading config: {e}")
        return

    # Check if the contacts file exists
    if not os.path.exists(cfg.pending_update_file):
        print(f"No pending updates file found at {cfg.pending_update_file}")
        return

    # Load contacts to update
    with open(cfg.pending_update_file, "r", encoding="utf-8") as f:
        try:
            contacts = json.load(f)
        except json.JSONDecodeError:
            contacts = []

    if not contacts:
        print("No contacts pending update.")
        return

    print(f"Found {len(contacts)} contacts to update.")

    mautic = MauticClient(cfg.base_url, cfg.token_file, cfg.timeout_seconds)
    
    remaining_contacts = []
    successful_contacts = []
    updated_count = 0

    for contact in contacts:
        cid = contact.get("id")
        email = contact.get("email")
        
        if not cid:
            continue

        # Construct endpoint: api/contacts/{id}/edit
        endpoint = cfg.update_endpoint_template.replace("{id}", str(cid))
        payload = {"tags": cfg.update_tags}

        try:
            mautic.request_json("PATCH", endpoint, json_body=payload)
            print(f"[UPDATE] OK id={cid} email={email}")
            updated_count += 1
            
            contact["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            successful_contacts.append(contact)
        except Exception as e:
            print(f"[UPDATE] FAIL id={cid} email={email}: {e}")
            remaining_contacts.append(contact)

    # Overwrite the file with only the contacts that FAILED (or empty list if all good)
    os.makedirs(os.path.dirname(cfg.pending_update_file), exist_ok=True) # Ensure directory exists
    with open(cfg.pending_update_file, "w", encoding="utf-8") as f:
        json.dump(remaining_contacts, f, indent=2)

    # Append successful updates to the log file
    if successful_contacts:
        log_data = []
        if os.path.exists(cfg.update_log_file):
            try:
                with open(cfg.update_log_file, "r", encoding="utf-8") as f:
                    log_data = json.load(f)
            except Exception:
                pass
        log_data.extend(successful_contacts)
        
        with open(cfg.update_log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2)

    print(f"\nSummary: Updated {updated_count}. Remaining {len(remaining_contacts)} in {cfg.pending_update_file}.")
    if successful_contacts:
        print(f"Logged {len(successful_contacts)} successes to {cfg.update_log_file}")

if __name__ == "__main__":
    main()