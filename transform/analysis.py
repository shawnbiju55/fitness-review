"""
transform/analysis.py — Generate weekly narrative report via Claude API.

Uses the last 7 days of Garmin data (activities, sleep, daily) to produce
a structured markdown report. Uploaded to Drive as analysis_YYYY-WW.md.
"""

import json
from datetime import date, timedelta
import anthropic
from config import ANTHROPIC_API_KEY

_MODEL = "claude-sonnet-4-20250514"


def generate_weekly_report(
    week_end: date,
    activities: list[dict],
    sleep: list[dict],
    daily: list[dict],
) -> str:
    """
    Generates a markdown weekly fitness review report.
    Returns the markdown string.
    """
    week_start = week_end - timedelta(days=6)
    week_label = week_end.strftime("%Y-W%V")

    # Trim to last 7 days only for the report
    def last_7(records):
        return [
            r for r in records
            if week_start.isoformat() <= str(r.get("date", "")) <= week_end.isoformat()
        ]

    payload = {
        "week":        f"{week_start.isoformat()} to {week_end.isoformat()}",
        "activities":  _sanitize(last_7(activities)),
        "sleep":       _sanitize(last_7(sleep)),
        "daily":       _sanitize(last_7(daily)),
    }

    prompt = f"""You are analyzing one week of Garmin fitness data for a personal weekly review.

Data for the week of {payload['week']}:

{json.dumps(payload, indent=2)}

Generate a structured markdown report with these exact sections:

## Weekly Fitness Review — {payload['week']}

### Training Summary
Summarize runs: total distance, average pace, heart rate trends. Note standout sessions.

### Sleep Analysis
Summarize sleep quality and consistency. Flag nights below 6 hours or sleep scores below 60.
Note HRV trends if available.

### Recovery & Readiness
Combine body battery, resting HR trend, stress, and HRV status into a recovery picture.
Flag any metrics suggesting under-recovery.

### Correlations
Identify 1-3 concrete patterns visible in this week's data.
Example: "Sleep score dropped below 70 on nights after long runs."

### Flags & Recommendations
Bullet points only. Max 5. Actionable observations only.
Flag data gaps (missing days, missing metrics).

Keep the tone analytical. Use specific numbers. No motivational filler."""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    try:
        response = client.messages.create(
            model=_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        report = response.content[0].text.strip()
        print(f"  [analysis] Weekly report generated for {week_label}.")
        return report
    except Exception as e:
        print(f"  [analysis] Claude API error: {e}")
        return f"# Analysis failed for {week_label}\n\nError: {e}"


def _sanitize(records: list[dict]) -> list[dict]:
    """Remove raw_text before sending to Claude (not needed for analysis)."""
    return [{k: v for k, v in r.items() if k != "raw_text"} for r in records]
