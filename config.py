"""
config.py — Central configuration for all pipeline constants.
Change metric fields, file names, or date logic here — not in individual modules.
"""

import os
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

# --- Credentials ---
GARMIN_EMAIL = os.getenv("GARMIN_EMAIL")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
OAUTH_CLIENT_SECRETS = os.getenv("OAUTH_CLIENT_SECRETS", "./credentials/client_secrets.json")
OAUTH_TOKEN_PATH = os.getenv("OAUTH_TOKEN_PATH", "./credentials/oauth_token.json")

# --- Email delivery ---
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", "")

# --- Watermark DB ---
WATERMARK_DB_PATH = "./watermarks.db"

# --- Google Drive master file names ---
DRIVE_FILES = {
    "activities": "garmin_activities_master.csv",
    "sleep":      "garmin_sleep_master.csv",
    "daily":      "garmin_daily_master.csv",
}

# Subfolder on Drive for weekly narrative reports
DRIVE_ANALYSIS_SUBFOLDER = "weekly_reports"

# --- Schema definitions (used for CSV headers + normalization validation) ---

ACTIVITIES_COLUMNS = [
    "date",
    "activity_id",
    "activity_type",
    "distance_km",
    "duration_min",
    "avg_pace_min_per_km",   # P1: running pace
    "avg_hr",                 # P1: heart rate
    "max_hr",
    "avg_cadence",
    "training_effect_aerobic",
    "training_effect_anaerobic",
    "calories",
    "loaded_at",
]

SLEEP_COLUMNS = [
    "date",
    "sleep_start",
    "sleep_end",
    "total_sleep_min",        # P1: sleep
    "deep_sleep_min",         # P1
    "light_sleep_min",        # P1
    "rem_sleep_min",          # P1
    "awake_min",
    "sleep_score",
    "avg_spo2",
    "avg_respiration",
    "avg_hrv_nightly",        # P2: HRV
    "loaded_at",
]

DAILY_COLUMNS = [
    "date",
    "resting_hr",             # P1: heart rate context
    "hrv_status",             # P2
    "body_battery_max",       # P2
    "body_battery_min",
    "avg_stress",             # P2
    "steps",
    "active_calories",
    "loaded_at",
]

# --- Date helpers ---

def get_date_range_for_run(last_loaded_date: date | None) -> tuple[date, date]:
    """
    Returns (start_date, end_date) for the current run.
    - First ever run (no watermark): pulls last 90 days as initial batch.
    - Subsequent runs: pulls from day after last_loaded_date to yesterday.
      We use yesterday (not today) because Garmin data for today may be incomplete.
    """
    end_date = date.today() - timedelta(days=1)

    if last_loaded_date is None:
        start_date = end_date - timedelta(days=90)
    else:
        start_date = last_loaded_date + timedelta(days=1)

    return start_date, end_date
