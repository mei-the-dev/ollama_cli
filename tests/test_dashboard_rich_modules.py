import pytest
from ref.dashboard.request_rate import RequestRate
from ref.dashboard.latency_graph import LatencyGraph
from ref.dashboard.gpu_widget import GPUMetrics

@pytest.mark.asyncio
async def test_request_rate_module(monkeypatch):
    class FakeResp:
        def __init__(self, status=200, json_data=None):
            self.status = status
            self._json = json_data or {'telemetry': {'reqs_last_minute': 120}}
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
            return FakeResp(200, {'telemetry': {'reqs_last_minute': 120}})

    monkeypatch.setenv('SINGULARITY_MCP_SERVER_URL', 'http://127.0.0.1:35887')
    monkeypatch.setattr('aiohttp.ClientSession', lambda: FakeSession())

    m = RequestRate()
    m.mount(object())
    await m.do_check()
    assert len(m.widget.history) >= 1

    # Ensure dashboard quickly registers and mounts modules into KPI slots
    from ref.singularity_dashboard import SingularityDashboard
    app = SingularityDashboard()
    app.register_modules()
    app.mount_modules()
    assert hasattr(app, '_widget_registry')
    assert any(hasattr(w, 'update') for w in app._widget_registry)


@pytest.mark.asyncio
async def test_latency_and_gpu_modules(monkeypatch):
    class FakeResp:
        def __init__(self, status=200, json_data=None):
            self.status = status
            self._json = json_data or {'telemetry': {'p50_ms': 5.0, 'p95_ms': 10.0, 'avg_latency_ms': 6.0, 'gpu_memory_mb': 4096}}
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
            return FakeResp(200, {'telemetry': {'p50_ms': 5.0, 'p95_ms': 10.0, 'avg_latency_ms': 6.0, 'gpu_memory_mb': 4096}})

    monkeypatch.setenv('SINGULARITY_MCP_SERVER_URL', 'http://127.0.0.1:35887')
    monkeypatch.setattr('aiohttp.ClientSession', lambda: FakeSession())

    lat = LatencyGraph()
    gpu = GPUMetrics()
    lat.mount(object())
    gpu.mount(object())
    await lat.do_check()
    await gpu.do_check()
    assert lat.widget.last['p50'] >= 0
    assert gpu.widget.last == 4096
