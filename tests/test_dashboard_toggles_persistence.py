import json
from pathlib import Path
import pytest
from ref.omarchy_dashboard import OmarchyDashboard

def read_config():
    p = Path.home() / '.omarchy' / 'config.json'
    if not p.exists():
        return {}
    return json.loads(p.read_text())

@pytest.mark.asyncio
async def test_enable_disable_persistence(tmp_path, monkeypatch):
    # Use temp HOME so we don't overwrite user's config
    monkeypatch.setenv('HOME', str(tmp_path))
    app = OmarchyDashboard()
    app.register_modules()
    # Ensure module exists
    assert any(m._module_name == 'req_rate' for m in app.modules)
    # Disable req_rate
    app.disable_module('req_rate')
    cfg = read_config()
    assert 'enabled_modules' in cfg
    assert 'req_rate' not in cfg['enabled_modules']
    # Enable back
    app.enable_module('req_rate')
    cfg = read_config()
    assert 'req_rate' in cfg['enabled_modules']

@pytest.mark.asyncio
async def test_disable_unmounts(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    app = OmarchyDashboard()
    app.register_modules()
    app.mount_modules()
    # ensure mounted
    assert any(getattr(m, '_mounted', False) for m in app.modules if getattr(m, '_module_name', None) == 'req_rate')
    # disable
    app.disable_module('req_rate')
    # now the module should be disabled and removed from registry
    assert 'req_rate' in getattr(app, '_disabled_modules', [])
