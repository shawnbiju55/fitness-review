"""
pull/dayone.py — Parse Day One JSON export for a given date range.

Expected input: JSON file exported by iOS Shortcut (Day One format).
The iOS Shortcut should export to a synced folder (iCloud/Google Drive)
and overwrite the same file each week. This script reads new entries
based on the watermark date — it does not depend on the export being
incremental itself.

Day One JSON structure:
{
  "metadata": {...},
  "entries": [
    {
      "uuid": "...",
      "creationDate": "2026-04-27T08:30:00Z",
      "text": "Entry body text...",
      ...
    }
  ]
}
"""

import json
from datetime import date, timezone
from dateutil import parser as dateutil_parser
from config import DAYONE_EXPORT_PATH


def pull_dayone_entries(start_date: date, end_date: date) -> list[dict]:
    """
    Reads the Day One JSON export and returns entries within the date range.
    Sentiment fields are left as None here — filled in by transform/sentiment.py.
    """
    try:
        with open(DAYONE_EXPORT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"  [dayone] Export file not found at {DAYONE_EXPORT_PATH}. Skipping.")
        return []
    except json.JSONDecodeError as e:
        print(f"  [dayone] JSON parse error: {e}. Skipping.")
        return []

    raw_entries = data.get("entries", [])
    print(f"  [dayone] {len(raw_entries)} total entries in export file.")

    records = []
    for entry in raw_entries:
        created_str = entry.get("creationDate") or entry.get("date")
        if not created_str:
            continue

        entry_date = _parse_entry_date(created_str)
        if entry_date is None:
            continue
        if not (start_date <= entry_date <= end_date):
            continue

        text = entry.get("text") or ""
        word_count = len(text.split()) if text else 0

        records.append({
            "date":             entry_date.isoformat(),
            "entry_id":         entry.get("uuid", ""),
            "word_count":       word_count,
            "raw_text":         text,          # used by sentiment.py, dropped before CSV write
            # sentiment fields filled by transform/sentiment.py
            "sentiment_score":  None,
            "sentiment_label":  None,
            "fatigue_flag":     None,
            "motivation_flag":  None,
            "entry_summary":    None,
        })

    print(f"  [dayone] {len(records)} entries in range {start_date} → {end_date}.")
    return records


def _parse_entry_date(date_str: str) -> date | None:
    """Parses ISO 8601 date strings from Day One export."""
    try:
        dt = dateutil_parser.parse(date_str)
        # Normalize to local date (Day One stores in UTC)
        if dt.tzinfo is not None:
            dt = dt.astimezone(tz=None).replace(tzinfo=None)
        return dt.date()
    except Exception:
        return None
