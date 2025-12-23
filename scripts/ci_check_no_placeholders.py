#!/usr/bin/env python3
"""CI helper: fail if placeholder responses are present in events or logs."""
import argparse
import json
import os
import re
import sys

PLACEHOLDER_RX = re.compile(r"placeholder response|this environment provides a placeholder|use /mode code", re.I)


def check_events(path: str) -> int:
    if not os.path.exists(path):
        return 0
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh, start=1):
            try:
                j = json.loads(line)
            except Exception:
                continue
            payload = j.get("payload") or {}
            s = " ".join(str(payload.get(k, "")) for k in ("content", "answer", "raw", "text"))
            if s and PLACEHOLDER_RX.search(s):
                print(f"PLACEHOLDER FOUND in {path}:{i}: {s}")
                return 2
    return 0


def check_log(path: str) -> int:
    if not os.path.exists(path):
        return 0
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for i, l in enumerate(fh, start=1):
            if PLACEHOLDER_RX.search(l):
                print(f"PLACEHOLDER FOUND in {path}:{i}: {l.strip()}")
                return 2
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--events", default=os.environ.get("TEST_MODEL_EVENTS_PATH") or "logs/test_model_events.jsonl")
    p.add_argument("--log", default="logs/singularity.log")
    args = p.parse_args()

    rc = 0
    rc = max(rc, check_events(args.events))
    rc = max(rc, check_log(args.log))
    if rc != 0:
        print("Placeholder checks failed.")
    else:
        print("No placeholders found.")
    sys.exit(rc)


if __name__ == "__main__":
    main()
