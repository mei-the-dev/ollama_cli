import os

import singularity_cli


def test_session_create_and_load(tmp_path, monkeypatch):
    # Use a temp HOME to avoid touching real ~/.singularity
    monkeypatch.setenv("HOME", str(tmp_path))

    sm = singularity_cli.SessionManager()
    s = sm.create("mysession")
    assert s.name == "mysession"

    loaded = sm.load(s.id)
    assert loaded is not None
    assert loaded.id == s.id

    last = sm.get_last()
    assert last.id == s.id

    lst = sm.list()
    assert any(x.id == s.id for x in lst)
