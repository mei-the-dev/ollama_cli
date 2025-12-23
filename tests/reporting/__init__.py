"""Reporting helpers used by scripts/test_report.py

Export a few small helpers for parsing structured JSONL model events and building
cards suitable for the test reporter. Kept lightweight and with minimal runtime
dependencies to remain importable inside test runs.
"""
from __future__ import annotations

import json
from typing import Dict, List


from .models import ModelEvent, Card


def parse_jsonl_events(path: str) -> Dict[str, List[dict]]:
    """Parse a JSONL file at `path` and return events grouped by test node id."""
    by_test: Dict[str, List[dict]] = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                j = json.loads(line)
            except Exception:
                continue
            t = j.get("test") or "unknown"
            by_test.setdefault(t, []).append(j)
    return by_test


def validate_event(obj: dict) -> ModelEvent | None:
    """Validate a single event dict against the ModelEvent pydantic model.

    Returns the parsed ModelEvent on success, or None on validation failure.
    """
    try:
        return ModelEvent(**obj)
    except Exception:
        return None


def validate_cards(cards: list) -> list:
    """Validate a list of card dicts; returns list of Card instances for valid ones."""
    out = []
    for c in cards:
        try:
            out.append(Card(**c))
        except Exception:
            continue
    return out


def build_cards_from_events(by_test: Dict[str, List[dict]]) -> List[dict]:
    """Convert grouped events into a list of cards (test, prompt, answer, parsed_tool)."""
    cards: List[dict] = []
    for test, evs in by_test.items():
        prompt = ""
        answer = ""
        parsed = None
        for e in evs:
            if e.get("event") == "PROMPT":
                prompt = e.get("payload", {}).get("prompt", "")
            elif e.get("event") == "ASSISTANT":
                answer = e.get("payload", {}).get("content", "")
            elif e.get("event") == "PARSED_TOOL":
                parsed = e.get("payload")
        cards.append({"test": test, "prompt": prompt or "(no prompt logged)", "answer": answer or "(no model call)", "parsed_tool": parsed})
    # Keep stable ordering by test id
    cards.sort(key=lambda c: c.get("test", ""))
    return cards


def export_report_json(cards: List[dict], path: str):
    """Write canonical report JSON to `path`.

    The schema is deliberately small and intended for CI consumption:
    {
        "generated_at": "iso-ts",
        "cards": [ {test,prompt,answer,parsed_tool}, ... ]
    }
    """
    import datetime

    out = {"generated_at": datetime.datetime.utcnow().isoformat() + "Z", "cards": cards}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)


# --- Schema & validation helpers ---

def get_event_schema() -> dict:
    """Return a JSON Schema-like dict describing a ModelEvent.

    If Pydantic is available, prefer generating the schema from the model. If not,
    provide a small hand-written schema to use for basic validation.
    """
    try:
        # pydantic (v1 or v2) supports schema() on models
        s = ModelEvent.schema()  # type: ignore[attr-defined]
        return s
    except Exception:
        # Fallback minimal schema
        return {
            "type": "object",
            "properties": {
                "ts": {"type": "string"},
                "test": {"type": "string"},
                "event": {"type": "string"},
                "payload": {"type": "object"},
            },
            "required": ["ts", "test", "event", "payload"],
        }


def validate_jsonl_events(path: str) -> list:
    """Validate each line in a JSONL file using `validate_event`.

    Returns a list of tuples (line_number, error_message) for invalid lines.
    """
    errs = []
    with open(path, "r", encoding="utf-8") as fh:
        for i, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                j = json.loads(raw)
            except Exception as e:
                errs.append((i, f"invalid json: {e}"))
                continue
            ve = validate_event(j)
            if ve is None:
                errs.append((i, "schema validation failed"))
    return errs
