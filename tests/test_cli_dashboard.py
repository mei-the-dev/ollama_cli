import asyncio
import types

import pytest

from omarchy_cli import OmarchyCLI


@pytest.mark.asyncio
async def test_start_dashboard_with_tmux(monkeypatch, tmp_path):
    cli = OmarchyCLI()
    called = {}

    # Monkeypatch shutil.which to pretend tmux exists
    import shutil
    monkeypatch.setattr(shutil, 'which', lambda name: '/usr/bin/tmux' if name == 'tmux' else None)

    async def fake_create(*args, **kwargs):
        called['args'] = args
        # Return dummy with pid
        proc = types.SimpleNamespace()
        proc.pid = 12345
        return proc

    monkeypatch.setattr(asyncio, 'create_subprocess_exec', fake_create)

    await cli.start_dashboard()

    assert called['args'][0] == '/usr/bin/tmux'
    assert 'new-window' in called['args']
    # find the -n argument and ensure the window name starts with 'dashboard-'
    if '-n' in called['args']:
        idx = called['args'].index('-n')
        name = called['args'][idx + 1]
        assert name.startswith('dashboard-')


@pytest.mark.asyncio
async def test_start_dashboard_without_tmux(monkeypatch, tmp_path):
    cli = OmarchyCLI()
    called = {}

    import shutil
    monkeypatch.setattr(shutil, 'which', lambda name: None)

    async def fake_create(*args, **kwargs):
        called['args'] = args
        proc = types.SimpleNamespace()
        proc.pid = 22222
        return proc

    monkeypatch.setattr(asyncio, 'create_subprocess_exec', fake_create)

    await cli.start_dashboard()

    assert called['args'][0] == 'python3'
    # Dashboard path should be passed as second arg
    assert 'omarchy_dashboard.py' in called['args'][1]


def test_help_includes_dashboard(capsys):
    cli = OmarchyCLI()
    # Capture console output
    cli.show_help()
    captured = capsys.readouterr()
    assert '/dashboard' in captured.out
