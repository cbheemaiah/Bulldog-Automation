import os
import sys
import logging
from dotenv import load_dotenv
from app.mautic_client import MauticClient

# Add src to path if running directly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging for the script
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    load_dotenv()

    base_url = os.getenv("MAUTIC_BASE_URL")
    client_id = os.getenv("MAUTIC_CLIENT_ID")
    client_secret = os.getenv("MAUTIC_CLIENT_SECRET")
    callback_url = os.getenv("MAUTIC_CALLBACK_URL")

    # Enforce Client Credentials
    grant_type = os.getenv("MAUTIC_GRANT_TYPE", "client_credentials")

    if not all([base_url, client_id, client_secret, callback_url]):
        logger.error("Missing required environment variables.")
        print(
            "Please ensure MAUTIC_BASE_URL, MAUTIC_CLIENT_ID, MAUTIC_CLIENT_SECRET, and MAUTIC_CALLBACK_URL are set in .env"
        )
        return

    try:
        # Pass the grant_type to the client
        client = MauticClient(
            base_url,
            client_id,
            client_secret,
            callback_url,
            grant_type=grant_type,
            token_file="mautic_tokens.json",
        )
    except Exception as e:
        logger.error(f"Failed to initialize client: {e}")
        return

    print(f"\n--- Mautic OAuth Verification ({grant_type}) ---")

    if grant_type != "client_credentials":
        print(
            f"WARNING: The configured grant_type '{grant_type}' requires manual/browser interaction."
        )
        print("This script has been updated to support headless verification only.")
        print("Please set MAUTIC_GRANT_TYPE=client_credentials in your .env file.")
        return

    print("Mode: Headless (Client Credentials)")
    print("Attempting to fetch token directly...")

    # TODO: Requires retrying the token fetch in case of transient errors, but for simplicity, we will just attempt once here.
    try:
        token = client.fetch_client_credentials_token()
        if token:
            print(f"\n✅ Success! Token acquired: {token[:10]}...")
            print("Tokens have been saved to mautic_tokens.json.")
        else:
            print("\n❌ Failed to acquire token.")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()