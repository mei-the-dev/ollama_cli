import asyncio
import json
import pytest

import singularity_cli


async def fake_stream_gen(chunks):
    for c in chunks:
        await asyncio.sleep(0)
        yield c


def test_extract_json_object_various():
    cases = [
        ('Here is {"tool":"write_code","args":{"path":"a.txt"}} done', '{"tool":"write_code","args":{"path":"a.txt"}}'),
        ('```json\n{"tool":"x","args":{}}\n```', '{"tool":"x","args":{}}'),
        ('prefix {"a": {"b": 1}} suffix', '{"a": {"b": 1}}'),
        ('no json here', None),
    ]
    for text, expected in cases:
        res = singularity_cli.SingularityAgent._extract_json_object(text)
        assert res == expected


@pytest.mark.asyncio
async def test_process_with_tools_calls_mcp(monkeypatch, tmp_path, model_event_logger):
    # Ensure events are written to a temp JSONL file
    events = tmp_path / "events.jsonl"
    monkeypatch.setenv("TEST_MODEL_EVENTS_PATH", str(events))

    agent = singularity_cli.SingularityAgent()

    # Simulate streaming output that yields chunks culminating in a JSON tool call
    chunks = ['Hello ', '{"tool": "test_tool", "args": {"x": 1}}']

    async def gen(prompt, system=None, timeout=120.0):
        async for c in fake_stream_gen(chunks):
            yield c

    agent.generate_streaming = gen

    # Mock call_mcp_tool to assert it's called and return success
    async def fake_call(name, args, timeout=30.0, retries=2):
        assert name == 'test_tool'
        assert args == {'x': 1}
        return {'status': 'SUCCESS', 'data': {'ok': True}}

    monkeypatch.setattr(agent, 'call_mcp_tool', fake_call)

    res = await agent.process_with_tools('do the thing')
    assert 'Executed' in res or res.startswith('✓')

    # Verify that structured events were emitted
    lines = list(events.read_text(encoding='utf-8').splitlines())
    evs = [json.loads(l) for l in lines]
    kinds = [e.get('event') for e in evs]
    assert 'PROMPT' in kinds
    assert 'ASSISTANT' in kinds
    assert 'PARSED_TOOL' in kinds

    parsed = next(e for e in evs if e.get('event') == 'PARSED_TOOL')
    assert parsed['payload']['tool'] == 'test_tool'
    assert parsed['payload']['args'] == {'x': 1}
    # raw payload should preserve the original parsed object when available
    assert isinstance(parsed['payload'].get('raw'), dict)
    assert parsed['payload']['raw'].get('tool') == 'test_tool'

@pytest.mark.asyncio
async def test_process_with_tools_normalizes_file_path(monkeypatch, tmp_path, model_event_logger):
    monkeypatch.setenv("TEST_MODEL_EVENTS_PATH", str(tmp_path / "events.jsonl"))
    monkeypatch.setenv("SINGULARITY_SANDBOX", str(tmp_path))
    agent = singularity_cli.SingularityAgent()

    target = str(tmp_path / "live_test.txt")
    chunks = [
        '```json\n{\n  "tool": "write_file",\n  "args": {\n    "file_path": "',
        target,
        '",\n    "content": "hello"\n  }\n}\n```',
    ]

    async def gen(prompt, system=None, timeout=120.0):
        async for c in fake_stream_gen(chunks):
            yield c

    agent.generate_streaming = gen

    # Mock call_mcp_tool to assert sanitized args
    async def fake_call(name, args, timeout=30.0, retries=2):
        assert name == 'write_code'
        # Original absolute path must be preserved and sanitized filepath must be under sandbox
        assert args.get('original_filepath') == target
        assert args.get('content') == 'hello'
        assert str(args.get('filepath')).startswith(str(tmp_path))
        return {'status': 'SUCCESS', 'data': {'ok': True}}

    monkeypatch.setattr(agent, 'call_mcp_tool', fake_call)

    res = await agent.process_with_tools('please write the file')
    assert 'Executed' in res or res.startswith('✓')

    # Verify events
    lines = list((tmp_path / "events.jsonl").read_text(encoding='utf-8').splitlines())
    evs = [json.loads(l) for l in lines]
    assert any(e.get('event') == 'PARSED_TOOL' and e.get('payload', {}).get('tool') == 'write_code' for e in evs)
    parsed = next(
        e
        for e in evs
        if e.get('event') == 'PARSED_TOOL'
        and (
            e.get('payload', {}).get('args', {}).get('original_filepath')
            or str(e.get('payload', {}).get('args', {}).get('filepath', '')).startswith(str(tmp_path))
        )
    )
    # Parsed args should now include sanitized filepath or original_filepath preserved
    assert parsed['payload']['args'].get('original_filepath') == target or parsed['payload']['args'].get('filepath', '').startswith(str(tmp_path))
    assert parsed['payload']['args'].get('content') == 'hello'
    # raw original object is preserved
    assert isinstance(parsed['payload'].get('raw'), dict)
    assert 'file_path' in parsed['payload']['raw'].get('args', {}) or 'filepath' in parsed['payload']['raw'].get('args', {})
