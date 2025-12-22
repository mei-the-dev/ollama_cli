import os
import sys
import asyncio
import json
from pathlib import Path
import pytest

from omarchy_cli import OmarchyCLI


def test_show_banner_runs(capsys):
    cli = OmarchyCLI()
    # show_banner should run without error and print something
    cli.show_banner()
    captured = capsys.readouterr()
    assert "Omarchy" in captured.out or "Artistic Code Agent" in captured.out


@pytest.mark.asyncio
async def test_startup_prompts_noninteractive_skips(monkeypatch, tmp_path):
    cli = OmarchyCLI()
    # Ensure non-interactive environment
    monkeypatch.setattr(sys.stdin, 'isatty', lambda: False)

    # Remove any existing config
    cfg_path = Path.home() / '.omarchy' / 'config.json'
    if cfg_path.exists():
        bak = tmp_path / 'cfg_backup.json'
        bak.write_text(cfg_path.read_text())
        cfg_path.unlink()
    try:
        await cli.startup_config_prompt()
        # In non-interactive mode, config file should not be created/modified by prompts
        assert not cfg_path.exists()
    finally:
        if 'bak' in locals() and bak.exists():
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            cfg_path.write_text(bak.read_text())


@pytest.mark.asyncio
async def test_execute_command_async(capsys):
    cli = OmarchyCLI()
    await cli.execute_command('echo hello-omarchy-test')
    captured = capsys.readouterr()
    assert 'hello-omarchy-test' in captured.out
