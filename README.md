# Bulldog

Bulldog is an automation tool for managing Mautic contacts. It handles importing contacts from CSV files, managing their lifecycle through automated day-based tagging, and maintaining a local history of operations.

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
- **Input**: CSV files are downloaded to the `data/` directory.
- **Output**: Persistent state and logs are stored in `generated/`:
    - `bulldog_state.json`: Current Day counter and last run date.
    - `contact_history.json`: List of successfully created contacts.
    - `created_tags.json`: Registry of tags created by the script for automated cleanup.
    - `mautic_tokens.json`: OAuth2 credentials.

## Usage

### Step 1: Fetch External CSV
Downloads the latest contact list from the source defined in `config.json` (`bulldog_api_url`).

```bash
uv run app/fetch_bulldog_csv.py
```

### Step 2: Create and Tag Contacts
Processes the latest CSV found in the `data/` directory.

> [!IMPORTANT]
> **Safety First**: Always check the current day counter in `generated/bulldog_state.json` before running. If the count is wrong, use the `--day` override.

- **Day-Based Tags**: Automatically increments a "Day" counter and creates a new tag in Mautic (e.g., `Digital-Bulldog-Day-1`).
- **Confirmation**: Running this script manually will show a summary of the tags being used and ask for a `(y/n)` confirmation before creating contacts.

```bash
uv run app/create_contacts_from_csv.py
```

#### Manual Overrides
For manual/testing runs, you can use the following arguments:
- `--file <path>`: Process a specific CSV file (bypasses the "must be from today" check).
- `--day <number>`: Override the Bulldog Day. This value is saved and future automated runs will continue from here.

### Cleanup & Reset

#### Full Reset (Testing Only)
Deletes **all** contacts and **all** tags Bulldog has ever created, then wipes the local state.

```bash
uv run scripts/delete_created_contacts.py
```

#### Targeted Deletion
Deletes only the contacts and the specific tag for a **single** Bulldog Day. This surgically edits your local history files to remove only the targeted records.

```bash
# Delete all contacts and the tag for Day 5
uv run scripts/delete_by_tag.py --day 5

# Or delete by a specific Mautic Tag ID
uv run scripts/delete_by_tag.py --tag_id 29
```

**Note**: This script does **not** reset the Bulldog Day counter in `bulldog_state.json`. Subsequent automated runs will continue moving forward (e.g., if you delete Day 10, the next run will be Day 11).

**What this does:**
1.  **Deletes Contacts**: Removes all contacts listed in `contact_history.json` from Mautic.
2.  **Deletes Tags**: Removes all tracked tags in `created_tags.json` using the `api/tags/{id}/delete` endpoint.
3.  **Resets State**: Deletes all local history, state files, and cached CSVs.

## Automation
A convenience script `run_daily_import.sh` is provided to run the full workflow (Fetch + Create) sequentially.

**Logging**: This script uses `tee` to output all logs to both your **terminal** (for real-time monitoring) and timestamped **log files** in the `logs/` directory (for historical records).

---
# Notes
- Remember to adjust the `limit` parameter in `config.json` after testing (set it to 0 for full runs).
- Ensure your Mautic API has the appropriate permissions for contact and tag deletion.
- Setup a CRON job locally to automate the process daily.