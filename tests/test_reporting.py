import json
import os

from tests.reporting import parse_jsonl_events, build_cards_from_events, export_report_json


def test_reporting_parse_and_build(tmp_path):
    p = tmp_path / "events.jsonl"
    lines = [
        json.dumps({"ts":"t","test":"t1","event":"PROMPT","payload":{"prompt":"hello"}}),
        json.dumps({"ts":"t","test":"t1","event":"ASSISTANT","payload":{"content":"world"}}),
        json.dumps({"ts":"t","test":"t2","event":"PROMPT","payload":{"prompt":"ask"}}),
    ]
    p.write_text("\n".join(lines))

    by = parse_jsonl_events(str(p))
    assert "t1" in by and "t2" in by

    cards = build_cards_from_events(by)
    assert any(c["test"] == "t1" and c["answer"].strip() == "world" for c in cards)

    # Ensure PARSED_TOOL raw payloads are preserved end-to-end
    p2 = tmp_path / "events2.jsonl"
    p2.write_text('\n'.join([
        json.dumps({"ts":"t","test":"t1","event":"PROMPT","payload":{"prompt":"hi"}}),
        json.dumps({"ts":"t","test":"t1","event":"PARSED_TOOL","payload":{"tool":"write_code","args":{"filepath":"/tmp/x","content":"hi"},"raw":{"tool":"write_code","args":{"filepath":"/tmp/x"}}}})
    ]))
    by2 = parse_jsonl_events(str(p2))
    cards2 = build_cards_from_events(by2)
    assert any(c.get('parsed_tool') and c['parsed_tool']['tool'] == 'write_code' for c in cards2)

    out = tmp_path / "report.json"
    export_report_json(cards, str(out))
    obj = json.loads(out.read_text())
    assert "generated_at" in obj and "cards" in obj
