import json
from pathlib import Path

from tests.event_assertions import read_events


def test_read_and_find(tmp_path):
    p = tmp_path / "events.jsonl"
    lines = [
        json.dumps({"ts":"t","test":"t1","event":"PROMPT","payload":{"prompt":"hi"}}),
        json.dumps({"ts":"t","test":"t1","event":"PARSED_TOOL","payload":{"tool":"write_code","args":{"filepath":"/tmp/x"}}}),
    ]
    p.write_text("\n".join(lines))

    evs = read_events(str(p))
    assert any(e.get('event') == 'PARSED_TOOL' for e in evs)
