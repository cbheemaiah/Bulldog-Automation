# Setup Instructions for Bulldog Automation

Follow these steps to set up your environment and run the Bulldog automation scripts.

## 1. Prerequisites

- **Python 3.13+**: Ensure you have Python installed.
- **uv**: This project uses `uv` for fast, reliable dependency management.
  - Install it via: `curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS/Linux)
  - Or see the [official uv docs](https://github.com/astral-sh/uv) for other platforms.
- **Mautic Instance**: You need an active Mautic instance with API access.

## 2. Initial Setup

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/cbheemaiah/Bulldog-Automation.git
    cd Bulldog-Automation
    ```

2.  **Install Dependencies**:
    ```bash
    uv sync
    ```

3.  **Environment Variables**:
    Create a `.env` file in the root directory:
    ```ini
    MAUTIC_CLIENT_ID=your_client_id
    MAUTIC_CLIENT_SECRET=your_client_secret
    BULLDOG_API_URL=https://your-source-url.com/contacts.csv
    ```

## 3. Mautic API Configuration

1.  Log in to your Mautic instance.
2.  Go to **Settings (Gear Icon) -> API Settings**.
3.  Ensure **API enabled?** is set to `Yes`.
4.  Ensure **OAuth2** is enabled.
5.  Go to **API Credentials** and create a new set of credentials.
6.  Copy the **Client ID** and **Client Secret** into your `.env` file.

## 4. Local Configuration

Review and update `config.json` in the root directory:

- `base_url`: Your Mautic instance URL (e.g., `https://mautic.example.com/`).
- `segment_id`: The ID of the Mautic segment you want to update automatically.
- `limit`: Set to `0` for full runs, or a small number (e.g., `5`) for initial testing.

## 5. Running the Pipeline

### Automatic Workflow 
The most common way to run Bulldog is via the daily import script:
```bash
./run_daily_import.sh
```

### Individual Steps - What the above command does
1.  **Fetch the CSV**:
    ```bash
    uv run app/fetch_bulldog_csv.py
    ```
2.  **Process and Import**:
    ```bash
    uv run app/create_contacts_from_csv.py
    ```

### Manual Overrides
If you need to process a specific file or force a specific Day:
```bash
uv run app/create_contacts_from_csv.py --file data/my_custom_import.csv --day 5
```

## 6. Cleanup and Reset - if needed after testing
If you are testing and want to wipe all contacts and tags created by Bulldog:
```bash
uv run scripts/delete_created_contacts.py
```

---
Success and history files are maintained in the `generated/` directory and `logs/`.
