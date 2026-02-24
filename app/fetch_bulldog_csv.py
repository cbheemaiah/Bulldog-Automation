import sys
import os
import requests
import glob
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import AppConfig

def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logger = logging.getLogger(__name__)

    load_dotenv()
    try:
        cfg = AppConfig.load("config.json")
    except Exception as e:
        logger.critical(f"Error loading config: {e}")
        return

    if not cfg.bulldog_api_url:
        logger.error("Aborting: 'bulldog_api_url' not found in config.")
        return

    today_str = datetime.now().strftime("%Y%m%d")
    search_pattern = os.path.join(cfg.input_dir, f"bulldog_import_{today_str}_*.csv")
    if glob.glob(search_pattern):
        logger.warning(f"Aborting: A CSV file for today ({today_str}) already exists.")
        return

    logger.info(f"Downloading CSV from {cfg.bulldog_api_url}...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    download_path = os.path.join(cfg.input_dir, f"bulldog_import_{timestamp}.csv")

    try:
        resp = requests.get(cfg.bulldog_api_url, timeout=60)
        resp.raise_for_status()
        
        # Validate content is not empty
        if not resp.content:
            logger.error("Aborting: Downloaded content is empty.")
            return

        os.makedirs(os.path.dirname(download_path), exist_ok=True)
        with open(download_path, "wb") as f:
            f.write(resp.content)
            
        if os.path.getsize(download_path) == 0:
            logger.error("Aborting: File created but is empty.")
            os.remove(download_path)
            return
            
        logger.info(f"CSV downloaded and validated: {download_path}")
    except Exception as e:
        logger.error(f"Aborting: Failed to download CSV: {e}")

if __name__ == "__main__":
    main()