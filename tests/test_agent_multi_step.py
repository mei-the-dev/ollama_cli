import asyncio
import pytest

import singularity_cli


@pytest.mark.asyncio
async def test_run_multi_step_executes_tool(monkeypatch):
    agent = singularity_cli.SingularityAgent()

    # Prepare generator that yields tool call in first step and then a completion message
    steps = [
        ["Step 1 text ", '{"tool": "write_code", "args": {"filepath": "./out.py", "content": "print(1)"}}'],
        ["Step 2 final TASK_COMPLETE"]
    ]

    async def gen(prompt, system=None, timeout=120.0):
        # Use first available batch
        batch = gen.batches.pop(0)
        for c in batch:
            yield c

    gen.batches = steps.copy()
    monkeypatch.setattr(agent, 'generate_streaming', gen)

    called = {}

    async def fake_call(name, args, timeout=30.0, retries=2):
        called['name'] = name
        called['args'] = args
        return {'status': 'SUCCESS', 'data': {'ok': True}}

    monkeypatch.setattr(agent, 'call_mcp_tool', fake_call)

    await agent.run_multi_step('Do a thing', max_steps=3)

    res = getattr(agent, 'last_multi_steps', None)
    assert res is not None
    assert len(res) >= 1
    # First step had a tool call
    first = res[0]
    assert first.tool_call is not None
    assert called.get('name') == 'write_code'
    # Last step should be marked completed due to TASK_COMPLETE
    assert any(s.completed for s in res)


@pytest.mark.asyncio
async def test_run_multi_step_handles_stream_error(monkeypatch):
    agent = singularity_cli.SingularityAgent()

    async def gen_err(prompt, system=None, timeout=120.0):
        raise RuntimeError('stream fail')
        yield

    monkeypatch.setattr(agent, 'generate_streaming', gen_err)

    await agent.run_multi_step('Do a thing', max_steps=2)
    res = getattr(agent, 'last_multi_steps', None)
    assert res is not None
    assert len(res) == 1
    assert 'Error during streaming' in res[0].content
