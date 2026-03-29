import json
import sys
import os
import argparse
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import AppConfig
from app.mautic_client import MauticClient

def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Bulldog: Targeted deletion of contacts and tags.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--day", type=int, help="Target a specific Bulldog Day (e.g. 1)")
    group.add_argument("--tag_id", type=int, help="Target a specific Mautic Tag ID")
    args = parser.parse_args()

    try:
        cfg = AppConfig.load("config.json")
    except Exception as e:
        print(f"Error loading config: {e}")
        return

    mautic = MauticClient(cfg.base_url, cfg.token_file, cfg.timeout_seconds)

    # 1. Resolve Tag ID
    target_tag_id = None
    target_tag_name = None

    tags_file = os.path.join(cfg.output_dir, "created_tags.json")
    existing_tags = []
    if os.path.exists(tags_file):
        try:
            with open(tags_file, "r") as f:
                existing_tags = json.load(f)
        except Exception:
            pass

    if args.day:
        target_name = f"Digital-Bulldog-Day-{args.day}"
        for t in existing_tags:
            if t.get("name") == target_name:
                target_tag_id = t.get("id")
                target_tag_name = t.get("name")
                break
        if not target_tag_id:
            print(f"Error: Could not find tracking info for Day {args.day} (Tag: {target_name})")
            return
    else:
        target_tag_id = args.tag_id
        for t in existing_tags:
            if t.get("id") == target_tag_id:
                target_tag_name = t.get("name")
                break

    if not target_tag_id:
        print(f"Error: Tag ID {args.tag_id} not found in tracking records.")
        return

    print(f"Targeting Tag ID: {target_tag_id} (Name: {target_tag_name or 'Unknown'})")

    # 2. Identify and Delete Contacts
    history = []
    if os.path.exists(cfg.history_file):
        with open(cfg.history_file, "r", encoding="utf-8") as f:
            try:
                history = json.load(f)
            except Exception:
                pass

    contacts_to_delete = [c for c in history if str(c.get("tag_id")) == str(target_tag_id)]
    remaining_history = [c for c in history if str(c.get("tag_id")) != str(target_tag_id)]

    if contacts_to_delete:
        print(f"Found {len(contacts_to_delete)} contacts matching this tag. Deleting from Mautic...")
        for contact in contacts_to_delete:
            cid = contact.get("id")
            email = contact.get("email")
            if not cid: continue

            # Pattern: DELETE api/contacts/{id}/delete
            endpoint = f"api/contacts/{cid}/delete"
            try:
                mautic.request_json("DELETE", endpoint)
                print(f"[DELETE] OK id={cid} email={email}")
            except Exception as e:
                if "404" in str(e):
                    print(f"[DELETE] Not Found (already deleted?) id={cid}")
                else:
                    print(f"[DELETE] FAIL id={cid}: {e}")
    else:
        print("No contacts found in history for this tag.")

    # 3. Delete Tag
    print(f"Deleting tag {target_tag_id} from Mautic...")
    tag_endpoint = f"api/tags/{target_tag_id}/delete"
    try:
        mautic.request_json("DELETE", tag_endpoint)
        print(f"[TAG DELETE] OK id={target_tag_id}")
    except Exception as e:
        if "404" in str(e):
            print(f"[TAG DELETE] Not Found (already deleted?) id={target_tag_id}")
        else:
            print(f"[TAG DELETE] FAIL id={target_tag_id}: {e}")

    # 4. Update Local State
    # Save History
    with open(cfg.history_file, "w", encoding="utf-8") as f:
        json.dump(remaining_history, f, indent=2)
    print(f"Updated {cfg.history_file} (Removed {len(contacts_to_delete)} entries)")

    # Save Tags
    remaining_tags = [t for t in existing_tags if str(t.get("id")) != str(target_tag_id)]
    with open(tags_file, "w") as f:
        json.dump(remaining_tags, f, indent=2)
    print(f"Updated {tags_file} (Removed tag {target_tag_id})")

    print(f"\nTargeted cleanup complete for Tag ID {target_tag_id}.")

if __name__ == "__main__":
    main()
