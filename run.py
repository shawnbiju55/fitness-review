"""
run.py — Pipeline entry point. Orchestrates all steps in order.

Run manually:   python run.py
Scheduled:      Windows Task Scheduler — trigger weekly (Sunday night)

Steps:
  1. Read watermarks (determine date range per source)
  2. Pull Garmin activities
  3. Pull Garmin sleep
  4. Pull Garmin daily summaries
  5. Normalize all datasets
  6. Append to master CSVs on Google Drive + advance watermarks
  7. Generate weekly narrative report via Claude API → upload to Drive
  8. Email weekly report via Gmail

Failure behavior:
  - Each source is isolated. A failed pull skips that source; others proceed.
  - Watermark only advances after a successful Drive write.
    Next run re-pulls the same date range and deduplicates safely.
  - If Gmail fails, pipeline still completes — report is available on Drive.
"""

from datetime import date, timedelta
from load.watermark import get_watermark, set_watermark, get_all_watermarks
from load.drive import append_to_master, upload_analysis_report
from load.gmail import send_weekly_report
from pull.garmin import pull_activities, pull_sleep, pull_daily
from transform.normalize import normalize
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
        print(f"  {src}: last loaded {last or 'never (initial 90-day batch)'}")

    # --- Step 2: Activities ---
    activities_norm = []
    print("\n[2/7] Garmin activities...")
    try:
        start, end = get_date_range_for_run(wm["activities"])
        activities_norm = normalize(pull_activities(start, end), "activities")
    except Exception as e:
        print(f"  [ERROR] Activities: {e}")

    # --- Step 3: Sleep ---
    sleep_norm = []
    print("\n[3/7] Garmin sleep...")
    try:
        start, end = get_date_range_for_run(wm["sleep"])
        sleep_norm = normalize(pull_sleep(start, end), "sleep")
    except Exception as e:
        print(f"  [ERROR] Sleep: {e}")

    # --- Step 4: Daily ---
    daily_norm = []
    print("\n[4/7] Garmin daily summaries...")
    try:
        start, end = get_date_range_for_run(wm["daily"])
        daily_norm = normalize(pull_daily(start, end), "daily")
    except Exception as e:
        print(f"  [ERROR] Daily: {e}")

    # --- Step 5: Drive uploads + watermarks ---
    print("\n[5/7] Writing to Google Drive...")
    sources = [
        ("activities", activities_norm, DRIVE_FILES["activities"]),
        ("sleep",      sleep_norm,      DRIVE_FILES["sleep"]),
        ("daily",      daily_norm,      DRIVE_FILES["daily"]),
    ]

    for source, records, filename in sources:
        if not records:
            print(f"  [drive] {source}: no records — skipping.")
            continue
        try:
            rows_written = append_to_master(source, records, filename)
            if rows_written >= 0:
                dates = [r["date"] for r in records if r.get("date")]
                watermark_date = max(dates) if dates else date.today().isoformat()
                set_watermark(source, date.fromisoformat(watermark_date))
        except Exception as e:
            print(f"  [ERROR] Drive write failed for {source}: {e}")
            print(f"  Watermark NOT advanced. Will retry next run.")

    # --- Step 6: Weekly report ---
    report_md = None
    week_label = None
    print("\n[6/7] Generating weekly analysis report...")
    try:
        week_end = date.today() - timedelta(days=1)
        week_label = week_end.strftime("%Y-W%V")
        report_md = generate_weekly_report(
            week_end=week_end,
            activities=activities_norm,
            sleep=sleep_norm,
            daily=daily_norm,
        )
        upload_analysis_report(week_label, report_md)
    except Exception as e:
        print(f"  [ERROR] Analysis report: {e}")

    # --- Step 7: Email report ---
    print("\n[7/7] Emailing weekly report...")
    if report_md and week_label:
        try:
            send_weekly_report(week_label, report_md)
        except Exception as e:
            print(f"  [ERROR] Gmail delivery failed: {e}")
            print("  Report still available on Drive.")
    else:
        print("  No report to send — report generation failed.")

    print("\n" + "=" * 55)
    print("  Pipeline complete.")
    print("=" * 55)


if __name__ == "__main__":
    main()
