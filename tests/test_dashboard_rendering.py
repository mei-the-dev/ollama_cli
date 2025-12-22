import pytest
from ref.omarchy_dashboard import OmarchyDashboard

@pytest.mark.asyncio
async def test_dashboard_kpi_updates(monkeypatch):
    # Fake MCP health endpoint returning telemetry
    class FakeResp:
        def __init__(self, status=200, json_data=None):
            self.status = status
            self._json = json_data or {'telemetry': {'reqs_last_minute': 60, 'p50_ms': 5.0, 'p95_ms': 10.0, 'gpu_memory_mb': 1000}}
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
            return FakeResp(200, {'telemetry': {'reqs_last_minute': 60, 'p50_ms': 5.0, 'p95_ms': 10.0, 'gpu_memory_mb': 1000}})
        def post(self, url, json=None, timeout=None):
            return FakeResp(200)

    monkeypatch.setenv('OMARCHY_MCP_SERVER_URL', 'http://127.0.0.1:35887')
    monkeypatch.setattr('aiohttp.ClientSession', lambda: FakeSession())

    app = OmarchyDashboard()
    app.register_modules()
    app.mount_modules()

    # run each module's do_check and verify dashboard kpi placeholders updated
    for m in app.modules:
        if hasattr(m, 'do_check'):
            await m.do_check()

    # Now assert KPI placeholders reflect expected values
    assert app.get_kpi_text('#kpi-reqs') is not None and 'Req/s' in app.get_kpi_text('#kpi-reqs')
    assert app.get_kpi_text('#kpi-lat') is not None and 'Latency' in app.get_kpi_text('#kpi-lat')
    assert app.get_kpi_text('#kpi-mcp') is not None and 'MCP' in app.get_kpi_text('#kpi-mcp')
    assert app.get_kpi_text('#kpi-ollama') is not None and 'Ollama' in app.get_kpi_text('#kpi-ollama')
