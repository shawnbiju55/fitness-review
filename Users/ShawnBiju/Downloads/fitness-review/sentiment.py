"""
transform/sentiment.py — Enrich Day One entries with sentiment + flags via Claude API.

One API call per batch (all entries for the week in a single prompt).
Returns: sentiment_score (-1.0 to 1.0), sentiment_label, fatigue_flag,
         motivation_flag, entry_summary.

Design note: we batch all entries into one call rather than one call per entry.
Cheaper, faster, and context across entries helps Claude detect patterns.
Max ~20 entries per batch to stay within token limits.
"""

import json
import anthropic
from config import ANTHROPIC_API_KEY

_BATCH_SIZE = 20
_MODEL = "claude-sonnet-4-20250514"


def enrich_with_sentiment(entries: list[dict]) -> list[dict]:
    """
    Takes a list of dayone records (with raw_text populated) and returns
    the same list with sentiment fields filled in.
    Entries without raw_text are skipped (fields stay None).
    """
    if not entries:
        return entries

    to_enrich = [e for e in entries if e.get("raw_text")]
    if not to_enrich:
        print("  [sentiment] No entries with text to enrich.")
        return entries

    print(f"  [sentiment] Enriching {len(to_enrich)} entries...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Process in batches
    enriched_map = {}
    for i in range(0, len(to_enrich), _BATCH_SIZE):
        batch = to_enrich[i:i + _BATCH_SIZE]
        batch_map = _call_claude(client, batch)
        enriched_map.update(batch_map)

    # Merge results back into original list
    for entry in entries:
        eid = entry.get("entry_id")
        if eid in enriched_map:
            entry.update(enriched_map[eid])

    print(f"  [sentiment] Done. {len(enriched_map)} entries enriched.")
    return entries


def _call_claude(client: anthropic.Anthropic, batch: list[dict]) -> dict:
    """
    Sends a batch of entries to Claude and returns a dict keyed by entry_id.
    """
    entries_payload = [
        {"entry_id": e["entry_id"], "date": e["date"], "text": e["raw_text"]}
        for e in batch
    ]

    prompt = f"""You are analyzing personal journal entries to extract fitness and wellness insights.

For each entry, return a JSON object with these fields:
- entry_id: (same as input)
- sentiment_score: float from -1.0 (very negative) to 1.0 (very positive)
- sentiment_label: "positive", "neutral", or "negative"
- fatigue_flag: true if the entry mentions tiredness, exhaustion, low energy, soreness, or recovery struggles
- motivation_flag: true if the entry mentions feeling motivated, energized, excited about training, or hitting goals
- entry_summary: 1-2 sentence summary focused on physical/mental state and any training references

Return ONLY a JSON array of objects. No preamble, no markdown, no explanation.

Entries to analyze:
{json.dumps(entries_payload, indent=2)}
"""

    try:
        response = client.messages.create(
            model=_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        results = json.loads(raw)
        return {r["entry_id"]: {
            "sentiment_score":  r.get("sentiment_score"),
            "sentiment_label":  r.get("sentiment_label"),
            "fatigue_flag":     r.get("fatigue_flag"),
            "motivation_flag":  r.get("motivation_flag"),
            "entry_summary":    r.get("entry_summary"),
        } for r in results}
    except Exception as e:
        print(f"  [sentiment] Claude API error: {e}. Entries in batch will have null sentiment.")
        return {}
