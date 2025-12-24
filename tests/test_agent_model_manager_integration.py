import asyncio
import pytest

import singularity_cli
import model_manager


@pytest.mark.asyncio
async def test_generate_streaming_uses_model_manager(monkeypatch):
    cli = singularity_cli.SingularityCLI()

    # Fake manager with a stream that yields two chunks
    class FakeMgr:
        async def stream(self, model, prompt, system=None, timeout=120.0):
            yield "chunk1"
            yield "chunk2"

    fake = FakeMgr()

    monkeypatch.setattr(model_manager, 'get_default_manager', lambda: fake)

    got = []
    async for c in cli.agent.generate_streaming("hello", system="s", timeout=1.0):
        got.append(c)

    assert got == ["chunk1", "chunk2"]
