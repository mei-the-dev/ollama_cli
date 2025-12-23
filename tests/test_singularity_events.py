import asyncio
import json
import os

import pytest

from singularity_cli import SingularityAgent


@pytest.mark.asyncio
async def test_events_emitted(model_event_logger, tmp_path, monkeypatch):
    # Ensure pytest fixture uses a temporary events file
    events_path = tmp_path / "events.jsonl"
    os.environ["TEST_MODEL_EVENTS_PATH"] = str(events_path)

    agent = SingularityAgent()

    # Fake streaming that returns a message containing a JSON tool call
    async def fake_generate_streaming(self, prompt, system=None):
        # Simulate incremental chunks
        yield "Partial answer... "
        yield '{"tool":"read_code","args":{"filepath":"foo.txt"}}'

    async def fake_call_mcp_tool(self, name, arguments, timeout=30.0, retries=2):
        assert name == "read_code"
        assert arguments.get("filepath") == "foo.txt"
        return {"status": "SUCCESS", "data": {"content": "hello world"}}

    monkeypatch.setattr(SingularityAgent, "generate_streaming", fake_generate_streaming)
    monkeypatch.setattr(SingularityAgent, "call_mcp_tool", fake_call_mcp_tool)

    res = await agent.process_with_tools("Please read the file foo.txt")
    assert "Executed" in res or "Executed" in res or "✓ Executed" in res

    # Read events
    lines = list(events_path.read_text().splitlines())
    events = [json.loads(l) for l in lines]

    kinds = [e.get("event") for e in events]
    assert "PROMPT" in kinds
    assert "ASSISTANT" in kinds
    assert "PARSED_TOOL" in kinds

    # Check payloads
    parsed_events = {e["event"]: e for e in events}
    assert parsed_events["PARSED_TOOL"]["payload"]["tool"] == "read_code"
    assert parsed_events["PARSED_TOOL"]["payload"]["args"]["filepath"] == "foo.txt"

    # Clean up env
    os.environ.pop("TEST_MODEL_EVENTS_PATH", None)
