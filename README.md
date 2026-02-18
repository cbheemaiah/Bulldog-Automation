# Bulldog

Bulldog is an automation tool for managing Mautic contacts. It handles importing contacts from CSV files, managing their lifecycle through specific tags (e.g., "warmup_campaign" to "Test"), and maintaining a local history of operations.

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
- **Input**: Place CSV files in the `data/` directory.
- **Output**: Generated files (tokens, logs, history) appear in `generated/`.

## Usage

### Step 1: Create or Reset Contacts
Reads the CSV file defined in `config.json`.
- **New Contacts**: Created in Mautic with the default tag (`warmup_campaign`).
- **Existing Contacts**: If a contact exists in local history and has the `Test` tag, it is reset to `warmup_campaign`.
- **Queue**: All processed contacts are added to `generated/pending_updates.json`.

```bash
uv run app/create_contacts_from_csv.py
```

### Step 2: Update Tags
Processes the queue from `pending_updates.json`.
- Updates tags in Mautic (removes `warmup_campaign`, adds `Test`).
- Logs successful updates to `generated/update_log.json`.
- Failed updates remain in the pending file for retry.

```bash
uv run app/update_contacts_tags.py
```

### Cleanup (Testing Only)
Deletes all contacts tracked in `contact_history.json` from Mautic and resets the local state.

```bash
uv run scripts/delete_created_contacts.py
```


# Remember to remove limmit parameter