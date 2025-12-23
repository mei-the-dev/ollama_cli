import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

import pytest
import requests

import singularity_cli

RUN_LIVE = os.environ.get("RUN_LIVE_OLLAMA") == "1"


@pytest.mark.skipif(not RUN_LIVE, reason="Live Ollama integration tests are disabled. Set RUN_LIVE_OLLAMA=1 to enable.")
def test_live_model_emits_tool_and_mcp_exec(tmp_path):
    """Integration test: require Ollama running locally. It should emit a JSON tool call which we execute via MCP.

    - Starts the production MCP server from ref/v2/production_mcp_server.py (random port)
    - Ensures Ollama is reachable (fails if not)
    - Sends a prompt that instructs the model to output *only* a JSON tool call: {"tool": "write_code", "args": {...}}
    - process_with_tools should detect and execute the tool via MCP and return a success summary
    - The test verifies the file exists with the expected content
    """

    # 1) Verify Ollama is reachable
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        r.raise_for_status()
    except Exception as e:
        pytest.fail(f"Ollama does not appear to be running or reachable (http://localhost:11434): {e}")

    # 2) Start production MCP server subprocess
    mcp_script = Path(__file__).resolve().parents[1] / "ref" / "v2" / "production_mcp_server.py"
    assert mcp_script.exists(), f"Production MCP server not found at {mcp_script}"

    async def inner():
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(mcp_script),
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # 3) Capture the listening URL from stdout/stderr
        url = None
        start_t = time.time()
        stderr_lines = []
        while time.time() - start_t < 8:
            try:
                line = await asyncio.wait_for(proc.stdout.readline(), timeout=0.5)
                if line:
                    s = line.decode(errors="replace").strip()
                    url = singularity_cli.SingularityAgent._parse_mcp_listen_line(s)
                    if url:
                        break
            except asyncio.TimeoutError:
                pass

            # check stderr as well
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
            # cleanup
            proc.terminate()
            await proc.wait()
            pytest.fail(f"Could not capture MCP server URL. STDERR: {' | '.join(stderr_lines[:10])}")

        agent = singularity_cli.SingularityAgent()
        agent.mcp_server_url = url

        # 4) Prepare the expected target file
        target = tmp_path / "live_test.txt"
        content = "hello from live model test"

        # 5) Insert a strict system instruction into conversation history to force JSON-only output
        system_instr = (
            "You are a tool-calling assistant. When asked to create files, respond with a single JSON object and nothing else. "
            "The JSON MUST be an object with keys: 'tool' (string) and 'args' (object). "
            "Do NOT output any other text or explanation."
        )
        agent.conversation_history.insert(0, {"role": "system", "content": system_instr})

        # 6) Ask the model to write the file using write_code tool
        # Choose an available model from Ollama tags so the request does not 404
        try:
            tags = requests.get("http://localhost:11434/api/tags", timeout=2).json()
            models = [m.get("name") for m in tags.get("models", []) if m.get("name")]
            if models:
                agent.model = models[0]
        except Exception:
            pass

        prompt = (
            f"Please create a file at {str(target)} with the exact content: {json.dumps(content)} "
            "and output only the JSON tool call like {\"tool\": \"write_code\", \"args\": { ... }}"
        )

        # 7) Run processing which should stream, detect the tool call, and execute it via MCP
        result = await agent.process_with_tools(prompt)

        # 8) Verify that the MCP execution returned success and file exists with expected content
        if not ("Executed" in (result or "") or (isinstance(result, str) and result.startswith("✓"))):
            last = agent.conversation_history[-1] if agent.conversation_history else None
            assistant_msg = agent.conversation_history[-2] if len(agent.conversation_history) >= 2 else None
            parsed_json = None
            if assistant_msg and isinstance(assistant_msg.get('content'), str):
                parsed_json = singularity_cli.SingularityAgent._extract_json_object(assistant_msg.get('content'))
            pytest.fail(
                f"Tool execution was not successful: {result}\nLast assistant message: {assistant_msg}\nParsed JSON: {parsed_json}"
            )

        # Read file using MCP read_code tool to be consistent
        read_res = await agent.call_mcp_tool("read_code", {"filepath": str(target)})
        if read_res.get("status") != "SUCCESS":
            last = agent.conversation_history[-1] if agent.conversation_history else None
            pytest.fail(f"read_code failed: {read_res}\nTool result: {result}\nLast assistant message: {last}")

        # 9) Cleanup - stop MCP server
        proc.terminate()
        await proc.wait()

    asyncio.run(inner())
