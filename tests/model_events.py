"""Lightweight model event helper used by tests and the pytest plugin.

Provides a simple in-test API to emit structured events that are persisted to a
JSONL file and consumed by the test reporter.

Event schema (per line / JSON object):
{
  "ts": "2025-12-22T23:00:00.000Z",
  "test": "tests/test_foo.py::test_bar",
  "event": "PROMPT" | "ASSISTANT" | "PARSED_TOOL",
  "payload": { ... }
}
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

DEFAULT_EVENTS_PATH = Path("logs/test_model_events.jsonl")


@dataclass
class ModelEvent:
    ts: str
    test: str
    event: str
    payload: Dict[str, Any]

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


class ModelEventLogger:
    def __init__(self, test_node: str, out_path: str | None = None):
        self.test_node = test_node
        self._events: list[ModelEvent] = []
        self.out_path = Path(out_path) if out_path else DEFAULT_EVENTS_PATH
        # Ensure parent dir exists
        try:
            self.out_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def emit(self, event: str, payload: Dict[str, Any]):
        """Record an event in-memory and append to the JSONL file.

        `event` is a short string (PROMPT/ASSISTANT/PARSED_TOOL).
        `payload` is a JSON-serializable dict.
        """
        # Use timezone-aware UTC timestamps to avoid deprecation warnings
        ts = datetime.now(timezone.utc).isoformat()
        ev = ModelEvent(ts=ts, test=self.test_node, event=event, payload=payload)
        self._events.append(ev)
        # Append to file immediately so external tools can read streaming
        try:
            with open(self.out_path, "a", encoding="utf-8") as fh:
                fh.write(ev.to_json() + "\n")
        except Exception:
            # best-effort logging; do not raise from tests
            pass

    def events(self) -> list[ModelEvent]:
        return list(self._events)
