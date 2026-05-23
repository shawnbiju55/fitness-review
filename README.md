# Fitness Review Pipeline

Automated weekly fitness review: Garmin data + Day One journal entries →
Google Drive CSVs → Power BI (work laptop) + Claude analysis + Gmail delivery.

## Setup

### 1. Python environment
```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

### 2. Credentials

**Garmin:**
- Copy `.env.example` to `.env`
- Add your Garmin Connect email and password
- First run will authenticate and store tokens at `~/.garminconnect/garmin_tokens.json`

**Google Drive (Service Account):**
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable Google Drive API
3. IAM & Admin → Service Accounts → Create → download JSON key
4. Save JSON key to `./credentials/google_service_account.json`
5. Create a folder in your Google Drive → copy the folder ID from the URL
6. Share that folder with the service account email (Editor access)
7. Add folder ID to `.env`

**Anthropic:**
- Add your API key to `.env`

**Gmail (for emailing the weekly report):**
1. Enable the Gmail API on your Google Cloud project
2. APIs & Services → Credentials → Create Credentials → OAuth client ID
   → Application type: Desktop app → Download JSON
3. Save to `./credentials/gmail_oauth_credentials.json`
4. Add `GMAIL_RECIPIENT=your@email.com` to `.env`
5. First run opens a browser for OAuth authorization
   Token saved to `./credentials/gmail_token.json` and reused automatically

### 3. Day One iOS Shortcut

Create an iOS Shortcut that:
1. Triggers every Sunday at 8:00 PM
2. Action: "Get Journal Entries" → Last 30 days → All journals
3. Action: "Get Contents of URL" (or save to Files)
4. Saves JSON to iCloud Drive or Google Drive app folder
5. Update `DAYONE_EXPORT_PATH` in `.env` to point to the synced file

Alternatively: export manually from Day One web → save to the path in `.env`.

### 4. First run (initial 90-day batch)
```bash
python run.py
```
No watermarks exist yet → pulls last 90 days for all sources.

### 5. Windows Task Scheduler (automated weekly runs)

1. Open Task Scheduler → Create Basic Task
2. Name: `Fitness Review Pipeline`
3. Trigger: Weekly → Sunday → 9:00 PM
4. Action: Start a program
   - Program: `C:\path\to\fitness-review\.venv\Scripts\python.exe`
   - Arguments: `run.py`
   - Start in: `C:\path\to\fitness-review`
5. Enable: "Run whether user is logged on or not"

### 6. Power BI (work laptop)

1. Open Power BI Desktop
2. Get Data → Web → enter the Google Drive direct download URL for each CSV:
   `https://drive.google.com/uc?export=download&id=FILE_ID`
3. The FILE_ID appears in the browser URL when you open the file in Drive
4. Build your visuals. Hit Refresh when you want latest data.

On personal laptop: open the CSVs in Google Drive → they auto-open as Google Sheets.

## File outputs on Drive

```
fitness-review/                          ← your Google Drive folder
├── garmin_activities_master.csv
├── garmin_sleep_master.csv
├── garmin_daily_master.csv
├── dayone_entries_master.csv
└── weekly_reports/
    ├── analysis_2026-W18.md
    ├── analysis_2026-W19.md
    └── ...
```

## Repo structure

```
fitness-review/
├── run.py                  # entry point
├── config.py               # all constants + schema definitions
├── requirements.txt
├── .env.example
├── watermarks.db           # local SQLite, gitignored
├── CHANGELOG.md
├── credentials/            # gitignored
│   ├── google_service_account.json
│   └── gmail_oauth_credentials.json
├── data/                   # gitignored
│   └── dayone_export.json
├── pull/
│   ├── garmin.py           # Garmin Connect data pull
│   └── dayone.py           # Day One JSON export parser
├── transform/
│   ├── normalize.py        # schema enforcement + dedup
│   ├── sentiment.py        # Claude sentiment enrichment
│   └── analysis.py         # Claude weekly report generation
└── load/
    ├── watermark.py        # incremental load tracking
    ├── drive.py            # Google Drive append + upload
    └── gmail.py            # Gmail delivery of weekly report
```

## Troubleshooting

**Garmin auth fails:** Delete `~/.garminconnect/garmin_tokens.json` and re-run.
If you have MFA enabled, first login requires interactive browser step.

**Drive upload fails:** Check service account has Editor access to the folder.
Watermark won't advance — next run will safely retry the same date range.

**Day One file not found:** Check `DAYONE_EXPORT_PATH` in `.env`.
Ensure the iOS Shortcut has run at least once and the file is synced.

**Gmail: browser doesn't open for auth:** Run `python run.py` in an interactive
terminal (not a headless Task Scheduler job) for the first run to complete OAuth.
After that, `./credentials/gmail_token.json` handles auth silently.

**Gmail: token expired:** Delete `./credentials/gmail_token.json` and re-run
interactively to re-authorize.
