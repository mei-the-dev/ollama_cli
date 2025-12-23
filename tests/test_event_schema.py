import json
import os

from tests.reporting import get_event_schema, validate_jsonl_events


def test_event_schema_and_validation(tmp_path):
    # Minimal valid event
    valid = {"ts":"t","test":"t1","event":"PROMPT","payload":{"prompt":"hello"}}
    invalid = {"ts":123,"test":"t1","event":"PROMPT","payload":"not-a-dict"}

    p = tmp_path / "events.jsonl"
    p.write_text(json.dumps(valid) + "\n" + json.dumps(invalid) + "\n")

    schema = get_event_schema()
    assert "properties" in schema

    errs = validate_jsonl_events(str(p))
    assert len(errs) == 1
    assert errs[0][0] == 2
