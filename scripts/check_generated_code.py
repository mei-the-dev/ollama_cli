#!/usr/bin/env python3
"""Extract write_code tool outputs from a prompt JSONL and run flake8/mypy/pytest.

Produces a CSV summary with one row per parsed tool 'write_code' invocation.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parent.parent

# Helpers to find venv binaries if present
def venv_bin(name: str) -> str:
    v = ROOT / ".venv" / "bin" / name
    if v.exists():
        return str(v)
    return name

FLAKE8 = venv_bin("flake8")
MYPY = venv_bin("mypy")
PYTEST = venv_bin("pytest")


def sanitize_path(p: str) -> str:
    # remove absolute leading slash to place under temp dir
    return p.lstrip("/")


def run_cmd(cmd, cwd=None, timeout=30):
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd, timeout=timeout, text=True)
        return proc.returncode, proc.stdout
    except subprocess.TimeoutExpired as e:
        return 124, (e.stdout or "") + "\nTimeout"
    except FileNotFoundError:
        return 127, f"Command not found: {cmd[0]}"


def main(infile: Path, out_csv: Path, tmp_dir: Path):
    tmp_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    with infile.open("r", encoding="utf-8") as fh:
        for ln in fh:
            try:
                rec = json.loads(ln)
            except Exception:
                continue
            events = rec.get("events") or []
            for ev in events:
                if ev.get("event") == "PARSED_TOOL":
                    payload = ev.get("payload") or {}
                    tool = payload.get("tool")
                    if tool != "write_code":
                        continue
                    args = payload.get("args") or {}
                    filepath = args.get("filepath")
                    content = args.get("content")
                    if not filepath or not content:
                        continue

                    relpath = sanitize_path(filepath)
                    dest = tmp_dir / relpath
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_text(content, encoding="utf-8")

                    # Run flake8
                    fcode, foutput = run_cmd([FLAKE8, str(dest)])
                    f_ok = fcode == 0

                    # Run mypy (type-checking); restrict to file
                    mcode, moutput = run_cmd([MYPY, str(dest)])
                    m_ok = mcode == 0

                    # Run pytest if tests exist under same directory
                    # Use pytest's -q and --maxfail=1
                    pytest_res = "skipped"
                    pcode = None
                    if any(str(x).endswith("test_") or str(x).endswith("_test.py") or "tests" in str(dest.parent).lower() for x in [dest]):
                        pcode, pout = run_cmd([PYTEST, str(tmp_dir), "-q", "--maxfail=1"], cwd=tmp_dir, timeout=60)
                        pytest_res = f"code={pcode}\n{pout}"
                    else:
                        # attempt to detect any test files in tmp_dir
                        tests = list(tmp_dir.rglob("test_*.py")) + list(tmp_dir.rglob("*_test.py"))
                        if tests:
                            pcode, pout = run_cmd([PYTEST, str(tmp_dir), "-q", "--maxfail=1"], cwd=tmp_dir, timeout=60)
                            pytest_res = f"code={pcode}\n{pout}"

                    rows.append({
                        "prompt_index": rec.get("i"),
                        "prompt": rec.get("prompt"),
                        "filepath": filepath,
                        "flake8_ok": f_ok,
                        "flake8_output": (foutput or "").strip(),
                        "mypy_ok": m_ok,
                        "mypy_output": (moutput or "").strip(),
                        "pytest_result": pytest_res,
                    })

    # Write CSV
    keys = ["prompt_index","prompt","filepath","flake8_ok","flake8_output","mypy_ok","mypy_output","pytest_result"]
    with out_csv.open("w", encoding="utf-8", newline='') as outf:
        writer = csv.DictWriter(outf, fieldnames=keys)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print(f"Wrote {len(rows)} rows to {out_csv}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--in", dest="infile", required=True)
    parser.add_argument("-o", "--out", dest="outfile", required=True)
    parser.add_argument("--tmp", dest="tmp", default=str(ROOT / "tmp" / "generated"))
    args = parser.parse_args()
    main(Path(args.infile), Path(args.outfile), Path(args.tmp))
