# Bulldog

Bulldog is an automation tool for managing Mautic contacts. It handles importing contacts from CSV files, managing their lifecycle through automated day-based tagging (e.g., "Digital-Bulldog-Day-1"), and maintaining a local history of operations.

## Setup

### 1. Prerequisites
- Python 3.13+
- Mautic instance with API credentials (OAuth2)

### 2. Installation
This project uses `uv` for dependency management.

```bash
uv sync
```

### 3. Environment Variables
Create a `.env` file in the root directory with your Mautic API credentials:

```ini
MAUTIC_CLIENT_ID=your_client_id
MAUTIC_CLIENT_SECRET=your_client_secret
```

### 4. Configuration
Ensure `config.json` is set up with your Mautic URL and file paths.
- **Input**: Place CSV files in the `data/` directory (or use the fetch script).
- **Output**: Generated files (tokens, state, history) appear in `generated/`.

## Usage

### Step 1: Fetch External CSV
Downloads the latest contact list from the source defined in `config.json` (`bulldog_api_url`).

```bash
uv run app/fetch_bulldog_csv.py
```

### Step 2: Create and Tag Contacts
Processes the latest CSV found in the `data/` directory.
- **Day-Based Tags**: Automatically increments a "Day" counter and creates a new tag in Mautic (e.g., `Digital-Bulldog-Day-1`).
- **Segment Sync**: Updates the configured Mautic segment to filter only for contacts with the current day's tag.
- **Contact Creation**: Creates new contacts with the day-tag, a test-tag, and a rotation group (1-4).
- **Retries**: Automatically retries previously failed contact creations.

```bash
uv run app/create_contacts_from_csv.py
```

#### Manual Overrides
For manual runs, you can use the following arguments:
- `--file <path>`: Process a specific CSV file. This bypasses the "must be from today" check.
- `--day <number>`: Override the current Bulldog Day. This value will be saved to the state and used for subsequent automated runs.

Example:
```bash
uv run app/create_contacts_from_csv.py --file data/old_import.csv --day 10
```

### Cleanup (Testing Only)
Deletes all contacts tracked in `contact_history.json` from Mautic and resets the local state.

```bash
uv run scripts/delete_created_contacts.py
```

## Automation
A convenience script `run_daily_import.sh` is provided to run the full workflow (Fetch + Create) sequentially, suitable for CRON jobs.

---
# Notes
- Make sure to manually delete tags if you reset the sequence.
- Remember to adjust the `limit` parameter in `config.json` after testing (set it to 0 for full runs).
- Setup a CRON job locally to automate the process daily.