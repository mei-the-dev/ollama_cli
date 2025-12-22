import os
import json
import getpass
from pathlib import Path
import pytest
from omarchy_cli import OmarchyCLI


def test_startup_prompts_enable_auto_and_sudo(monkeypatch, tmp_path):
    # Redirect HOME to temp
    monkeypatch.setenv('HOME', str(tmp_path))

    # Create config file with defaults
    cfg = tmp_path / '.omarchy' / 'config.json'
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps({"model":"x","allow_sudo":False, "auto_apply": False}))

    cli = OmarchyCLI()

    # Monkeypatch Confirm.ask to return True for all prompts
    monkeypatch.setattr('rich.prompt.Confirm.ask', lambda *args, **kwargs: True)
    # Monkeypatch getpass to return a test password
    monkeypatch.setattr('getpass.getpass', lambda prompt='': 'secretpw')

    # Run the startup prompt method synchronously
    import asyncio
    asyncio.run(cli.startup_config_prompt())

    # Verify config file updated
    cfg_data = json.loads(cfg.read_text())
    assert cfg_data.get('allow_sudo') is True
    assert cfg_data.get('auto_apply') is True
    # Confirm CLI stored sudo_password
    assert getattr(cli, 'sudo_password') == 'secretpw'