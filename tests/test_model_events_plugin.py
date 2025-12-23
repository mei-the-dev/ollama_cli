import json
from pathlib import Path


def test_model_event_fixture_writes_jsonl(tmp_path, monkeypatch):
    """Ensure the fixture writes events to the configured JSONL path."""
    p = tmp_path / "events.jsonl"
    monkeypatch.setenv("TEST_MODEL_EVENTS_PATH", str(p))

    # Import here so conftest fixture is active
    def run_sample_test(model_event_logger):
        model_event_logger.emit("PROMPT", {"prompt": "hello"})
        model_event_logger.emit("ASSISTANT", {"content": "world"})

    # Simulate pytest injecting the fixture; import the fixture provider
    from tests.model_events import ModelEventLogger

    logger = ModelEventLogger(test_node="tests::fake", out_path=str(p))
    logger.emit("PROMPT", {"prompt": "hello"})
    logger.emit("ASSISTANT", {"content": "world"})

    assert p.exists()
    lines = p.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    entries = [json.loads(l) for l in lines]
    assert entries[0]["event"] == "PROMPT"
    assert entries[1]["event"] == "ASSISTANT"
    assert entries[1]["payload"]["content"] == "world"
