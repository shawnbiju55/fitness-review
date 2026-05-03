"""
run.py — Pipeline entry point. Orchestrates all steps in order.

Run manually:   python run.py
Scheduled:      Windows Task Scheduler → trigger weekly (Sunday night / Monday morning)

Step order:
  1. Read watermarks (determine date range per source)
  2. Pull Garmin (activities, sleep, daily)
  3. Pull Day One entries
  4. Enrich Day One with sentiment (Claude API)
  5. Normalize all datasets
  6. Append to master CSVs on Google Drive
  7. Advance watermarks (only on successful Drive write)
  8. Generate weekly narrative report (Claude API) → upload to Drive

Failure behavior:
  - If any source fails to pull, that source is skipped for this run.
    Other sources proceed normally. Watermark for failed source is not advanced.
  - If Drive upload fails for a source, watermark is not advanced.
    Next run will re-pull and re-deduplicate safely.
"""

import sys
from datetime import date
from load.watermark import get_watermark, set_watermark, get_all_watermarks
from load.drive import append_to_master, upload_analysis_report
from pull.garmin import pull_activities, pull_sleep, pull_daily
from pull.dayone import pull_dayone_entries
from transform.normalize import normalize
from transform.sentiment import enrich_with_sentiment
from transform.analysis import generate_weekly_report
from config import DRIVE_FILES, get_date_range_for_run


def main():
    print("=" * 55)
    print("  Fitness Review Pipeline")
    print(f"  Run date: {date.today().isoformat()}")
    print("=" * 55)

    # --- Step 1: Watermarks ---
    print("\n[1/7] Reading watermarks...")
    wm = get_all_watermarks()
    for src, last in wm.items():
        print(f"  {src}: last loaded {last or 'never (initial batch)'}")

    # --- Step 2: Garmin activities ---
    activities_norm = []
    print("\n[2/7] Garmin activities...")
    try:
        start, end = get_date_range_for_run(wm["activities"])
        raw_activities = pull_activities(start, end)
        activities_norm = normalize(raw_activities, "activities")
    except Exception as e:
        print(f"  [ERROR] Activities pull failed: {e}")

    # --- Step 3: Garmin sleep ---
    sleep_norm = []
    print("\n[3/7] Garmin sleep...")
    try:
        start, end = get_date_range_for_run(wm["sleep"])
        raw_sleep = pull_sleep(start, end)
        sleep_norm = normalize(raw_sleep, "sleep")
    except Exception as e:
        print(f"  [ERROR] Sleep pull failed: {e}")

    # --- Step 4: Garmin daily ---
    daily_norm = []
    print("\n[4/7] Garmin daily summaries...")
    try:
        start, end = get_date_range_for_run(wm["daily"])
        raw_daily = pull_daily(start, end)
        daily_norm = normalize(raw_daily, "daily")
    except Exception as e:
        print(f"  [ERROR] Daily pull failed: {e}")

    # --- Step 5: Day One + sentiment ---
    dayone_norm = []
    print("\n[5/7] Day One entries + sentiment...")
    try:
        start, end = get_date_range_for_run(wm["dayone"])
        raw_dayone = pull_dayone_entries(start, end)
        raw_dayone = enrich_with_sentiment(raw_dayone)
        dayone_norm = normalize(raw_dayone, "dayone")
    except Exception as e:
        print(f"  [ERROR] Day One pull/enrich failed: {e}")

    # --- Step 6: Drive uploads + watermark advancement ---
    print("\n[6/7] Writing to Google Drive...")

    sources = [
        ("activities", activities_norm, DRIVE_FILES["activities"]),
        ("sleep",      sleep_norm,      DRIVE_FILES["sleep"]),
        ("daily",      daily_norm,      DRIVE_FILES["daily"]),
        ("dayone",     dayone_norm,     DRIVE_FILES["dayone"]),
    ]

    today = date.today()
    for source, records, filename in sources:
        if not records:
            print(f"  [drive] {source}: no records — skipping.")
            continue
        try:
            rows_written = append_to_master(source, records, filename)
            if rows_written >= 0:
                # Determine the max date in the records we just wrote
                dates = [r["date"] for r in records if r.get("date")]
                watermark_date = max(dates) if dates else today.isoformat()
                set_watermark(source, date.fromisoformat(watermark_date))
        except Exception as e:
            print(f"  [ERROR] Drive write failed for {source}: {e}")
            print(f"  Watermark NOT advanced for {source}. Will retry next run.")

    # --- Step 7: Weekly narrative report ---
    print("\n[7/7] Generating weekly analysis report...")
    try:
        # Use yesterday as the week-end date (same as pull end date)
        from datetime import timedelta
        week_end = date.today() - timedelta(days=1)
        week_label = week_end.strftime("%Y-W%V")

        report_md = generate_weekly_report(
            week_end=week_end,
            activities=activities_norm,
            sleep=sleep_norm,
            daily=daily_norm,
            dayone=dayone_norm,
        )
        upload_analysis_report(week_label, report_md)
    except Exception as e:
        print(f"  [ERROR] Analysis report failed: {e}")

    print("\n" + "=" * 55)
    print("  Pipeline complete.")
    print("=" * 55)


if __name__ == "__main__":
    main()
