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


import ast


def _extract_test_metadata(nodeid: str) -> dict:
    """Extract metadata for a test node id like 'tests/foo.py::test_bar'.

    Returns: { 'file': str, 'func': str, 'description': str|None, 'line': int|None, 'markers': list[str] }
    """
    parts = nodeid.split("::")
    file_part = parts[0] if parts else nodeid
    func_part = parts[1] if len(parts) > 1 else None
    out = {"file": file_part, "func": func_part, "description": None, "line": None, "markers": []}

    try:
        with open(file_part, "r", encoding="utf-8") as fh:
            src = fh.read()
        module = ast.parse(src)
        # Find the function
        for node in module.body:
            if isinstance(node, ast.FunctionDef) and node.name == func_part:
                out["description"] = ast.get_docstring(node) or None
                out["line"] = getattr(node, "lineno", None)
                # Inspect decorators for pytest.mark.*
                markers = []
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Attribute):
                        # e.g., pytest.mark.slow
                        try:
                            if isinstance(dec.value, ast.Attribute) and isinstance(dec.value.value, ast.Name) and dec.value.value.id == "pytest":
                                markers.append(dec.attr)
                        except Exception:
                            pass
                    elif isinstance(dec, ast.Call):
                        # e.g., pytest.mark.parametrize(...) or pytest.mark.live
                        func = dec.func
                        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Attribute):
                            # pytest.mark.something
                            if isinstance(func.value.value, ast.Name) and func.value.value.id == "pytest":
                                markers.append(func.attr)
                        elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "pytest":
                            markers.append(func.attr)
                out["markers"] = markers
                break
    except Exception:
        # best-effort only; don't fail because of metadata extraction
        pass
    return out


def build_cards_from_events(by_test: Dict[str, List[dict]]) -> List[dict]:
    """Convert grouped events into a list of cards (test, prompt, answer, parsed_tool), enriched with metadata."""
    cards: List[dict] = []
    for test, evs in by_test.items():
        prompt = ""
        answer = ""
        parsed = None
        timestamps = {}
        for e in evs:
            if e.get("event") == "PROMPT":
                prompt = e.get("payload", {}).get("prompt", "")
                timestamps.setdefault("prompt_ts", e.get("ts"))
            elif e.get("event") == "ASSISTANT":
                answer = e.get("payload", {}).get("content", "")
                timestamps.setdefault("assistant_ts", e.get("ts"))
            elif e.get("event") == "PARSED_TOOL":
                parsed = e.get("payload")
                timestamps.setdefault("parsed_ts", e.get("ts"))
        meta = _extract_test_metadata(test)
        # Determine intention/result hint
        intent = "No model interaction expected"
        if "live" in (test or "") or any("live" == m for m in meta.get("markers", [])):
            intent = "Live model integration — expected a model-emitted tool call"
        if answer and answer != "(no model call)":
            intent = "Model interaction recorded"

        # If there's no prompt recorded, try to extract a code snippet (first few lines of the test function)
        test_snippet = None
        try:
            tf = meta.get("file")
            ln = meta.get("line")
            if tf and ln and os.path.exists(tf):
                with open(tf, "r", encoding="utf-8", errors="ignore") as fh:
                    lines = fh.read().splitlines()
                # grab up to 6 lines starting at the function line
                start = max(ln - 1, 0)
                snippet = lines[start : start + 6]
                test_snippet = "\n".join(snippet).strip()
        except Exception:
            test_snippet = None

        card = {
            "test": test,
            "file": meta.get("file"),
            "line": meta.get("line"),
            "markers": meta.get("markers", []),
            "description": meta.get("description") or "(no test description)",
            "test_snippet": test_snippet,
            "prompt": prompt or "(no prompt logged)",
            "answer": answer or "(no model call)",
            "parsed_tool": parsed,
            "intent": intent,
            "timestamps": timestamps,
        }
        cards.append(card)
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

    # Use timezone-aware UTC timestamp
    out = {"generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "cards": cards}
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
