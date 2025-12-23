#!/usr/bin/env python3
"""Inventory tests and their structured event coverage.

Produces a per-test report with:
- file, function, docstring present, markers
- event counts (PROMPT, ASSISTANT, PARSED_TOOL)
- sample prompt/assistant text
- whether singularity.log contains references

Writes JSON report to reports/test_inventory.json and prints a concise summary.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

# import helpers from tests.reporting
# Make repo root importable so we can import tests.reporting outside pytest
sys.path.insert(0, str(ROOT))
try:
    from tests import reporting
except Exception as e:
    print("Failed to import tests.reporting:", e, file=sys.stderr)
    sys.exit(2)


def collect_tests() -> list[str]:
    cmd = [sys.executable, "-m", "pytest", "--collect-only", "-q"]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    lines = [l.strip() for l in (proc.stdout or "").splitlines() if l.strip()]
    nodes = [l for l in lines if "::" in l]
    return nodes


def load_events(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        return reporting.parse_jsonl_events(path)
    except Exception:
        # best-effort fallback: parse manually
        by_test = defaultdict(list)
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    j = json.loads(line)
                except Exception:
                    continue
                t = j.get("test") or "unknown"
                by_test[t].append(j)
        return by_test


def search_logs_for_test(test_id: str, log_path: str = "logs/singularity.log") -> int:
    if not os.path.exists(log_path):
        return 0
    cnt = 0
    with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
        for l in fh:
            if test_id in l:
                cnt += 1
    return cnt


def summarize():
    nodes = collect_tests()
    events_path = os.environ.get("TEST_MODEL_EVENTS_PATH") or str(ROOT / "logs" / "test_model_events.jsonl")
    by_test = load_events(events_path)

    inventory = []

    missing_doc = []
    missing_events = []
    live_expected_no_call = []

    for node in nodes:
        meta = reporting._extract_test_metadata(node)
        evs = by_test.get(node, [])
        counts = defaultdict(int)
        sample_prompt = None
        sample_answer = None
        parsed_count = 0
        for e in evs:
            counts[e.get("event")] += 1
            if e.get("event") == "PROMPT" and sample_prompt is None:
                sample_prompt = e.get("payload", {}).get("prompt")
            if e.get("event") == "ASSISTANT" and sample_answer is None:
                sample_answer = e.get("payload", {}).get("content")
            if e.get("event") == "PARSED_TOOL":
                parsed_count += 1
        log_hits = search_logs_for_test(node)

        doc_exists = bool(meta.get("description"))
        intent = "No model interaction expected"
        if "live" in (node or "") or any("live" == m for m in meta.get("markers", [])):
            intent = "Live model integration — expected a model-emitted tool call"
        if counts.get("ASSISTANT"):
            intent = "Model interaction recorded"

        rec = {
            "test": node,
            "file": meta.get("file"),
            "func": meta.get("func"),
            "line": meta.get("line"),
            "markers": meta.get("markers"),
            "docstring": meta.get("description"),
            "doc_present": doc_exists,
            "prompt_count": counts.get("PROMPT", 0),
            "assistant_count": counts.get("ASSISTANT", 0),
            "parsed_tool_count": counts.get("PARSED_TOOL", 0) or parsed_count,
            "sample_prompt": (sample_prompt or "")[:400] if sample_prompt else None,
            "sample_answer": (sample_answer or "")[:400] if sample_answer else None,
            "log_hits": log_hits,
            "intent": intent,
        }

        if not doc_exists:
            missing_doc.append(node)
        if rec["prompt_count"] + rec["assistant_count"] + rec["parsed_tool_count"] == 0:
            # investigate why there are no events for this test by scanning the test file for agent fixtures or calls
            scan = {"mentions": []}
            tf = meta.get("file")
            try:
                if tf and os.path.exists(tf):
                    src = open(tf, "r", encoding="utf-8", errors="ignore").read()
                    keywords = ["model_event_logger", "event_reader", "SingularityAgent", "execute_with_animation", "execute_streaming", "generate_streaming", "PROMPT", "ASSISTANT", "PARSED_TOOL", "agent ="]
                    for kw in keywords:
                        if kw in src:
                            scan["mentions"].append(kw)
            except Exception:
                pass
            rec["investigation"] = scan
            missing_events.append(node)
            if "Live model integration" in intent:
                live_expected_no_call.append(node)

        inventory.append(rec)

    report = {
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "counts": {
            "total_tests": len(nodes),
            "with_docstring": len(nodes) - len(missing_doc),
            "with_events": len(nodes) - len(missing_events),
            "missing_doc": len(missing_doc),
            "missing_events": len(missing_events),
            "live_expected_no_call": len(live_expected_no_call),
        },
        "inventory": inventory,
        "missing_doc": missing_doc,
        "missing_events": missing_events,
        "live_expected_no_call": live_expected_no_call,
        "events_path": events_path,
        "log_path": str(ROOT / "logs" / "singularity.log"),
    }

    out_path = REPORTS / "test_inventory.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Print concise summary
    print("Test inventory written to:", out_path)
    print()
    print("Summary:")
    for k, v in report["counts"].items():
        print(f"  {k}: {v}")

    if report["counts"]["missing_doc"]:
        print("\nTests missing docstrings (first 10):")
        for t in missing_doc[:10]:
            print(" -", t)

    if report["counts"]["missing_events"]:
        print("\nTests with no structured events (first 10):")
        for t in missing_events[:10]:
            print(" -", t)

        # Additional investigation: how many of these contain agent-related keywords
        mention_counts = {"has_mentions": 0, "no_mentions": 0}
        examples_with = []
        examples_without = []
        for node in missing_events:
            # find corresponding rec
            rec = next((r for r in inventory if r["test"] == node), None)
            mentions = (rec.get("investigation", {}) or {}).get("mentions", [])
            if mentions:
                mention_counts["has_mentions"] += 1
                if len(examples_with) < 5:
                    examples_with.append((node, mentions))
            else:
                mention_counts["no_mentions"] += 1
                if len(examples_without) < 5:
                    examples_without.append(node)
        print(f"\nOf tests missing events, {mention_counts['has_mentions']} mention agent/fixtures keywords and {mention_counts['no_mentions']} do not.")
        if examples_with:
            print("\nExamples that mention agent/fixtures (first 5):")
            for node, m in examples_with:
                print(" -", node, "=>", ",".join(m))
        if examples_without:
            print("\nExamples that do NOT mention agent/fixtures (first 5):")
            for node in examples_without:
                print(" -", node)

    if report["counts"]["live_expected_no_call"]:
        print("\nLive tests expected but missing model calls (first 10):")
        for t in live_expected_no_call[:10]:
            print(" -", t)

    return 0


if __name__ == "__main__":
    sys.exit(summarize())
