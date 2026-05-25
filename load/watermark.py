"""
load/watermark.py — Incremental load watermarks stored in local SQLite.

Rules:
- Watermark only advances AFTER successful Drive write.
- If Drive upload fails, next run re-pulls the same date range.
- Deduplication in drive.py handles any overlap — no data loss, no gaps.
"""

import sqlite3
from datetime import date
from config import WATERMARK_DB_PATH

# Valid source keys — must match DRIVE_FILES keys in config.py
SOURCES = {"activities", "sleep", "daily", "dayone"}


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(WATERMARK_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS watermarks (
            source       TEXT PRIMARY KEY,
            last_loaded  TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def get_watermark(source: str) -> date | None:
    """
    Returns the last successfully loaded date for a source, or None if
    this source has never been loaded (triggers 90-day initial batch).
    """
    assert source in SOURCES, f"Unknown source: {source}"
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT last_loaded FROM watermarks WHERE source = ?", (source,)
        ).fetchone()
    return date.fromisoformat(row[0]) if row else None


def set_watermark(source: str, loaded_through: date) -> None:
    """
    Advances the watermark for a source. Call this ONLY after a successful
    Drive write — not before, not on partial success.
    """
    assert source in SOURCES, f"Unknown source: {source}"
    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO watermarks (source, last_loaded)
            VALUES (?, ?)
            ON CONFLICT(source) DO UPDATE SET last_loaded = excluded.last_loaded
            """,
            (source, loaded_through.isoformat()),
        )
        conn.commit()
    print(f"  [watermark] {source} → {loaded_through.isoformat()}")


def get_all_watermarks() -> dict[str, date | None]:
    """Returns watermarks for all sources. Useful for run summary logging."""
    return {source: get_watermark(source) for source in SOURCES}
