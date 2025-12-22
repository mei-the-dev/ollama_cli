import os
import json
from pathlib import Path

import pytest
from omarchy_cli import OmarchyCLI


def test_get_effective_config(tmp_path, monkeypatch):
    # redirect HOME to a temp dir
    monkeypatch.setenv('HOME', str(tmp_path))
    cfg = tmp_path / '.omarchy' / 'config.json'
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps({'allow_sudo': True, 'auto_apply': False, 'model': 'x'}))

    # env should override file
    monkeypatch.setenv('OMARCHY_AUTO_APPLY', '1')

    cli = OmarchyCLI()
    conf = cli.get_effective_config()
    assert conf['allow_sudo'] is True
    assert conf['auto_apply'] is True
    assert conf['model'] == 'x'


def test_cli_config_show_exec(monkeypatch, tmp_path):
    # Ensure the CLI prints JSON when called as `omarchy config show`
    # Use the local venv wrapper script
    script = Path('./.venv/bin/omarchy')
    if not script.exists():
        pytest.skip('no local wrapper')

    monkeypatch.setenv('HOME', str(tmp_path))
    # write a config
    cfg = tmp_path / '.omarchy' / 'config.json'
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps({'allow_sudo': False, 'auto_apply': False}))

    import subprocess
    proc = subprocess.run([str(script), 'config', 'show'], capture_output=True, text=True)
    assert proc.returncode == 0
    out = proc.stdout.strip()
    data = json.loads(out)
    assert 'allow_sudo' in data
    assert 'auto_apply' in data
