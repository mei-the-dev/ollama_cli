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
async def test_process_with_tools_calls_mcp(monkeypatch):
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


@pytest.mark.asyncio
async def test_process_with_tools_normalizes_file_path(monkeypatch, tmp_path):
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

    # Mock call_mcp_tool to assert normalized args
    async def fake_call(name, args, timeout=30.0, retries=2):
        assert name == 'write_code'
        assert args.get('filepath') == target
        assert args.get('content') == 'hello'
        return {'status': 'SUCCESS', 'data': {'ok': True}}

    monkeypatch.setattr(agent, 'call_mcp_tool', fake_call)

    res = await agent.process_with_tools('please write the file')
    assert 'Executed' in res or res.startswith('✓')

