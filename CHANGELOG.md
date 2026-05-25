# Changelog

All notable changes to this project are documented here.
Format: `[YYYY-MM-DD] | Type | Description | Why`

---

## [2026-05-25] | REFACTOR | Auth consolidation + dead code cleanup

**Why:** Simplify auth by using a single OAuth2 token for both Google Drive and Gmail
instead of separate credentials. Remove dead Day One integration code (no public API).

**Changes:**
- Removed `pull/dayone.py`, `transform/sentiment.py`, and all Day One references
  from config, watermark, normalize, drive, analysis, and run.py.
- Created `load/auth.py`: shared `get_credentials()` for Drive + Gmail OAuth2.
- Refactored `load/drive.py`: uses shared OAuth instead of service account.
- Refactored `load/gmail.py`: uses shared OAuth instead of its own token flow.
- Renamed `GMAIL_RECIPIENT` → `EMAIL_RECIPIENT` in config.py and .env.example.
- Removed config vars: `GOOGLE_SERVICE_ACCOUNT_JSON`, `GMAIL_CREDENTIALS_JSON`,
  `GMAIL_TOKEN_PATH`, `DAYONE_EXPORT_PATH`, `DAYONE_COLUMNS`.
- Pinned `garminconnect>=0.3.3` in requirements.txt (tokenstore support).

**Migration (one-time):**
- Delete `credentials/oauth_token.json` before next run — scopes changed.
  Browser auth will open once to grant combined Drive + Gmail access.
- Rename `GMAIL_RECIPIENT` to `EMAIL_RECIPIENT` in your `.env` file.
- Remove `GMAIL_CREDENTIALS_JSON`, `GMAIL_TOKEN_PATH`, `GOOGLE_SERVICE_ACCOUNT_JSON`
  from `.env` (no longer used).

---

## [2026-05-23] | FEATURE | Gmail API delivery of weekly report

**Why:** After the pipeline generates and uploads the weekly analysis report to Drive,
now also emails the markdown report to a configurable recipient via Gmail API.
Allows reading the weekly review without opening Drive — arrives in inbox automatically.

**Changes:**
- Added `load/gmail.py`: Gmail API sender using OAuth2 Desktop credentials.
  Silently skips if `GMAIL_RECIPIENT` or credentials file is missing — pipeline
  always completes even without Gmail configured.
- Updated `run.py` Step 8 (new): calls `send_weekly_report` after Drive upload.
- Updated `config.py`: added `GMAIL_RECIPIENT`, `GMAIL_CREDENTIALS_JSON`, `GMAIL_TOKEN_PATH`.
- Updated `requirements.txt`: added `google-auth-oauthlib>=1.2.0`.
- Updated `.env.example` with Gmail config.
- Restructured all source files from flat layout into proper `pull/`, `transform/`,
  `load/` package hierarchy matching imports in `run.py`.

**Gmail setup (one-time):**
1. Google Cloud Console → Enable Gmail API on your project.
2. APIs & Services → Credentials → OAuth client ID → Desktop app → Download JSON.
3. Save as `./credentials/gmail_oauth_credentials.json`.
4. Set `GMAIL_RECIPIENT` in `.env`.
5. First run opens a browser for OAuth authorization; token saved to
   `./credentials/gmail_token.json` and reused automatically from then on.

---

## [2026-05-03] | INIT | Initial project scaffold

**Why:** Build an automated weekly fitness review pipeline pulling Garmin data
and Day One journal entries, storing incremental CSVs to Google Drive for
Power BI (work laptop) and Claude analysis (personal laptop / browser artifact).

**Design decisions:**
- Single master CSV per data type (append-only) rather than one CSV per week.
  Reason: Power BI can point at one file and hit Refresh — no folder merging logic needed.
- SQLite watermark DB for incremental loads. Watermark only advances on successful
  Drive write. Prevents gaps if upload fails mid-run.
- Deduplication on `activity_id` / `date+source` before append to prevent double-rows
  if a run is re-triggered manually.
- CSVs over Google Sheets: more portable, works on work laptop (Power BI Web connector)
  and personal laptop (Google Drive opens as Sheets natively).

**Priority metrics (P1):** running pace, heart rate, all sleep metrics.
**Priority metrics (P2):** HRV, body battery, stress, training load.

**Data sources:**
- Garmin: `python-garminconnect` v0.3.3, MIT license, unofficial reverse-engineered wrapper.
  Risk: Garmin can break auth without notice. Mitigated by watermark — failed runs don't
  lose data, they just retry the same date range next time.
- Day One: iOS Shortcut exports weekly JSON to iCloud/Google Drive.
  No public API exists as of May 2026.

**Output files on Google Drive:**
- `garmin_activities_master.csv`
- `garmin_sleep_master.csv`
- `garmin_daily_master.csv`
- `dayone_entries_master.csv`
- `analysis_YYYY-WW.md` (Claude weekly narrative, one file per week)
