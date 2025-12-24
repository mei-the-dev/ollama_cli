import asyncio
import json

import pytest
from mcp_server import MCPServer


class FakeRequest:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_http_handler_wraps_non_toolresult():
    server = MCPServer()
    payload = {"name": "read_code", "arguments": {"filepath": __file__}}
    req = FakeRequest(payload)

    resp = await server.http_handler(req)
    # Should be an aiohttp.web.Response-like with body bytes
    body = resp.body if hasattr(resp, "body") else resp._body
    assert b'"status"' in body
    j = json.loads(body.decode())
    assert j.get("status") in ("SUCCESS", "ERROR")
    assert "data" in j


@pytest.mark.asyncio
async def test_http_handler_unknown_tool_returns_400():
    server = MCPServer()
    payload = {"name": "nonexistent_tool", "arguments": {}}
    req = FakeRequest(payload)
    resp = await server.http_handler(req)
    assert resp.status == 400
    body = resp.body if hasattr(resp, "body") else resp._body
    j = json.loads(body.decode())
    assert "error" in j
