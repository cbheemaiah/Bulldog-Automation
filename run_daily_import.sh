#!/bin/bash

# 1. Configuration
# ----------------
PROJECT_DIR="/Users/chiragbheemaiah/Documents/Bulldog"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/import_$(date +\%Y\%m\%d).log"

# IMPORTANT: Cron runs with a minimal path. 
# Run 'which uv' in your terminal and paste the result here if different.
UV_BIN="/Users/chiragbheemaiah/.local/bin/uv" 

# 2. Setup
# --------
mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR" || { echo "Failed to cd to $PROJECT_DIR"; exit 1; }

echo "==================================================" >> "$LOG_FILE"
echo "Starting Import Job: $(date)" >> "$LOG_FILE"

# 3. Run Fetch Script
# -------------------
echo "[1/2] Running Fetch Script..." >> "$LOG_FILE"
"$UV_BIN" run app/fetch_bulldog_csv.py >> "$LOG_FILE" 2>&1
FETCH_EXIT=$?

if [ $FETCH_EXIT -ne 0 ]; then
    echo "ERROR: Fetch script failed (Exit Code: $FETCH_EXIT). Aborting." >> "$LOG_FILE"
    exit $FETCH_EXIT
fi

# 4. Run Create Contacts Script
# -----------------------------
echo "[2/2] Running Create Contacts Script..." >> "$LOG_FILE"
"$UV_BIN" run app/create_contacts_from_csv.py >> "$LOG_FILE" 2>&1
CREATE_EXIT=$?

echo "Job finished with exit code $CREATE_EXIT at $(date)" >> "$LOG_FILE"
echo "==================================================" >> "$LOG_FILE"