#!/usr/bin/env python3
"""Clean prompt results JSONL by removing entries with known transient errors

Usage:
  python scripts/clean_prompt_results.py --in reports/prompt_test_results.jsonl --out reports/prompt_test_results_clean.jsonl
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

BAD_SUBSTRINGS = ["400 Client Error", "Bad Request", "Read timed out", "timeout", "404: {\"error\":\"model", "model 'Qwen2.5-Coder-14B' not found"]


def is_bad_entry(rec: dict) -> bool:
    # If ok is False and the error message contains one of the bad substrings, drop it
    if not rec.get("ok"):
        err = (rec.get("error") or "") + " " + (rec.get("stdout") or "") + " " + (rec.get("stderr") or "")
        err = err.lower()
        for s in BAD_SUBSTRINGS:
            if s.lower() in err:
                return True
    return False


def clean_file(in_path: Path, out_path: Path) -> dict:
    kept = 0
    removed = 0
    with in_path.open("r", encoding="utf-8") as inf, out_path.open("w", encoding="utf-8") as outf:
        for ln in inf:
            try:
                rec = json.loads(ln)
            except Exception:
                continue
            if is_bad_entry(rec):
                removed += 1
                continue
            outf.write(json.dumps(rec, ensure_ascii=False) + "\n")
            kept += 1
    return {"kept": kept, "removed": removed}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", "-i", dest="infile", required=True)
    parser.add_argument("--out", "-o", dest="outfile", required=True)
    args = parser.parse_args()
    in_path = Path(args.infile)
    out_path = Path(args.outfile)
    if not in_path.exists():
        raise SystemExit(f"Input file not found: {in_path}")
    stats = clean_file(in_path, out_path)
    print(f"Wrote {stats['kept']} entries to {out_path} (removed {stats['removed']}).")