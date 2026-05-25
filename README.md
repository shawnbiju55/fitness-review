# Fitness Review Pipeline

Automated weekly fitness review: Garmin data →
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

**Google (Drive + Gmail — shared OAuth):**
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable Google Drive API and Gmail API
3. APIs & Services → Credentials → Create Credentials → OAuth client ID
   → Application type: Desktop app → Download JSON
4. Save to `./credentials/client_secrets.json`
5. Create a folder in your Google Drive → copy the folder ID from the URL
6. Add folder ID and `EMAIL_RECIPIENT=your@email.com` to `.env`
7. First run opens a browser for OAuth authorization (grants Drive + Gmail together).
   Token saved to `./credentials/oauth_token.json` and reused automatically.

**Anthropic:**
- Add your API key to `.env`

### 3. First run (initial 90-day batch)
```bash
python run.py
```
No watermarks exist yet → pulls last 90 days for all sources.

### 4. Windows Task Scheduler (automated weekly runs)

1. Open Task Scheduler → Create Basic Task
2. Name: `Fitness Review Pipeline`
3. Trigger: Weekly → Sunday → 9:00 PM
4. Action: Start a program
   - Program: `C:\path\to\fitness-review\.venv\Scripts\python.exe`
   - Arguments: `run.py`
   - Start in: `C:\path\to\fitness-review`
5. Enable: "Run whether user is logged on or not"

### 5. Power BI (work laptop)

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
│   ├── client_secrets.json   # OAuth client ID (from GCP)
│   └── oauth_token.json      # auto-created after first login
├── pull/
│   └── garmin.py           # Garmin Connect data pull
├── transform/
│   ├── normalize.py        # schema enforcement + dedup
│   └── analysis.py         # Claude weekly report generation
└── load/
    ├── auth.py             # shared OAuth2 credentials (Drive + Gmail)
    ├── watermark.py        # incremental load tracking
    ├── drive.py            # Google Drive append + upload
    └── gmail.py            # Gmail delivery of weekly report
```

## Troubleshooting

**Garmin auth fails:** Delete `~/.garminconnect/garmin_tokens.json` and re-run.
If you have MFA enabled, first login requires interactive browser step.

**Drive upload fails:** Watermark won't advance — next run will safely retry the same date range.

**OAuth: browser doesn't open for auth:** Run `python run.py` in an interactive
terminal (not a headless Task Scheduler job) for the first run to complete OAuth.
After that, `./credentials/oauth_token.json` handles auth silently.

**OAuth: token expired or invalid:** Delete `./credentials/oauth_token.json` and re-run
interactively to re-authorize. This grants combined Drive + Gmail access in one step.
