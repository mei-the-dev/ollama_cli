#!/usr/bin/env python3
"""Run a test factory batch and validate the resulting report and events."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = str(ROOT / '.venv' / 'bin' / 'python') if (ROOT / '.venv' / 'bin' / 'python').exists() else sys.executable
EVENTS = ROOT / 'logs' / 'test_model_events.jsonl'
FACTORY_TEST_DIR = ROOT / 'tests' / 'factory_converted'


def run():
    env = os.environ.copy()
    env['TEST_MODEL_EVENTS_PATH'] = str(EVENTS)
    print(f"Running factory tests in {FACTORY_TEST_DIR} with events {EVENTS}")
    cmd = [PY, '-m', 'pytest', '-q', str(FACTORY_TEST_DIR)]
    rc = subprocess.run(cmd, env=env).returncode
    if rc != 0:
        print('pytest failed', rc)
        return rc

    # enforce coverage
    print('Enforcing event coverage...')
    rc2 = subprocess.run([PY, str(ROOT / 'scripts' / 'enforce_event_coverage.py')], env=env).returncode
    if rc2 != 0:
        print('event coverage enforcement failed', rc2)
        return rc2

    # render report for these tests
    print('Rendering enriched report (limited to factory tests)')
    py = [PY, str(ROOT / 'scripts' / 'test_report.py'), '--no-run']
    # capture pytest output
    proc = subprocess.run([PY, '-m', 'pytest', '-q', str(FACTORY_TEST_DIR)], env=env, stdout=subprocess.PIPE, text=True)
    out = proc.stdout
    subprocess.run(py, input=out, text=True)
    return 0


if __name__ == '__main__':
    sys.exit(run())
