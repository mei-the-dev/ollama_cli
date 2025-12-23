#!/usr/bin/env python3
"""Enforce event coverage locally: fail if tests that mention agent/fixtures produce no events."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

sys.path.insert(0, str(ROOT))
try:
    from tests import reporting
except Exception as e:
    print("Failed to import tests.reporting:", e, file=sys.stderr)
    sys.exit(2)


events_path = os.environ.get("TEST_MODEL_EVENTS_PATH") or str(ROOT / "logs" / "test_model_events.jsonl")
by_test = reporting.parse_jsonl_events(events_path) if os.path.exists(events_path) else {}

# collect tests
cmd = [sys.executable, "-m", "pytest", "--collect-only", "-q"]
import subprocess
proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
nodes = [l.strip() for l in (proc.stdout or "").splitlines() if l.strip() and "::" in l]

# determine converted tests set (test names already generated into factory_converted rendered pytest files)
converted_tests = set()
for p in (ROOT / "tests" / "factory_converted").glob("*__factory_rendered_tests.py"):
    try:
        src = p.read_text()
        for line in src.splitlines():
            line = line.strip()
            if line.startswith('def test_'):
                fname = line.split()[1].split('(')[0]
                converted_tests.add(fname)
    except Exception:
        continue

missing = []
# Known tests or patterns to ignore in coverage enforcement (unit helpers, live-only integrations)
ignore_node_patterns = [
    "tests/test_factory_spec.py::test_to_pytest_code_contains_expected_snippet",
    "tests/test_mcp_tools.py::test_execute_streaming",
]
ignore_file_prefixes = [
    "tests/test_integration_live_",
]
for node in nodes:
    # quick ignore checks
    if any(pat in node for pat in ignore_node_patterns):
        continue
    if any(node.startswith(prefix) for prefix in ignore_file_prefixes):
        continue

    # scan file for agent keywords
    meta = reporting._extract_test_metadata(node)
    tf = meta.get("file")
    mentions = []
    if tf and os.path.exists(tf):
        src = open(tf, "r", encoding="utf-8", errors="ignore").read()
        # Try to restrict keyword scan to this specific test function body, to reduce file-level false positives
        func_src = None
        try:
            import ast
            tree = ast.parse(src)
            fname_only = node.split("::", 1)[1] if "::" in node else None
            if fname_only and fname_only.startswith('test_'):
                for node_ast in ast.walk(tree):
                    if isinstance(node_ast, (ast.FunctionDef, ast.AsyncFunctionDef)) and node_ast.name == fname_only:
                        lines = src.splitlines()
                        start = node_ast.lineno - 1
                        end = getattr(node_ast, 'end_lineno', node_ast.lineno)
                        func_src = '\n'.join(lines[start:end])
                        break
        except Exception:
            func_src = None

        # Only consider runtime fixtures or agent function usage as signals that a test should emit events.
        keywords = ["model_event_logger", "event_reader", "SingularityAgent", "execute_with_animation", "execute_streaming", "generate_streaming", "agent ="]
        scan_src = func_src if func_src is not None else src
        for k in keywords:
            if k in scan_src:
                mentions.append(k)
    if mentions:
        # skip if this test has been converted to a TestFactory rendered test already
        fname = node.split("::", 1)[1] if "::" in node else None
        # Skip generator helper test that just validates spec generation
        if fname == 'test_factory_generated' or node.endswith('::test_factory_generated'):
            continue
        if fname and (fname in converted_tests or ("test_" + fname) in converted_tests):
            continue
        evs = by_test.get(node, [])
        if not any(e.get("event") in ("ASSISTANT", "PARSED_TOOL", "PROMPT") for e in evs):
            missing.append({"test": node, "mentions": mentions})

if missing:
    print("Found tests that mention agent or fixtures but emitted NO structured events:")
    for m in missing:
        print(" -", m["test"], "mentions:", ",".join(m["mentions"]))
    print("Failing coverage check. Run tests with TEST_MODEL_EVENTS_PATH set to collect structured events.")
    sys.exit(3)

print("All agent-related tests emitted at least one structured event (or no agent usage found).")
sys.exit(0)
