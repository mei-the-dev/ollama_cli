#!/usr/bin/env python3
"""CI helper to enforce model call expectations from `report.json`.

Exit code 0 on success. Exit 2 if missing required model calls are found.
"""
import argparse
import json
import sys
import re


def find_missing_model_calls(report_path: str) -> list:
    with open(report_path, "r", encoding="utf-8") as fh:
        j = json.load(fh)
    cards = j.get("cards") or []

    missing = []
    for c in cards:
        ans = c.get("answer", "")
        test = c.get("test", "")
        if isinstance(ans, str) and ans.strip() == "(no model call)":
            # Heuristic: if the test name contains 'live' or 'integration' or 'ollama', consider it required
            if re.search(r"live|integration|ollama", test, flags=re.I):
                missing.append(test)
    return missing


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--report", required=True, help="Path to report.json")
    args = p.parse_args()

    missing = find_missing_model_calls(args.report)
    if missing:
        print("Missing required model calls detected:")
        for t in missing:
            print(" - ", t)
        print("Failing due to missing model calls.")
        sys.exit(2)
    print("No missing required model calls detected.")
    sys.exit(0)


if __name__ == "__main__":
    main()
