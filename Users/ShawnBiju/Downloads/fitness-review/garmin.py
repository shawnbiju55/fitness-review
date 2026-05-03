"""
pull/garmin.py — Pull Garmin Connect data for a given date range.

Pulls three datasets:
  1. Activities (running focus: pace, HR, cadence)
  2. Sleep (all stages, HRV, SpO2)
  3. Daily summary (resting HR, body battery, stress, HRV status)

Auth note: python-garminconnect uses Garmin's mobile SSO flow.
Tokens auto-refresh. Full re-login only needed if refresh token expires.
Tokens stored at ~/.garminconnect/garmin_tokens.json.
"""

import time
from datetime import date, timedelta
from garminconnect import Garmin, GarminConnectAuthenticationError, GarminConnectTooManyRequestsError
from config import GARMIN_EMAIL, GARMIN_PASSWORD


# Garmin API rate limit: be conservative — 1 req/sec is safe.
_REQUEST_DELAY_SEC = 1.0
_client: Garmin | None = None


def _get_client() -> Garmin:
    """Returns authenticated Garmin client. Authenticates once per process."""
    global _client
    if _client is None:
        print("  [garmin] Authenticating...")
        _client = Garmin(email=GARMIN_EMAIL, password=GARMIN_PASSWORD)
        _client.login()
        print("  [garmin] Authenticated.")
    return _client


def _date_range(start: date, end: date):
    """Yields each date from start to end inclusive."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------

def pull_activities(start_date: date, end_date: date) -> list[dict]:
    """
    Returns a list of activity dicts for the date range.
    Filters to running activities only for pace calculation,
    but includes all activity types for complete training load picture.
    """
    client = _get_client()
    print(f"  [garmin] Pulling activities {start_date} → {end_date}")

    try:
        raw = client.get_activities_by_date(
            start_date.isoformat(), end_date.isoformat()
        )
    except GarminConnectTooManyRequestsError:
        print("  [garmin] Rate limited. Waiting 60s...")
        time.sleep(60)
        raw = client.get_activities_by_date(
            start_date.isoformat(), end_date.isoformat()
        )

    activities = []
    for a in raw:
        distance_m = a.get("distance") or 0
        distance_km = round(distance_m / 1000, 3)
        duration_sec = a.get("duration") or 0
        duration_min = round(duration_sec / 60, 2)

        # Pace: min/km — only meaningful for running/walking
        activity_type = a.get("activityType", {}).get("typeKey", "unknown")
        avg_pace = None
        if activity_type in ("running", "trail_running", "treadmill_running") and distance_km > 0:
            avg_pace = round(duration_min / distance_km, 2)

        activities.append({
            "date":                        (a.get("startTimeLocal") or "")[:10],
            "activity_id":                 a.get("activityId"),
            "activity_type":               activity_type,
            "distance_km":                 distance_km,
            "duration_min":                duration_min,
            "avg_pace_min_per_km":         avg_pace,
            "avg_hr":                      a.get("averageHR"),
            "max_hr":                      a.get("maxHR"),
            "avg_cadence":                 a.get("averageRunningCadenceInStepsPerMinute"),
            "training_effect_aerobic":     a.get("aerobicTrainingEffect"),
            "training_effect_anaerobic":   a.get("anaerobicTrainingEffect"),
            "calories":                    a.get("calories"),
        })

    time.sleep(_REQUEST_DELAY_SEC)
    print(f"  [garmin] {len(activities)} activities fetched.")
    return activities


# ---------------------------------------------------------------------------
# Sleep
# ---------------------------------------------------------------------------

def pull_sleep(start_date: date, end_date: date) -> list[dict]:
    """Returns daily sleep records for the date range."""
    client = _get_client()
    print(f"  [garmin] Pulling sleep {start_date} → {end_date}")

    records = []
    for day in _date_range(start_date, end_date):
        try:
            raw = client.get_sleep_data(day.isoformat())
            time.sleep(_REQUEST_DELAY_SEC)
        except GarminConnectTooManyRequestsError:
            print(f"  [garmin] Rate limited on {day}. Waiting 60s...")
            time.sleep(60)
            raw = client.get_sleep_data(day.isoformat())

        daily = raw.get("dailySleepDTO") or {}
        if not daily:
            continue

        records.append({
            "date":            day.isoformat(),
            "sleep_start":     daily.get("sleepStartTimestampLocal"),
            "sleep_end":       daily.get("sleepEndTimestampLocal"),
            "total_sleep_min": _sec_to_min(daily.get("sleepTimeSeconds")),
            "deep_sleep_min":  _sec_to_min(daily.get("deepSleepSeconds")),
            "light_sleep_min": _sec_to_min(daily.get("lightSleepSeconds")),
            "rem_sleep_min":   _sec_to_min(daily.get("remSleepSeconds")),
            "awake_min":       _sec_to_min(daily.get("awakeSleepSeconds")),
            "sleep_score":     daily.get("sleepScores", {}).get("overall", {}).get("value"),
            "avg_spo2":        raw.get("averageSpO2Value"),
            "avg_respiration": raw.get("averageRespirationValue"),
            "avg_hrv_nightly": raw.get("avgOvernightHrv"),
        })

    print(f"  [garmin] {len(records)} sleep records fetched.")
    return records


# ---------------------------------------------------------------------------
# Daily summary
# ---------------------------------------------------------------------------

def pull_daily(start_date: date, end_date: date) -> list[dict]:
    """Returns daily health summary (resting HR, body battery, stress, HRV status)."""
    client = _get_client()
    print(f"  [garmin] Pulling daily summaries {start_date} → {end_date}")

    records = []
    for day in _date_range(start_date, end_date):
        try:
            raw = client.get_stats(day.isoformat())
            time.sleep(_REQUEST_DELAY_SEC)
        except GarminConnectTooManyRequestsError:
            print(f"  [garmin] Rate limited on {day}. Waiting 60s...")
            time.sleep(60)
            raw = client.get_stats(day.isoformat())

        if not raw:
            continue

        records.append({
            "date":             day.isoformat(),
            "resting_hr":       raw.get("restingHeartRate"),
            "hrv_status":       raw.get("hrvStatus"),
            "body_battery_max": raw.get("bodyBatteryHighestValue"),
            "body_battery_min": raw.get("bodyBatteryLowestValue"),
            "avg_stress":       raw.get("averageStressLevel"),
            "steps":            raw.get("totalSteps"),
            "active_calories":  raw.get("activeKilocalories"),
        })

    print(f"  [garmin] {len(records)} daily summaries fetched.")
    return records


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sec_to_min(seconds) -> float | None:
    if seconds is None:
        return None
    return round(seconds / 60, 1)
