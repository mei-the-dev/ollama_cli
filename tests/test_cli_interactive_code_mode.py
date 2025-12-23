import asyncio
import json
import os
import re
import pytest

import singularity_cli
from tests.model_events import DEFAULT_EVENTS_PATH


@pytest.mark.asyncio
async def test_interactive_code_mode_prints_code_and_no_placeholder(monkeypatch, capsys, tmp_path):
    """Simulate interactive CLI: /mode code, then a code prompt, ensure code-like reply and no 'placeholder' in output."""

    # Prepare prompt sequence: /mode code -> code prompt -> /exit
    seq = ["/mode code", "generate an animated ux loading component", "/exit"]

    async def fake_prompt_ask(prompt=None):
        # mimic Prompt.ask synchronous call in interactive_mode, but return value directly
        if not seq:
            return ""
        return seq.pop(0)

    # Monkeypatch Prompt.ask used in interactive loop
    monkeypatch.setattr(singularity_cli.Prompt, "ask", lambda prompt=None: seq.pop(0) if seq else "")

    # Monkeypatch agent.execute_with_animation to return code-like reply
    async def fake_execute_with_animation(self, full_prompt, status, system=None):
        # Simulate a realistic code reply
        reply = "def animated_loader():\n    return '<svg><!-- loader --></svg>'"
        # Print same way the real method does
        singularity_cli.console.print(f"[bold green]Agent:[/bold green] {reply}")
        # Emit PROMPT and ASSISTANT events if events path is set
        path = os.environ.get("TEST_MODEL_EVENTS_PATH") or str(DEFAULT_EVENTS_PATH)
        try:
            # Write minimal JSONL lines directly
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": "now", "test": os.environ.get("PYTEST_CURRENT_TEST", "tests_cli::interactive"), "event": "PROMPT", "payload": {"prompt": full_prompt}}) + "\n")
                fh.write(json.dumps({"ts": "now", "test": os.environ.get("PYTEST_CURRENT_TEST", "tests_cli::interactive"), "event": "ASSISTANT", "payload": {"content": reply}}) + "\n")
        except Exception:
            pass
        return reply

    monkeypatch.setattr(singularity_cli.SingularityAgent, "execute_with_animation", fake_execute_with_animation)

    # Ensure events file is isolated
    events = tmp_path / "events.jsonl"
    monkeypatch.setenv("TEST_MODEL_EVENTS_PATH", str(events))

    cli = singularity_cli.SingularityCLI()

    # Run the interactive loop (it will exit after /exit)
    await cli.interactive_mode()

    # Capture terminal output
    captured = capsys.readouterr()
    out = captured.out + captured.err

    # Should contain code-like tokens
    assert "def " in out or "<svg" in out or "function " in out
    # Should not contain the word 'placeholder'
    assert "placeholder" not in out.lower()

    # Also check the events file contains ASSISTANT
    evs = [json.loads(l) for l in events.read_text(encoding='utf-8').splitlines() if l.strip()]
    assert any(e.get('event') == 'ASSISTANT' for e in evs)
