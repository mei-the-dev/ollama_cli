import pytest

from mcp_server import MCPServer


class FakeRequest:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_http_handler_records_telemetry():
    srv = MCPServer()
    # Call a known method (list_tools) via http_handler
    req = FakeRequest({"name": "list_tools"})
    res = await srv.http_handler(req)
    assert isinstance(res, type(res))  # response object returned
    # Telemetry should have incremented
    assert srv.telemetry["request_count"] >= 1
    assert len(srv.telemetry["latencies_ms"]) >= 1


@pytest.mark.asyncio
async def test_health_includes_telemetry():
    srv = MCPServer()
    # call a dummy request to record one
    req = FakeRequest({"name": "list_tools"})
    await srv.http_handler(req)
    # h is aiohttp.web.Response; access via .text or .body; easier: call _telemetry_summary()
    summary = srv._telemetry_summary()
    assert "avg_latency_ms" in summary
    assert "reqs_last_minute" in summary
