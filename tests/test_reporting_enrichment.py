import json
from pathlib import Path

from tests.reporting import build_cards_from_events


def test_build_cards_includes_test_docstring_and_markers(tmp_path, monkeypatch):
    # Create a dummy test file with docstring and marker
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_enrich.py"
    content = '''import pytest

@pytest.mark.live
def test_enrich():
    """This is a helpful docstring describing the test's intention."""
    assert True
'''
    test_file.write_text(content)

    nodeid = f"{test_file.as_posix()}::test_enrich"
    by_test = {
        nodeid: [
            {"ts": "ts1", "event": "PROMPT", "payload": {"prompt": "Please do X"}},
            {"ts": "ts2", "event": "ASSISTANT", "payload": {"content": "{\"tool\": \"write_code\"}"}},
        ]
    }

    cards = build_cards_from_events(by_test)
    assert len(cards) == 1
    c = cards[0]
    assert c["description"] == "This is a helpful docstring describing the test's intention."
    assert "live" in c["markers"]
    assert c["file"].endswith("test_enrich.py")
    assert c["intent"] == "Model interaction recorded"
