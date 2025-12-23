#!/usr/bin/env python3
"""Generate an enriched CLI-focused test report locally.

This script runs pytest for CLI-related tests, captures the output, and
renders the enriched, terminal-only report produced by `scripts/test_report.py`.

Usage:
    python scripts/cli_report.py

Exit codes:
    0 - all tests passed
    non-zero - some tests failed (exit code reflects pytest return code)
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PY = Path(".venv/bin/python") if Path(".venv/bin/python").exists() else Path(sys.executable)
ROOT = Path(__file__).resolve().parent.parent
EVENTS = ROOT / "logs" / "test_model_events.jsonl"
PYTEST_CMD = [str(PY), "-m", "pytest", "-q", "-k", "cli"]


def run_pytest_and_report():
    env = os.environ.copy()
    env["TEST_MODEL_EVENTS_PATH"] = str(EVENTS)

    print(f"Running CLI tests: {' '.join(PYTEST_CMD)}")
    proc = subprocess.run(PYTEST_CMD, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, text=True)

    # Ensure logs dir exists
    os.makedirs(str(EVENTS.parent), exist_ok=True)

    output = proc.stdout or ""

    # Write a short copy for debugging purposes
    out_path = ROOT / "reports" / "pytest_cli_output.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(output, encoding="utf-8")
    print(f"Wrote pytest output to {out_path}")

    # Render the terminal-only report by piping the captured output to test_report.py --no-run
    report_cmd = [str(PY), str(ROOT / "scripts" / "test_report.py"), "--no-run"]
    print(f"Rendering terminal report: {' '.join(report_cmd)}")
    p2 = subprocess.run(report_cmd, input=output, text=True)

    # Exit with pytest's return code to surface failures in automation
    return proc.returncode


if __name__ == "__main__":
    rc = run_pytest_and_report()
    sys.exit(rc)
