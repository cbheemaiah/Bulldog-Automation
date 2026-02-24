import json
import sys
import os
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import AppConfig
from app.mautic_client import MauticClient

def main():
    load_dotenv()

    # Load configuration (assumes running from project root)
    try:
        cfg = AppConfig.load("config.json")
    except Exception as e:
        print(f"Error loading config: {e}")
        return

    history = []
    if os.path.exists(cfg.history_file):
        # Load history
        with open(cfg.history_file, "r", encoding="utf-8") as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                history = []
    else:
        print(f"No history file found at {cfg.history_file}")

    if history:
        print(f"Found {len(history)} contacts in history. Deleting...")

        mautic = MauticClient(cfg.base_url, cfg.token_file, cfg.timeout_seconds)
        remaining_history = []

        for contact in history:
            cid = contact.get("id")
            email = contact.get("email")

            if not cid:
                continue

            # Endpoint as requested: DELETE /contacts/ID/delete
            # Note: If this custom endpoint fails, the standard Mautic API is DELETE /api/contacts/{id}
            endpoint = f"api/contacts/{cid}/delete"

            try:
                mautic.request_json("DELETE", endpoint)
                print(f"[DELETE] OK id={cid} email={email}")
            except Exception as e:
                # If 404, it implies the contact is already deleted.
                if "404" in str(e):
                    print(f"[DELETE] Not Found (already deleted?) id={cid} email={email}")
                else:
                    print(f"[DELETE] FAIL id={cid} email={email}: {e}")
                    remaining_history.append(contact)
    else:
        print("No contacts in history to delete.")

    # Reset all state files
    state_files = [
        cfg.history_file,
        cfg.failed_creation_file,
        os.path.join(cfg.output_dir, "bulldog_state.json")
    ]

    for fpath in state_files:
        if os.path.exists(fpath):
            os.remove(fpath)
            print(f"Deleted state file: {fpath}")

    # Clean up input directory (data folder)
    if os.path.exists(cfg.input_dir):
        print(f"Cleaning up input directory: {cfg.input_dir}")
        for filename in os.listdir(cfg.input_dir):
            file_path = os.path.join(cfg.input_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")

    print("Cleanup complete. All contacts deleted and local state reset.")

if __name__ == "__main__":
    main()
