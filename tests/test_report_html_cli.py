import json
import sys
import io
from pathlib import Path

from scripts import test_report


def test_report_exports_html(tmp_path, monkeypatch):
    events = tmp_path / "events.jsonl"
    lines = [
        json.dumps({"ts":"t","test":"t1","event":"PROMPT","payload":{"prompt":"hi"}}),
        json.dumps({"ts":"t","test":"t1","event":"ASSISTANT","payload":{"content":"world"}}),
    ]
    events.write_text("\n".join(lines))

    monkeypatch.setenv("TEST_MODEL_EVENTS_PATH", str(events))

    out = tmp_path / "report.json"
    out_html = tmp_path / "report.html"

    # Instead of invoking the CLI which pipes stdin, call the underlying helpers directly
    from tests.reporting import parse_jsonl_events, build_cards_from_events, export_report_json
    from scripts.export_report_html import export_html

    by = parse_jsonl_events(str(events))
    cards = build_cards_from_events(by)
    export_report_json(cards, str(out))
    export_html(str(out), str(out_html))

    assert out_html.exists()
    assert "Test Report" in out_html.read_text()
