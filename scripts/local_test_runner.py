#!/usr/bin/env python3
"""Local test runner for fast, strong developer checks.

Runs a focused subset of tests and checks designed to catch regressions that
would affect the interactive CLI experience and placeholder behavior.

Usage:
    python scripts/local_test_runner.py

Steps performed:
    1. Run pytest fast subset (exclude live/slow tests)
    2. Run interactive CLI test(s)
    3. Run placeholder check against JSONL and logs

Exit codes:
    0 - all checks passed
    non-zero - one or more checks failed
"""
from __future__ import annotations

import os
import subprocess
import sys

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
PYTEST = os.environ.get("PYTEST", sys.executable + " -m pytest")

checks = []


def run_cmd(cmd, capture=False, env=None):
    print(f"Running: {cmd}")
    proc = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE if capture else None, stderr=subprocess.STDOUT if capture else None, text=True, env=env)
    if capture:
        print(proc.stdout)
    return proc.returncode


def check_pytest_fast():
    """Run unit + integration tests excluding live or explicit slow tests and emit structured events."""
    print("\n==> 1) Running focused pytest (excludes 'live' and 'slow')")
    events_path = os.environ.get("TEST_MODEL_EVENTS_PATH") or os.path.join(os.getcwd(), "logs", "test_model_events.jsonl")
    # ensure events file is cleared
    try:
        if os.path.exists(events_path):
            os.remove(events_path)
    except Exception:
        pass
    cmd = f"{sys.executable} -m pytest -q -k 'not live and not slow'"
    # Run with TEST_MODEL_EVENTS_PATH set so tests will write structured events
    env = os.environ.copy()
    env["TEST_MODEL_EVENTS_PATH"] = str(events_path)
    print(f"Using TEST_MODEL_EVENTS_PATH={events_path}")
    return run_cmd(cmd, capture=False, env=env)


def check_interactive():
    """Run the interactive CLI test we added for code-mode behavior."""
    print("\n==> 2) Running interactive CLI test(s)")
    # Directly run the single test to keep it fast and deterministic
    cmd = f"{sys.executable} -m pytest -q tests/test_cli_interactive_code_mode.py"
    return run_cmd(cmd)


def check_placeholders():
    """Run the placeholder checker against local events/logs."""
    print("\n==> 3) Checking for placeholder responses in logs and events")
    events = os.environ.get("TEST_MODEL_EVENTS_PATH") or os.path.join(os.getcwd(), "logs", "test_model_events.jsonl")
    log = os.path.join(os.getcwd(), "logs", "singularity.log")
    cmd = f"{sys.executable} scripts/ci_check_no_placeholders.py --events {events} --log {log}"
    return run_cmd(cmd, capture=True)


def main():
    rc = 0
    rc = max(rc, check_pytest_fast())
    rc = max(rc, check_interactive())
    rc = max(rc, check_placeholders())

    # Enforce event coverage for agent-related tests
    print("\n==> 4) Enforcing event coverage for agent-related tests")
    rc = max(rc, run_cmd(f"{sys.executable} scripts/enforce_event_coverage.py", capture=False))

    if rc == 0:
        print("\nAll local checks passed — good to go.")
    else:
        print("\nOne or more local checks failed. See output above.")
    sys.exit(rc)


if __name__ == "__main__":
    main()
