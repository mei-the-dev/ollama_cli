import os
import re
from pathlib import Path

import pytest

from tests.event_assertions import read_events

PLACEHOLDER_RX = re.compile(r"placeholder response|this environment provides a placeholder|use /mode code", re.I)


def _read_log(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def test_no_placeholders_in_singularity_log():
    """Fail if known placeholder text appears in `logs/singularity.log`."""
    log = _read_log(os.path.join(os.getcwd(), "logs", "singularity.log"))
    assert not PLACEHOLDER_RX.search(log), "Found placeholder text in logs/singularity.log"


def test_no_placeholders_in_event_jsonl():
    """Fail if known placeholder text appears in `TEST_MODEL_EVENTS_PATH` JSONL."""
    events_path = os.environ.get("TEST_MODEL_EVENTS_PATH") or os.path.join(os.getcwd(), "logs", "test_model_events.jsonl")
    evs = []
    try:
        evs = read_events(events_path)
    except Exception:
        pass

    for e in evs:
        content = ""
        payload = e.get("payload") or {}
        # Check both assistant content and any raw answer fields
        content = " ".join(str(payload.get(k, "")) for k in ("content", "answer", "raw", "text") if payload.get(k))
        if content and PLACEHOLDER_RX.search(content):
            pytest.fail(f"Found placeholder text in {events_path}: {content}")
