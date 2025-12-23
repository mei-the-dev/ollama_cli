"""Pytest plugin: provide `model_event_logger` fixture and manage JSONL file lifecycle."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

import pytest

from tests.model_events import ModelEventLogger, DEFAULT_EVENTS_PATH


def pytest_sessionstart(session):
    """Clear or create the events file at session start unless overridden."""
    path = os.environ.get("TEST_MODEL_EVENTS_PATH")
    out = Path(path) if path else DEFAULT_EVENTS_PATH
    try:
        if out.exists():
            out.unlink()
        out.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    # expose path on session for downstream tools
    session.config._model_events_path = str(out)


@pytest.fixture
def model_event_logger(request) -> Generator[ModelEventLogger, None, None]:
    """Fixture that yields a ModelEventLogger scoped to the test node.

    Usage in tests:
        def test_x(model_event_logger):
            model_event_logger.emit('PROMPT', {'prompt': '...'} )
            model_event_logger.emit('ASSISTANT', {'content': '...'} )

    This fixture also sets the environment variable `PYTEST_CURRENT_TEST` to the
    nodeid for compatibility with code that inspects that env var (e.g., the
    agent emitting events during execution).
    """
    nodeid = request.node.nodeid
    path = os.environ.get("TEST_MODEL_EVENTS_PATH")

    # Set env var so code under test that inspects PYTEST_CURRENT_TEST gets the nodeid
    old = os.environ.get("PYTEST_CURRENT_TEST")
    os.environ["PYTEST_CURRENT_TEST"] = nodeid

    logger = ModelEventLogger(test_node=nodeid, out_path=path)
    try:
        yield logger
    finally:
        # Restore previous env var state
        if old is None:
            os.environ.pop("PYTEST_CURRENT_TEST", None)
        else:
            os.environ["PYTEST_CURRENT_TEST"] = old
    # no explicit teardown needed (events already flushed on emit)


@pytest.fixture
def event_reader(request):
    """Provide a small helper to read and wait for structured events for the current test.

    Usage:
        def test_x(event_reader):
            ev = event_reader.wait_for('PARSED_TOOL', timeout=1.0)
            assert ev and ev['payload']['tool'] == 'write_code'
    """
    from tests.event_assertions import read_events
    import time

    nodeid = request.node.nodeid
    path = os.environ.get("TEST_MODEL_EVENTS_PATH") or str(DEFAULT_EVENTS_PATH)

    class _R:
        def __init__(self, path, node):
            self.path = path
            self.node = node

        def read(self):
            return read_events(self.path)

        def find(self, kind: str):
            for e in self.read():
                if e.get("test") == self.node and e.get("event") == kind:
                    return e
            return None

        def wait_for(self, kind: str, timeout: float = 2.0, poll: float = 0.05):
            t0 = time.time()
            while time.time() - t0 < timeout:
                ev = self.find(kind)
                if ev:
                    return ev
                time.sleep(poll)
            return None

    return _R(path, nodeid)
