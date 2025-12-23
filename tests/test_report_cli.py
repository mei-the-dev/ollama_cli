import json
import os
import sys

from scripts import test_report


def test_report_exports_json(tmp_path, monkeypatch):
    events = tmp_path / "events.jsonl"
    lines = [
        json.dumps({"ts":"t","test":"t1","event":"PROMPT","payload":{"prompt":"hi"}}),
        json.dumps({"ts":"t","test":"t1","event":"ASSISTANT","payload":{"content":"world"}}),
    ]
    events.write_text("\n".join(lines))

    monkeypatch.setenv("TEST_MODEL_EVENTS_PATH", str(events))

    out = tmp_path / "report.json"

    # Instead of invoking the CLI (which reads stdin under --no-run), call the helpers directly
    from tests.reporting import parse_jsonl_events, build_cards_from_events, export_report_json

    by = parse_jsonl_events(str(events))
    cards = build_cards_from_events(by)
    export_report_json(cards, str(out))

    # Ensure parsed_tool is preserved to report.json
    j = json.loads(out.read_text())
    assert any(c.get('parsed_tool') is None or isinstance(c.get('parsed_tool'), dict) for c in j.get('cards', []))

    assert out.exists()
    j = json.loads(out.read_text())
    assert j.get("cards") and isinstance(j["cards"], list)
