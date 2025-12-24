import asyncio
import pytest

import singularity_cli


@pytest.mark.asyncio
async def test_execute_loop_steps(monkeypatch):
    agent = singularity_cli.SingularityAgent()

    seq = ["✓ Executed write_code: {...}", "Final answer: done"]

    async def fake_process(prompt, system=None, execute_tools=True):
        return seq.pop(0)

    monkeypatch.setattr(agent, 'process_with_tools', fake_process)

    steps = await agent.execute_loop('Generate code', system=None, max_steps=5)

    assert len(steps) == 2
    assert steps[0].response.startswith('✓ Executed')
    assert steps[1].completed is True
