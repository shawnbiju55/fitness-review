"""
transform/normalize.py — Enforce schema, deduplicate, add loaded_at timestamp.

Normalization rules:
- Add `loaded_at` timestamp to every row (UTC ISO format).
- Enforce column order from config.py schema definitions.
- Deduplicate on primary key before returning (activity_id for activities,
  date for sleep/daily).
- Columns missing from raw data are filled with None (not dropped).
"""

import csv
import io
from datetime import datetime, timezone
from config import ACTIVITIES_COLUMNS, SLEEP_COLUMNS, DAILY_COLUMNS


_SCHEMA_MAP = {
    "activities": (ACTIVITIES_COLUMNS, "activity_id"),
    "sleep":      (SLEEP_COLUMNS,      "date"),
    "daily":      (DAILY_COLUMNS,      "date"),
}


def normalize(records: list[dict], source: str) -> list[dict]:
    """
    Normalizes a list of raw records for a given source.
    Returns list of dicts conforming to the defined schema.
    """
    if source not in _SCHEMA_MAP:
        raise ValueError(f"Unknown source: {source}")

    columns, pk = _SCHEMA_MAP[source]
    loaded_at = datetime.now(timezone.utc).isoformat()

    normalized = []
    seen_pks = set()

    for row in records:
        pk_val = row.get(pk)
        if pk_val in seen_pks:
            continue
        seen_pks.add(pk_val)

        clean = {col: row.get(col) for col in columns if col != "loaded_at"}
        clean["loaded_at"] = loaded_at


        normalized.append(clean)

    print(f"  [normalize] {source}: {len(records)} in → {len(normalized)} out (deduped).")
    return normalized


def to_csv_rows(records: list[dict], columns: list[str]) -> str:
    """Serializes records to CSV string (no header — header managed by drive.py)."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    writer.writerows(records)
    return output.getvalue()


def get_columns(source: str) -> list[str]:
    """Returns the column list for a given source."""
    columns, _ = _SCHEMA_MAP[source]
    return columns
