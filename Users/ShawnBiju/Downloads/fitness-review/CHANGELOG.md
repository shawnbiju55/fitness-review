# Changelog

All notable changes to this project are documented here.
Format: `[YYYY-MM-DD] | Type | Description | Why`

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
