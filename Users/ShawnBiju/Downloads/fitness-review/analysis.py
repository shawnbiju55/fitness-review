"""
transform/analysis.py — Generate weekly narrative report via Claude API.

Pulls the last 7 days of data across all four sources and asks Claude
to produce a structured markdown report. Report is uploaded to Drive
as analysis_YYYY-WW.md.

Runs after all CSVs are written — uses the freshly normalized data
from the current run rather than re-downloading from Drive.
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
    dayone: list[dict],
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
        "week": f"{week_start.isoformat()} to {week_end.isoformat()}",
        "activities":  _sanitize(last_7(activities)),
        "sleep":       _sanitize(last_7(sleep)),
        "daily":       _sanitize(last_7(daily)),
        "journal":     _sanitize(last_7(dayone)),
    }

    prompt = f"""You are analyzing one week of fitness and journal data for a personal weekly review.

Data for the week of {payload['week']}:

{json.dumps(payload, indent=2)}

Generate a structured markdown report with these exact sections:

## Weekly Fitness Review — {payload['week']}

### Training Summary
Summarize runs: total distance, average pace, heart rate trends. Note any standout sessions.

### Sleep Analysis
Summarize sleep quality and consistency. Flag any nights below 6 hours or sleep scores below 60.
Note HRV trends if available.

### Recovery & Readiness
Combine body battery, resting HR trend, stress levels, and HRV status into a recovery picture.
Flag if any metrics suggest under-recovery.

### Journal Insights
Summarize sentiment trend across the week. Call out fatigue or motivation flags.
Note any correlation between journal tone and training performance.

### Correlations
Identify 1-3 concrete patterns visible in this week's data.
Example: "Sleep score dropped below 70 on nights after long runs" or
"Motivation flags align with days where body battery was above 80."

### Flags & Recommendations
Bullet points only. Max 5. Focus on actionable observations.
Flag data gaps (missing days, missing metrics).

Keep the tone analytical, not motivational. Use specific numbers. Avoid vague statements."""

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
