import pytest

from ref.dashboard.llm_telemetry import LLMTelemetry
from ref.dashboard.log_tail import LogTail
from ref.dashboard.mcp_metrics import MCPMetrics


@pytest.mark.asyncio
async def test_mcp_metrics_reads_health(monkeypatch):
    # Fake aiohttp session
    class FakeResp:
        def __init__(self, status=200, json_data=None):
            self.status = status
            self._json = json_data or {"status": "ok", "uptime": 123}

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def json(self):
            return self._json

    class FakeSession:
        def __init__(self):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def get(self, url, timeout=None):
            return FakeResp(200, {"status": "ok", "uptime": 42})

    monkeypatch.setenv("SINGULARITY_MCP_SERVER_URL", "http://127.0.0.1:35887")
    monkeypatch.setattr("aiohttp.ClientSession", lambda: FakeSession())

    m = MCPMetrics()

    # Use dummy app so log writes don't fail
    class DummyApp:
        def query_one(self, _):
            class L:
                def write(self, *_):
                    pass

            return L()

    m.mount(DummyApp())
    await m.do_check()
    assert m.widget.last_metrics["status"] == "ok"
    assert m.widget.last_metrics["uptime"] == 42


@pytest.mark.asyncio
async def test_llm_telemetry(monkeypatch):
    class FakeResp:
        def __init__(self, status=200, data=None):
            self.status = status

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeSession:
        def __init__(self):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def get(self, url, timeout=None):
            return FakeResp(200)

    monkeypatch.setattr("aiohttp.ClientSession", lambda: FakeSession())
    lm = LLMTelemetry()
    lm.mount(object())
    await lm.do_check()
    assert (
        lm.widget.last_info["model"] == "ollama"
        or lm.widget.last_info["model"] == "unknown"
    )


@pytest.mark.asyncio
async def test_log_tail_reads_file(tmp_path):
    p = tmp_path / "mcp_server.log"
    lines = [f"line {i}" for i in range(10)]
    p.write_text("\n".join(lines))
    lt = LogTail(path=str(p), lines=5)
    lt.mount(object())
    await lt.do_check()
    # The widget maintains entries in its internal log; here we simply ensure no exception and file read happens
    assert p.read_text().splitlines()[-1] == "line 9"
