import pytest

import singularity_cli


def test_permission_matches_exact_and_wildcard(tmp_path, monkeypatch):
    pm = singularity_cli.PermissionManager()
    pm.allowed_patterns.clear()
    pm.always_ask_patterns.clear()

    pm.add_allowed("write_code")
    assert pm.check("write_code", {"filepath": "a.py"}) is True

    pm.allowed_patterns.clear()
    pm.add_allowed("write_code(*.py)")
    assert pm.check("write_code", {"filepath": "foo.py"}) is True
    assert pm.check("write_code", {"filepath": "foo.txt"}) is False

    pm.allowed_patterns.clear()
    pm.add_allowed("write_code(/var/*)")
    assert pm.check("write_code", {"filepath": "/var/log/app.log"}) is True


def test_always_ask_pattern(tmp_path):
    pm = singularity_cli.PermissionManager()
    pm.allowed_patterns.clear()
    pm.always_ask_patterns.clear()

    pm.add_ask("execute_code")
    assert pm.check("execute_code", {}) is False
    # default when not matched is False (ask)
    assert pm.check("write_code", {"filepath": "a.py"}) is False
