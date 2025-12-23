import asyncio
import urllib.request

from mcp_server import MCPServer, ToolStatus


class FakeResp:
    def __init__(self, data: bytes):
        self._data = data

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_fetch_url_success(tmp_path, monkeypatch):
    # Use a mcp server with HOME pointed to tmp_path
    monkeypatch.setenv("HOME", str(tmp_path))
    m = MCPServer()

    def fake_urlopen(req, timeout=0):
        return FakeResp(b"<html><body>Hello <b>World</b></body></html>")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    res = asyncio.run(m.fetch_url({"url": "http://example.com", "maxlen": 50}))
    assert res.status == ToolStatus.SUCCESS
    assert "Hello World" in res.data["text"]
    assert res.data["url"] == "http://example.com"


def test_fetch_url_no_url(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    m = MCPServer()
    res = asyncio.run(m.fetch_url({}))
    assert res.status == ToolStatus.ERROR
    assert "No URL" in res.error or "No URL provided" in res.error
