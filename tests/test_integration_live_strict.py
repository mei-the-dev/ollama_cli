import asyncio
import json
import os
import sys
import time
from pathlib import Path

import pytest
import requests

import singularity_cli

RUN_LIVE = os.environ.get("RUN_LIVE_OLLAMA") == "1"


@pytest.mark.skipif(not RUN_LIVE, reason="Live Ollama integration tests are disabled. Set RUN_LIVE_OLLAMA=1 to enable.")
def _start_production_mcp_and_get_url(mcp_script_path: Path, timeout: float = 8.0) -> str:
    """Helper to start the production MCP server synchronously and return its URL.

    This mirrors the logic used elsewhere in the test suite but is self-contained for strict tests.
    """

    async def inner():
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(mcp_script_path),
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        url = None
        start_t = time.time()
        stderr_lines = []
        while time.time() - start_t < timeout:
            try:
                line = await asyncio.wait_for(proc.stdout.readline(), timeout=0.5)
                if line:
                    s = line.decode(errors="replace").strip()
                    url = singularity_cli.SingularityAgent._parse_mcp_listen_line(s)
                    if url:
                        break
            except asyncio.TimeoutError:
                pass

            try:
                err = await asyncio.wait_for(proc.stderr.readline(), timeout=0.1)
                if err:
                    stderr_lines.append(err.decode(errors="replace").strip())
                    url = singularity_cli.SingularityAgent._parse_mcp_listen_line(stderr_lines[-1])
                    if url:
                        break
            except asyncio.TimeoutError:
                pass

        if not url:
            proc.terminate()
            await proc.wait()
            raise RuntimeError(f"Could not capture MCP server URL. STDERR: {' | '.join(stderr_lines[:10])}")

        return proc, url

    return asyncio.run(inner())


@pytest.mark.skipif(not RUN_LIVE, reason="Live Ollama integration tests are disabled. Set RUN_LIVE_OLLAMA=1 to enable.")
def test_live_strict_write_code(tmp_path):
    """Strict end-to-end test (no mocking): model must emit a single JSON object (or fenced json) and nothing else.

    - Uses a production MCP server subprocess
    - Uses a real local Ollama model (chosen from /api/tags)
    - Verifies assistant output contains only JSON (or fenced JSON) and that the write succeeds
    """
    # Ensure model events are captured when the live test runs
    events_path = tmp_path / "events.jsonl"
    os.environ["TEST_MODEL_EVENTS_PATH"] = str(events_path)

    # Verify Ollama is reachable
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        r.raise_for_status()
    except Exception as e:
        pytest.fail(f"Ollama does not appear to be running or reachable (http://localhost:11434): {e}")

    # Start the production MCP server
    mcp_script = Path(__file__).resolve().parents[1] / "ref" / "v2" / "production_mcp_server.py"
    assert mcp_script.exists(), f"Production MCP server not found at {mcp_script}"

    proc, url = _start_production_mcp_and_get_url(mcp_script)

    try:
        agent = singularity_cli.SingularityAgent()
        agent.mcp_server_url = url

        # Strong system instruction for strict JSON-only output
        system_instr = (
            "You are a tool-calling assistant. When asked to create files, respond with a single JSON object only. "
            "The JSON MUST be an object with keys: 'tool' (string) and 'args' (object). Do NOT output any additional text or explanation. "
            "Do NOT use surrounding markdown code fences."
        )
        agent.conversation_history.insert(0, {"role": "system", "content": system_instr})

        # Select an available model from Ollama tags
        try:
            tags = requests.get("http://localhost:11434/api/tags", timeout=2).json()
            models = [m.get("name") for m in tags.get("models", []) if m.get("name")]
            if models:
                agent.model = models[0]
        except Exception:
            pass

        target = tmp_path / "strict_live_test.txt"
        content = "strict content verification"

        prompt = (
            f"Create a file at {str(target)} with EXACT content: {json.dumps(content)}. "
            "Output exactly one JSON object and nothing else (no code fences, no explanation). "
            "The JSON must be of the form {\"tool\":\"write_code\", \"args\": {\"filepath\": <path>, \"content\": <content>}}"
        )

        result = asyncio.run(agent.process_with_tools(prompt))

        # 1) Assert tool execution success
        assert isinstance(result, str) and result.startswith("✓"), f"Expected success, got: {result}"

        # 2) Verify file contents using MCP read_code
        read_res = asyncio.run(agent.call_mcp_tool("read_code", {"filepath": str(target)}))
        assert read_res.get("status") == "SUCCESS", f"read_code failed: {read_res}"
        data = read_res.get("data") or {}
        # Accept either 'content' or 'text' keys depending on server implementation
        file_text = data.get("content") or data.get("text") or ""
        assert file_text == content, f"File content mismatch: expected {content!r}, got {file_text!r}"

        # 3) Strict check: assistant message must contain only the JSON object (or the same wrapped in fenced code block is forbidden by system message)
        # Find the most recent assistant message in conversation history (avoid intervening system messages)
        assistant_msg = next((m for m in reversed(agent.conversation_history) if m.get("role") == "assistant"), None)
        assert assistant_msg and isinstance(assistant_msg.get("content"), str), "No assistant message recorded"
        raw = assistant_msg.get("content").strip()
        parsed = singularity_cli.SingularityAgent._extract_json_object(raw)
        assert parsed is not None, f"Could not extract JSON object from assistant output: {raw!r}"
        # Ensure there is no extra surrounding text other than optional whitespace
        assert raw == parsed, f"Assistant output contained extra text beyond the JSON object: {raw!r}"

        # Ensure structured PARSED_TOOL event exists when available
        try:
            ev = event_reader.wait_for("PARSED_TOOL", timeout=1.0) if 'event_reader' in locals() else None
            if ev is None:
                ev_lines = Path(os.environ.get("TEST_MODEL_EVENTS_PATH", "logs/test_model_events.jsonl")).read_text(encoding="utf-8").splitlines()
                evs = [json.loads(l) for l in ev_lines]
                assert any(e.get("event") == "PARSED_TOOL" for e in evs)
            else:
                assert ev.get("event") == "PARSED_TOOL"
                assert isinstance(ev.get("payload", {}).get("raw") or ev.get("payload", {}).get("args"), dict)
        except Exception:
            pass
    finally:
        proc.terminate()
        try:
            asyncio.run(proc.wait())
        except Exception:
            pass


@pytest.mark.skipif(not RUN_LIVE, reason="Live Ollama integration tests are disabled. Set RUN_LIVE_OLLAMA=1 to enable.")
def test_live_fragmented_json_streaming(tmp_path):
    """Ask the model to emit the JSON tool call fragmented across many small chunks and ensure the streamer reassembles it correctly."""
    # Ensure model events are captured when the live test runs
    events_path = tmp_path / "events.jsonl"
    os.environ["TEST_MODEL_EVENTS_PATH"] = str(events_path)
    # Verify Ollama is reachable
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        r.raise_for_status()
    except Exception as e:
        pytest.fail(f"Ollama does not appear to be running or reachable (http://localhost:11434): {e}")

    mcp_script = Path(__file__).resolve().parents[1] / "ref" / "v2" / "production_mcp_server.py"
    assert mcp_script.exists(), f"Production MCP server not found at {mcp_script}"

    proc, url = _start_production_mcp_and_get_url(mcp_script)

    try:
        agent = singularity_cli.SingularityAgent()
        agent.mcp_server_url = url

        # Prompt to force fragmented output (model compliance is required for the strict test)
        target = tmp_path / "frag_test.txt"
        content = "fragmented content"

        system_instr = (
            "You are a tool-calling assistant. Output the JSON object that calls 'write_code' for filepath and content, but split the JSON across many small fragments (for example, one token per line). "
            "The sequence of fragments should collectively form exactly one valid JSON object (no extra text)."
        )
        agent.conversation_history.insert(0, {"role": "system", "content": system_instr})

        # Select an available model from Ollama tags
        try:
            tags = requests.get("http://localhost:11434/api/tags", timeout=2).json()
            models = [m.get("name") for m in tags.get("models", []) if m.get("name")]
            if models:
                agent.model = models[0]
        except Exception:
            pass

        prompt = (
            f"Please send the JSON object to write a file at {str(target)} with content: {json.dumps(content)}. "
            "Split the JSON into many small fragments sent sequentially so that the stream yields partial JSON fragments in multiple steps."
        )

        result = asyncio.run(agent.process_with_tools(prompt))

        assert isinstance(result, str) and result.startswith("✓"), f"Expected success from fragmented JSON, got: {result}"

        # Confirm file contents
        read_res = asyncio.run(agent.call_mcp_tool("read_code", {"filepath": str(target)}))
        assert read_res.get("status") == "SUCCESS", f"read_code failed (fragmented case): {read_res}"
        data = read_res.get("data") or {}
        file_text = data.get("content") or data.get("text") or ""
        assert file_text == content, f"Fragmented write produced wrong content: {file_text!r}"

    finally:
        proc.terminate()
        try:
            asyncio.run(proc.wait())
        except Exception:
            pass
