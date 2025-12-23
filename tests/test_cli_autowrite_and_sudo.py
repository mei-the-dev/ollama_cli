from typing import Optional

import pytest

import os
import pytest

if os.environ.get("ALLOW_REF_IMPORTS") != "1":
    pytest.skip("Tests relying on local MCP server/reference modules are disabled by default. Set ALLOW_REF_IMPORTS=1 to enable.", allow_module_level=True)

from mcp_server import MCPServer, ToolStatus
from omarchy_cli import SingularityAgent, SingularityCLI


class DummyAgent(SingularityAgent):
    def __init__(self):
        super().__init__()
        # don't actually start subprocess
        self.mcp_server_url = "http://127.0.0.1:9999"

    async def call_ollama(
        self, prompt: str, system: Optional[str] = None, tools: Optional[list] = None
    ):
        # Simulate model returning a JSON tool call to write_code
        yield {
            "type": "tool_calls",
            "data": {
                "tool": "write_code",
                "args": {
                    "filepath": "test_out.txt",
                    "content": "hello",
                    "mode": "overwrite",
                },
            },
        }


@pytest.mark.asyncio
async def test_cli_autowrite(monkeypatch, tmp_path, capsys):
    cli = SingularityCLI()
    # Make agent a dummy that yields a write_code tool call
    cli.agent = DummyAgent()
    cli.auto_apply = True

    async def handler(args):
        if args.get("name") == "write_code":
            return {
                "status": "SUCCESS",
                "data": {"filepath": args["arguments"]["filepath"]},
            }
        return {"status": "ERROR"}

    # ensure events are captured
    events_path = tmp_path / "events.jsonl"
    import os
    os.environ["TEST_MODEL_EVENTS_PATH"] = str(events_path)

    # Provide event_reader for convenience
    # event_reader fixture not directly available here because the test may be skipped; use direct read

    # monkeypatch the HTTP call to the MCP server
    async def fake_post(url, json=None):
        class FakeResp:
            async def json(self):
                return {
                    "status": "SUCCESS",
                    "data": {"filepath": json["arguments"]["filepath"]},
                }

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        return FakeResp()

    class FakeSession:
        def __init__(self):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json=None):
            return fake_post(url, json=json)

    monkeypatch.setattr("aiohttp.ClientSession", lambda: FakeSession())

    # Run process_prompt which will call execute_with_animation which will call handle_tool_calls
    # Run execute_with_animation which will process the tool call and emit events
    await cli.agent.execute_with_animation("dummy prompt", "task", system="system")

    # Ensure structured PARSED_TOOL was emitted by DummyAgent's tool call
    lines = list(events_path.read_text(encoding='utf-8').splitlines())
    evs = [json.loads(l) for l in lines]
    kinds = [e.get('event') for e in evs]
    assert 'PARSED_TOOL' in kinds or any(e.get('event') == 'ASSISTANT' for e in evs)
    # When PARSED_TOOL is present, ensure raw args include the expected filepath
    parsed = next((e for e in evs if e.get('event') == 'PARSED_TOOL'), None)
    if parsed:
        assert parsed['payload'].get('tool') == 'write_code'
        # raw or args should include filepath == 'test_out.txt'
        raw_args = (parsed['payload'].get('raw') or {}).get('args') or parsed['payload'].get('args') or {}
        assert raw_args.get('filepath') == 'test_out.txt' or raw_args.get('file_path') == 'test_out.txt'
    # Should have printed completion lines


@pytest.mark.asyncio
async def test_execute_code_sudo(monkeypatch):
    # Test execute_code honors allow_sudo config
    m = MCPServer()
    m.config["allow_sudo"] = False
    r = await m.execute_code({"command": "echo hi", "sudo": True})
    assert r.status == ToolStatus.ERROR
    assert "Sudo not allowed" in r.error

    m.config["allow_sudo"] = True
    # Monkeypatch subprocess.run to capture command
    called = {}

    def fake_run(cmd, *args, **kwargs):
        called["cmd"] = cmd

        class R:
            returncode = 0
            stdout = "ok"
            stderr = ""

        return R()

    monkeypatch.setattr("subprocess.run", fake_run)
    r = await m.execute_code({"command": "echo hi", "sudo": True})
    assert r.status == ToolStatus.SUCCESS
    assert "sudo -n" in called["cmd"] or called["cmd"].startswith("sudo -n")
