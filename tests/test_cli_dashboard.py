import asyncio
import types

import pytest

from omarchy_cli import SingularityCLI


@pytest.mark.asyncio
async def test_start_dashboard_with_tmux(monkeypatch, tmp_path):
    cli = OmarchyCLI()

    # Monkeypatch shutil.which to pretend tmux exists
    import shutil
    monkeypatch.setattr(shutil, 'which', lambda name: '/usr/bin/tmux' if name == 'tmux' else None)

    calls = []

    async def fake_create(*args, **kwargs):
        calls.append(args)
        # Return dummy with pid
        proc = types.SimpleNamespace()
        proc.pid = 12345
        return proc

    monkeypatch.setattr(asyncio, 'create_subprocess_exec', fake_create)

    await cli.start_dashboard()

    # First call should use tmux binary
    assert calls[0][0] == '/usr/bin/tmux'
    # Accept either creating a new window or a detached session (both valid tmux strategies)
    assert ('new-window' in calls[0]) or ('new-session' in calls[0])
    # find the -n argument and ensure the window name starts with 'dashboard-'
    if '-n' in calls[0]:
        idx = calls[0].index('-n')
        name = calls[0][idx + 1]
        assert name.startswith('dashboard-')



@pytest.mark.asyncio
async def test_start_dashboard_without_tmux(monkeypatch, tmp_path):
    cli = OmarchyCLI()
    calls = []

    import shutil
    monkeypatch.setattr(shutil, 'which', lambda name: None)

    async def fake_create(*args, **kwargs):
        calls.append(args)
        proc = types.SimpleNamespace()
        proc.pid = 22222
        return proc

    monkeypatch.setattr(asyncio, 'create_subprocess_exec', fake_create)

    await cli.start_dashboard()

    import sys as _sys
    assert calls[0][0] == _sys.executable
    # Dashboard path should be passed somewhere in the args
    assert any('singularity_dashboard.py' in str(a) for a in calls[0])



def test_help_includes_dashboard(capsys):
    cli = OmarchyCLI()
    # Capture console output
    cli.show_help()
    captured = capsys.readouterr()
    assert '/dashboard' in captured.out


@pytest.mark.asyncio
async def test_auto_launch_gui_terminal(monkeypatch, tmp_path):
    """When a GUI display is present and an emulator like alacritty exists, it should be launched and attach to tmux session."""
    cli = OmarchyCLI()
    calls = []

    # Pretend tmux exists and alacritty exists
    import shutil
    monkeypatch.setattr(shutil, 'which', lambda name: '/usr/bin/tmux' if name == 'tmux' else ('/usr/bin/alacritty' if name == 'alacritty' else None))

    async def fake_create(*args, **kwargs):
        calls.append(args)
        proc = types.SimpleNamespace()
        proc.pid = 55555
        return proc

    monkeypatch.setenv('DISPLAY', ':0')
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', fake_create)

    await cli.start_dashboard()

    # first call should be tmux new-session, second call should be alacritty
    assert calls[0][0] == '/usr/bin/tmux'
    assert any('/usr/bin/alacritty' == c[0] for c in calls[1:])


@pytest.mark.asyncio
async def test_preferred_terminal_env(monkeypatch, tmp_path):
    """Preferred terminal via ENV should be used when available."""
    cli = OmarchyCLI()
    calls = []

    import shutil
    monkeypatch.setenv('OMARCHY_PREFERRED_TERMINAL', 'alacritty')
    monkeypatch.setenv('DISPLAY', ':0')
    monkeypatch.setattr(shutil, 'which', lambda name: '/usr/bin/tmux' if name == 'tmux' else ('/usr/bin/alacritty' if name == 'alacritty' else None))

    async def fake_create(*args, **kwargs):
        calls.append(args)
        proc = types.SimpleNamespace()
        proc.pid = 66666
        return proc

    monkeypatch.setattr(asyncio, 'create_subprocess_exec', fake_create)

    await cli.start_dashboard()

    # ensure alacritty was used (it should be one of the subsequent calls)
    assert any('/usr/bin/alacritty' == c[0] for c in calls)


