import os
import asyncio
import pytest
from pathlib import Path

import singularity_cli


@pytest.mark.asyncio
async def test_process_prompt_includes_context(monkeypatch, tmp_path):
    # Create a temp file to reference
    f = tmp_path / "demo.py"
    f.write_text("def demo():\n    return 42\n")

    cli = singularity_cli.SingularityCLI()
    # Ensure agent has context manager
    assert getattr(cli.agent, "context_manager", None) is not None

    captured = {}

    async def fake_process_with_tools(prompt, system=None, execute_tools=False):
        captured['system'] = system
        return "ok"

    monkeypatch.setattr(cli.agent, 'process_with_tools', fake_process_with_tools)
    # Force structured-path during tests
    monkeypatch.setenv("RUN_LIVE_OLLAMA", "1")

    # Run process_prompt with @file reference
    await cli.process_prompt(f"Analyze @file:{str(f)}", 'code')

    assert 'Context:' in captured.get('system', '')
    assert 'def demo' in captured.get('system', '')
