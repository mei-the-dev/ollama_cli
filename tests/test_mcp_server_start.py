import asyncio
import types
import pytest
import json
from pathlib import Path

import singularity_cli


class FakeStdout:
    def __init__(self, lines, delay=0.0):
        self._lines = list(lines)
        self._delay = delay

    def __aiter__(self):
        async def gen():
            while self._lines:
                l = self._lines.pop(0)
                if self._delay:
                    await asyncio.sleep(self._delay)
                yield l.encode() if isinstance(l, str) else l
        return gen()

    async def readline(self):
        # emulate StreamReader.readline: return one line at a time
        if not self._lines:
            await asyncio.sleep(0.01)
            return b""
        l = self._lines.pop(0)
        await asyncio.sleep(self._delay)
        return l.encode() if isinstance(l, str) else l


class FakeProcess:
    def __init__(self, stdout_lines):
        self.stdout = FakeStdout(stdout_lines)
        self.returncode = 0

    async def wait(self):
        return self.returncode

    def terminate(self):
        self.returncode = 0

    def kill(self):
        self.returncode = -9


def test_parse_listen_line_variants():
    examples = [
        ("MCP server listening on 127.0.0.1:54321", "http://127.0.0.1:54321"),
        ("listening on 0.0.0.0:12345", "http://0.0.0.0:12345"),
        ("Server started at http://127.0.0.1:2222", "http://127.0.0.1:2222"),
        ("no useful info here", None),
    ]

    for line, expected in examples:
        assert singularity_cli.SingularityAgent._parse_mcp_listen_line(line) == expected


def test_start_mcp_server_success(monkeypatch, tmp_path):
    async def fake_create_proc(*args, **kwargs):
        return FakeProcess(["MCP server listening on 127.0.0.1:54321\n"])

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_proc)

    agent = singularity_cli.SingularityAgent()

    # Ensure events file is present to assert no PARSED_TOOL emitted by server process
    import os
    events = tmp_path / "events.jsonl"
    monkeypatch.setenv("TEST_MODEL_EVENTS_PATH", str(events))

    result = asyncio.run(agent.start_mcp_server(timeout=1.0))
    assert result is True
    assert agent.mcp_server_url == "http://127.0.0.1:54321"

    if events.exists():
        evs = [json.loads(l) for l in events.read_text(encoding='utf-8').splitlines() if l.strip()]
        assert not any(e.get('event') == 'PARSED_TOOL' for e in evs)


def test_start_mcp_server_timeout(monkeypatch):
    async def fake_create_proc_no_announce(*args, **kwargs):
        # provide stdout that never yields the listening line
        p = FakeProcess(["Starting up...\n", "Still loading...\n"]) 
        # Add an informative stderr line
        p.stderr = FakeStdout(["Error: address already in use\n"])
        return p

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_proc_no_announce)

    agent = singularity_cli.SingularityAgent()

    result = asyncio.run(agent.start_mcp_server(timeout=0.5))
    assert result is False
    assert agent.mcp_server_url is None


def test_parse_listen_line_hostname_and_ipv6():
    examples = [
        ("Serving HTTP on myhost.local:8080", "http://myhost.local:8080"),
        ("Listening on [::]:12345", "http://[::]:12345"),
    ]

    for line, expected in examples:
        assert singularity_cli.SingularityAgent._parse_mcp_listen_line(line) == expected
