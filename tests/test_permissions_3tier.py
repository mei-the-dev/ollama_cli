import os
import json
import pytest

from singularity_cli import PermissionManager, PermissionLevel


def test_set_and_get_permissions(tmp_path, monkeypatch):
    # Isolate config path
    monkeypatch.setenv("HOME", str(tmp_path))
    pm = PermissionManager()

    # Default: ASK
    level = pm.get_permission("write_code", {"filepath": "foo.py"})
    assert level == PermissionLevel.ASK

    # Add allowed pattern
    pm.add_allowed("write_code")
    assert pm.get_permission("write_code", {}) == PermissionLevel.ALWAYS_ALLOW
    assert pm.check("write_code", {}) is True

    # Replace existing allowed with a more specific 'ask' pattern and verify behavior
    pm.allowed_patterns.discard("write_code")
    pm.save()
    pm.add_ask("write_code(*.py)")
    assert pm.get_permission("write_code", {"filepath": "a.py"}) == PermissionLevel.ASK
    # Other file types default to ASK as well
    assert pm.get_permission("write_code", {"filepath": "a.txt"}) == PermissionLevel.ASK

    # Block a pattern
    pm.add_block("execute_code")
    assert pm.get_permission("execute_code", {}) == PermissionLevel.NEVER
    assert pm.check("execute_code", {}) is False

    # Persisted json contains keys
    cfg = json.loads((tmp_path / ".singularity" / "permissions.json").read_text())
    assert "allowed" in cfg and "ask" in cfg and "never" in cfg
