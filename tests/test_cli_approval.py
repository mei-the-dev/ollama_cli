import json
import pytest

import singularity_cli
from rich.panel import Panel


@pytest.mark.asyncio
async def test_cli_auto_execute_when_allowed(monkeypatch, tmp_path):
    # Prepare events path
    monkeypatch.setenv("TEST_MODEL_EVENTS_PATH", str(tmp_path / "events.jsonl"))

    cli = singularity_cli.SingularityCLI()
    # allow write_code by default
    cli.permissions.add_allowed("write_code")

    # Simulate agent streaming a write_code call
    agent = cli.agent
    chunks = ['Hello ', '{"tool": "write_code", "args": {"filepath": "./out.py", "content": "print(1)"}}']

    async def gen(prompt, system=None, timeout=120.0):
        for c in chunks:
            yield c

    agent.generate_streaming = gen

    # Mock call_mcp_tool to verify execution
    called = {}

    async def fake_call(name, args, timeout=30.0, retries=2):
        called['name'] = name
        called['args'] = args
        return {'status': 'SUCCESS', 'data': {'ok': True}}

    monkeypatch.setattr(agent, 'call_mcp_tool', fake_call)

    await cli.process_prompt('generate code', 'code')

    assert called.get('name') == 'write_code'
    assert called.get('args', {}).get('content') == 'print(1)'


@pytest.mark.asyncio
async def test_cli_prompt_and_execute_on_approval(monkeypatch, tmp_path):
    monkeypatch.setenv("TEST_MODEL_EVENTS_PATH", str(tmp_path / "events.jsonl"))

    cli = singularity_cli.SingularityCLI()
    # Ensure not auto-allowed
    cli.permissions.allowed_patterns.clear()

    agent = cli.agent
    chunks = ['Message ', '{"tool": "write_code", "args": {"filepath": "./out2.py", "content": "print(2)"}}']

    async def gen(prompt, system=None, timeout=120.0):
        for c in chunks:
            yield c

    agent.generate_streaming = gen

    # Approve when prompted
    monkeypatch.setattr('rich.prompt.Confirm.ask', lambda *a, **k: True)

    executed = {}

    async def fake_call(name, args, timeout=30.0, retries=2):
        executed['ok'] = True
        return {'status': 'SUCCESS', 'data': {'ok': True}}

    monkeypatch.setattr(agent, 'call_mcp_tool', fake_call)

    await cli.process_prompt('generate code', 'code')
    assert executed.get('ok') is True


@pytest.mark.asyncio
async def test_cli_prompt_denies_when_user_declines(monkeypatch, tmp_path):
    monkeypatch.setenv("TEST_MODEL_EVENTS_PATH", str(tmp_path / "events.jsonl"))

    cli = singularity_cli.SingularityCLI()
    cli.permissions.allowed_patterns.clear()

    agent = cli.agent
    chunks = ['Msg ', '{"tool": "write_code", "args": {"filepath": "./out3.py", "content": "print(3)"}}']

    async def gen(prompt, system=None, timeout=120.0):
        for c in chunks:
            yield c

    agent.generate_streaming = gen

    # Deny approval
    monkeypatch.setattr('rich.prompt.Confirm.ask', lambda *a, **k: False)

    called = {}

    async def fake_call(name, args, timeout=30.0, retries=2):
        called['ok'] = True
        return {'status': 'SUCCESS', 'data': {'ok': True}}

    monkeypatch.setattr(agent, 'call_mcp_tool', fake_call)

    await cli.process_prompt('generate code', 'code')
    assert called == {}
