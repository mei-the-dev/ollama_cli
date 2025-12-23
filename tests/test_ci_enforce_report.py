import json
import subprocess
import sys
from pathlib import Path


def run_script(report_obj, tmp_path):
    p = tmp_path / "report.json"
    p.write_text(json.dumps(report_obj))
    # Run script via python interpreter
    res = subprocess.run([sys.executable, "scripts/ci_enforce_report.py", "--report", str(p)])
    return res.returncode


def test_enforce_detects_missing(tmp_path):
    # One card missing for a live test
    rpt = {"generated_at":"t","cards":[{"test":"tests/test_integration_live_model.py::test_live","prompt":"x","answer":"(no model call)"}]}
    rc = run_script(rpt, tmp_path)
    assert rc == 2


def test_enforce_all_good(tmp_path):
    rpt = {"generated_at":"t","cards":[{"test":"tests/test_something.py::test_x","prompt":"x","answer":"Something"}]}
    rc = run_script(rpt, tmp_path)
    assert rc == 0
