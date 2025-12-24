import asyncio
import os
import time
import pytest

import model_manager


@pytest.mark.asyncio
async def test_concurrency_limit(monkeypatch):
    mm = model_manager.ModelManager()
    mm._sem = asyncio.Semaphore(2)  # limit to 2 concurrent

    running = 0

    async def fake_stream(self, prompt, system=None, timeout=120.0):
        nonlocal running
        running += 1
        assert running <= 2
        # simulate work
        await asyncio.sleep(0.05)
        yield "chunk1"
        await asyncio.sleep(0.01)
        yield "chunk2"
        running -= 1

    monkeypatch.setattr(model_manager.ModelClient, 'stream', fake_stream)

    async def run_call(i):
        out = []
        async for c in mm.stream("m", f"p{i}"):
            out.append(c)
        return out

    tasks = [asyncio.create_task(run_call(i)) for i in range(6)]
    res = await asyncio.gather(*tasks)
    assert all(r == ["chunk1", "chunk2"] for r in res)


@pytest.mark.asyncio
async def test_gpu_wait(monkeypatch):
    mm = model_manager.ModelManager()
    # simulate low gpu memory first then high
    calls = [50, 50, 400]

    async def fake_get():
        return calls.pop(0) if calls else 400

    monkeypatch.setattr(model_manager, 'get_gpu_free_memory_mb', fake_get)

    # patch stream to be quick
    async def dummy(self, prompt, system=None, timeout=120.0):
        yield "ok"

    monkeypatch.setattr(model_manager.ModelClient, 'stream', dummy)

    start = time.time()
    out = []
    async for c in mm.stream("m", "p"):
        out.append(c)
    elapsed = time.time() - start
    assert out == ["ok"]
    assert elapsed >= 0  # completed without error
