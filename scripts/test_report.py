#!/usr/bin/env python3
"""Pretty Test Run Reporter

Runs pytest (opt-in live tests allowed via RUN_LIVE_OLLAMA=1), captures output,
parses the summary, and prints a concise, colored, human-friendly report using
`rich` for the terminal.

Usage:
    python scripts/test_report.py           # Run pytest and render a report
    python scripts/test_report.py --no-run  # Parse an existing pytest output file

This script is intended to help developers quickly understand the test pipeline
health and surface failing tests, slow tests, and the live-test status.
"""

import argparse
import os
import re
import shlex
import subprocess
import sys
import json
from textwrap import shorten

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box
except Exception:
    print("Missing dependency 'rich'. Install with: python -m pip install rich", file=sys.stderr)
    sys.exit(2)

console = Console()

# Color palette (shared)
PALETTE = {
    "primary": "#cc7722",  # strong orange
    "accent1": "#d6924e",
    "accent2": "#e0ad7a",
    "muted": "#ebc9a7",
    "bg": "#f5e4d3",
}

PYTEST_CMD = "pytest -q --disable-warnings --durations=10"

COUNT_KEYS = ["passed", "failed", "skipped", "xfailed", "xpassed", "errors", "warnings"]


def run_pytest() -> str:
    """Run pytest (using the invoking Python interpreter) and return captured stdout+stderr as text.

    Using `python -m pytest` keeps the run hermetic inside the current virtualenv.
    """
    cmd = [sys.executable, "-m", "pytest", "-q", "--disable-warnings", "--durations=10"]
    console.print(f"[dim]Running:[/dim] [green]{' '.join(cmd)}[/green]")
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return proc.stdout


def parse_counts(output: str) -> dict:
    counts = {k: 0 for k in COUNT_KEYS}

    # Search for occurrences like '52 passed' or '1 failed'
    for k in COUNT_KEYS:
        m = re.search(rf"(\d+)\s+{k}\b", output)
        if m:
            counts[k] = int(m.group(1))

    # If nothing found, try to catch 'collected N items'
    m = re.search(r"collected\s+(\d+)\s+items?", output)
    if m:
        counts["collected"] = int(m.group(1))

    return counts


def parse_slowest(output: str, max_items: int = 5) -> list:
    """Parse pytest 'slowest durations' block (simple heuristic)."""
    lines = output.splitlines()
    slow_lines = []
    capture = False
    for L in lines:
        if "slowest" in L.lower() and "durations" in L.lower():
            capture = True
            continue
        if capture:
            if not L.strip():
                break
            # Example lines: '0.86s call     tests/test_x.py::test_y'
            m = re.search(r"\s*(\d+\.\d+)s\s+.*?\s+(.*)$", L)
            if m:
                slow_lines.append((float(m.group(1)), m.group(2).strip()))
            if len(slow_lines) >= max_items:
                break
    return slow_lines


def find_failures(output: str, max_items: int = 10) -> list:
    """Find lines that indicate failing tests (FAILED lines)."""
    failures = []
    for line in output.splitlines():
        if line.startswith("FAILED ") or line.startswith("FAILED\t"):
            failures.append(line)
        # pytest sometimes prints 'FAILED tests/...' alone
        if line.strip().startswith("FAILED") and "::" in line:
            failures.append(line.strip())
    return failures[:max_items]


def check_ollama() -> tuple[bool, str]:
    """Quickly check if local Ollama appears reachable."""
    import requests

    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=1)
        r.raise_for_status()
        models = [m.get("name") for m in r.json().get("models", []) if m.get("name")]
        top = models[:3]
        return True, ", ".join(top) if top else "(no models found)"
    except Exception as e:
        return False, str(e)


def _balanced_json_objects(text: str) -> list:
    """Extract all balanced JSON object substrings from text.

    This is a simple scanner that returns each top-level JSON object it finds.
    """
    objs = []
    start = None
    depth = 0
    for i, ch in enumerate(text):
        if ch == '{':
            if start is None:
                start = i
            depth += 1
        elif ch == '}':
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    objs.append(text[start:i+1])
                    start = None
    return objs


def collect_model_outputs(pytest_output: str, log_path: str = "logs/singularity.log", max_entries: int = 10) -> list:
    """Collect model/assistant outputs from pytest output and the singularity log file.

    Returns a list of textual entries (JSON or plain text), newest-first, up to `max_entries`.
    """
    entries = []

    # 1) Fenced JSON blocks from pytest output (```json ... ```)
    fenced = re.findall(r"```json\n(.*?)```", pytest_output, re.DOTALL | re.IGNORECASE)
    for f in fenced:
        entries.append(f.strip())

    # 2) Any balanced JSON objects embedded in pytest output
    for obj in _balanced_json_objects(pytest_output):
        entries.append(obj)

    # 3) Parse the singularity log for assistant messages and JSON
    try:
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
                log_text = fh.read()
                # Heuristic: include lines that mention 'assistant' or 'Parsed tool call' or look JSON-like
                for line in reversed(log_text.splitlines()):
                    if len(entries) >= max_entries:
                        break
                    l = line.strip()
                    if not l:
                        continue
                    if "assistant" in l.lower() or "parsed tool" in l.lower() or (l.startswith("{") and l.endswith("}")):
                        entries.append(l)
                # Also include any balanced JSON objects found in logs
                for obj in _balanced_json_objects(log_text):
                    if len(entries) >= max_entries:
                        break
                    entries.append(obj)
    except Exception:
        pass

    # Deduplicate while preserving order (newest-first behaviour already applied by searching logs reversed)
    seen = set()
    out = []
    for e in entries:
        if e in seen:
            continue
        seen.add(e)
        out.append(e)
        if len(out) >= max_entries:
            break

    return out


def collect_model_call_cards(log_path: str = "logs/singularity.log", max_cards: int = 10) -> list:
    """Parse the singularity log and create cards for each PROMPT -> assistant pair.

    Each card is a dict: { 'test': <pytest id or 'unknown'>, 'prompt': <str>, 'answer': <str>, 'parsed_tool': <optional str> }
    """
    cards = []

    if not os.path.exists(log_path):
        return cards

    with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()

    prompt_re = re.compile(r"PROMPT \[(?P<test>[^\]]*)\]: (?P<prompt>.*)$")
    assistant_re = re.compile(r"assistant:\s*(?P<assistant>.*)$", re.IGNORECASE)
    parsed_re = re.compile(r"Parsed tool call:\s*(?P<parsed>\{.*\})\s*->\s*normalized to:\s*(?P<norm>\{.*\})", re.IGNORECASE)
    timestamp_re = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}")

    current_prompt = None
    current_test = "unknown"
    current_parsed = None

    i = 0
    while i < len(lines):
        line = lines[i]
        l = line.strip()
        i += 1
        if not l:
            continue
        pm = prompt_re.search(l)
        if pm:
            current_test = pm.group("test") or "unknown"
            current_prompt = pm.group("prompt")
            current_parsed = None
            continue
        pr = parsed_re.search(l)
        if pr and current_prompt is not None:
            current_parsed = pr.group("parsed")
            continue
        am = assistant_re.search(l)
        if am and current_prompt is not None:
            # capture multiline assistant content until next timestamped log line
            answer_lines = [am.group("assistant")]
            while i < len(lines) and not timestamp_re.match(lines[i]):
                # Preserve leading whitespace (do not strip) to keep JSON indentation intact
                answer_lines.append(lines[i].rstrip("\n"))
                i += 1
            # Join without stripping to preserve formatting
            answer = "\n".join(answer_lines)
            cards.append({"test": current_test, "prompt": current_prompt, "answer": answer, "parsed_tool": current_parsed})
            current_prompt = None
            current_test = "unknown"
            current_parsed = None
            if len(cards) >= max_cards:
                break

    # Keep newest-first order
    cards = list(reversed(cards))

    return cards


def collect_all_tests() -> list:
    """Run pytest --collect-only and return a list of collected test node ids.

    This helps ensure every test has a card in the report (placeholder if needed).
    """
    try:
        cmd = [sys.executable, "-m", "pytest", "--collect-only", "-q"]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        lines = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
        # Keep only nodeids (lines containing '::')
        nodes = [l for l in lines if "::" in l]
        return nodes
    except Exception:
        return []


def render_report(output: str):
    counts = parse_counts(output)
    slow = parse_slowest(output)
    failures = find_failures(output)

    passed = counts.get("passed", 0)
    failed = counts.get("failed", 0)
    skipped = counts.get("skipped", 0)

    # Title / overall status
    if failed > 0:
        title = Text("TEST SUITE: FAILURES", style="bold white on red")
    else:
        title = Text("TEST SUITE: ALL GREEN", style=f"bold white on {PALETTE['primary']}")

    console.rule(title)

    # Summary table
    tbl = Table.grid(expand=True)
    tbl.add_column(justify="left", ratio=2)
    tbl.add_column(justify="right", ratio=1)

    tbl.add_row("Passed", f"[{PALETTE['accent2']}]" + str(passed) + "[/]")
    tbl.add_row("Failed", f"[red]{failed}[/red]")
    tbl.add_row("Skipped", f"[{PALETTE['muted']}]" + str(skipped) + "[/]")

    if counts.get("xfailed"):
        tbl.add_row("XFailed", f"[magenta]{counts.get('xfailed')}[/magenta]")
    if counts.get("xpassed"):
        tbl.add_row("XPassed", f"[magenta]{counts.get('xpassed')}[/magenta]")

    # Run environment highlights
    env_table = Table.grid(expand=True)
    env_table.add_column(justify="left")
    env_table.add_column(justify="right")
    run_live = os.environ.get("RUN_LIVE_OLLAMA") == "1"
    env_table.add_row("RUN_LIVE_OLLAMA", f"[bold]{run_live}[/bold]")

    ollama_ok, ollama_note = check_ollama()
    env_table.add_row("Ollama reachable", f"[green]{ollama_ok}[/green]" if ollama_ok else f"[red]{ollama_ok}[/red]")
    env_table.add_row("Ollama note", shorten(ollama_note, width=60))

    console.print(Panel(tbl, title="Summary", subtitle="Quick counts", expand=False, box=box.ROUNDED, border_style=PALETTE['accent1']))
    console.print(Panel(env_table, title="Environment", expand=False, box=box.ROUNDED, border_style=PALETTE['accent2']))

    # Slow tests
    if slow:
        s_tbl = Table(title="Top slow tests (seconds)", box=box.MINIMAL_DOUBLE_HEAD)
        s_tbl.add_column("Time", justify="right")
        s_tbl.add_column("Test")
        for t, name in slow:
            s_tbl.add_row(f"{t:.2f}", shorten(name, width=80))
        console.print(s_tbl)

    # Failures
    if failures:
        f_tbl = Table(title="Failing tests (showing up to 10)", box=box.SQUARE)
        f_tbl.add_column("Failure")
        for f in failures:
            f_tbl.add_row(f)
        console.print(Panel(f_tbl, title="Failures", style="red", box=box.ROUNDED))

    # Tail of output for quick inspection
    tail = "\n".join(output.splitlines()[-20:])
    console.print(Panel(Text(tail), title="Last output (tail)", expand=False, box=box.ROUNDED))

    # Prefer structured JSONL events if available; only load for terminal display (no file exports)
    events_path = os.environ.get("TEST_MODEL_EVENTS_PATH") or os.path.join(os.getcwd(), "logs", "test_model_events.jsonl")
    cards = []
    if os.path.exists(events_path):
        try:
            from tests.reporting import parse_jsonl_events, build_cards_from_events

            by_test = parse_jsonl_events(events_path)
            cards = build_cards_from_events(by_test)
            console.print(f"[dim]Loaded {len(cards)} structured event cards from {events_path}[/dim]")
        except Exception as e:
            console.print(f"[yellow]Failed to parse structured events: {e}[/yellow]")

    # Fallback to heuristic model output parsing if no structured events found
    if not cards:
        model_outputs = collect_model_outputs(output, log_path=os.path.join(os.getcwd(), "logs", "singularity.log"), max_entries=12)
        if model_outputs:
            from rich.syntax import Syntax

            m_tbl = Table(title="Model / Assistant Outputs", box=box.SQUARE, expand=False)
            m_tbl.add_column("#", justify="right", width=3)
            m_tbl.add_column("Output", overflow="fold")

            timestamp_re = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})\s+(?P<level>\w+)\s+(?P<msg>.*)$")

            for i, o in enumerate(model_outputs, start=1):
                trimmed = o.strip()

                # If looks like JSON, pretty-print and syntax highlight
                is_json = trimmed.startswith("{") and trimmed.endswith("}")
                if is_json:
                    try:
                        j = json.loads(trimmed)
                        pretty = json.dumps(j, indent=2)
                        syntax = Syntax(pretty, "json", theme="monokai", line_numbers=False)
                        # Put JSON in a Panel-like display (color the border with primary color)
                        out = syntax
                        m_tbl.add_row(str(i), out)
                        continue
                    except Exception:
                        pass

                # Try to extract timestamped log lines like: '2025-12-22 23:05:57,112 INFO ...'
                m = timestamp_re.match(trimmed)
                if m:
                    ts = m.group("ts")
                    level = m.group("level")
                    msg = m.group("msg")
                    txt = Text()
                    txt.append(ts + " ", style=f"{PALETTE['muted']}")
                    txt.append(f"[{level}] ", style=f"bold {PALETTE['primary']}")
                    # Color the message with alternating accents for readability
                    msg_lines = msg.split(" -> ")
                    for idx, part in enumerate(msg_lines):
                        style = PALETTE['accent1'] if idx % 2 == 0 else PALETTE['accent2']
                        txt.append(part, style=style)
                        if idx != len(msg_lines) - 1:
                            txt.append(" -> ", style=f"{PALETTE['muted']}")
                    m_tbl.add_row(str(i), txt)
                    continue

                # Fallback: raw text (shortened)
                txt = Text(shorten(trimmed, width=200), style=PALETTE['accent2'])
                m_tbl.add_row(str(i), txt)

            console.print(Panel(m_tbl, title="Model Outputs", expand=False, box=box.ROUNDED, border_style=PALETTE['primary']))
        from rich.syntax import Syntax

        m_tbl = Table(title="Model / Assistant Outputs", box=box.SQUARE, expand=False)
        m_tbl.add_column("#", justify="right", width=3)
        m_tbl.add_column("Output", overflow="fold")

        timestamp_re = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})\s+(?P<level>\w+)\s+(?P<msg>.*)$")

        for i, o in enumerate(model_outputs, start=1):
            trimmed = o.strip()

            # If looks like JSON, pretty-print and syntax highlight
            is_json = trimmed.startswith("{") and trimmed.endswith("}")
            if is_json:
                try:
                    j = json.loads(trimmed)
                    pretty = json.dumps(j, indent=2)
                    syntax = Syntax(pretty, "json", theme="monokai", line_numbers=False)
                    # Put JSON in a Panel-like display (color the border with primary color)
                    out = syntax
                    m_tbl.add_row(str(i), out)
                    continue
                except Exception:
                    pass

            # Try to extract timestamped log lines like: '2025-12-22 23:05:57,112 INFO ...'
            m = timestamp_re.match(trimmed)
            if m:
                ts = m.group("ts")
                level = m.group("level")
                msg = m.group("msg")
                txt = Text()
                txt.append(ts + " ", style=f"{PALETTE['muted']}")
                txt.append(f"[{level}] ", style=f"bold {PALETTE['primary']}")
                # Color the message with alternating accents for readability
                msg_lines = msg.split(" -> ")
                for idx, part in enumerate(msg_lines):
                    style = PALETTE['accent1'] if idx % 2 == 0 else PALETTE['accent2']
                    txt.append(part, style=style)
                    if idx != len(msg_lines) - 1:
                        txt.append(" -> ", style=f"{PALETTE['muted']}")
                m_tbl.add_row(str(i), txt)
                continue

            # Fallback: raw text (shortened)
            txt = Text(shorten(trimmed, width=200), style=PALETTE['accent2'])
            m_tbl.add_row(str(i), txt)

        console.print(Panel(m_tbl, title="Model Outputs", expand=False, box=box.ROUNDED, border_style=PALETTE['primary']))

        # Build Model Call Cards (PROMPT -> assistant pairs)
        cards = collect_model_call_cards(log_path=os.path.join(os.getcwd(), "logs", "singularity.log"), max_cards=999)

        # Ensure every collected test has a card (create placeholder if missing), enrich with metadata and snippet
        collected_tests = collect_all_tests()
        existing_tests = [c.get("test", "") for c in cards]
        for t in collected_tests:
            if not any(t in et or et in t for et in existing_tests):
                # Try to enrich placeholder with file, line, markers, description and a small test snippet
                try:
                    meta = reporting._extract_test_metadata(t)
                except Exception:
                    meta = {"file": None, "line": None, "description": None, "markers": []}
                test_snippet = None
                try:
                    tf = meta.get("file")
                    ln = meta.get("line")
                    if tf and ln and os.path.exists(tf):
                        with open(tf, "r", encoding="utf-8", errors="ignore") as fh:
                            lines = fh.read().splitlines()
                        start = max(ln - 1, 0)
                        snippet = lines[start : start + 6]
                        test_snippet = "\n".join(snippet).strip()
                except Exception:
                    test_snippet = None

                card = {
                    "test": t,
                    "file": meta.get("file"),
                    "line": meta.get("line"),
                    "markers": meta.get("markers", []),
                    "description": meta.get("description") or "(no test description)",
                    "test_snippet": test_snippet,
                    "prompt": "(no prompt logged)",
                    "answer": "(no model call)",
                    "parsed_tool": None,
                    "intent": "No model interaction expected",
                    "timestamps": {},
                }
                cards.append(card)

        # Load optional overrides to customize descriptions/results
        overrides_path = os.path.join(os.getcwd(), "test_report_overrides.json")
        overrides = {}
        if os.path.exists(overrides_path):
            try:
                overrides = json.loads(open(overrides_path, "r", encoding="utf-8").read())
            except Exception:
                overrides = {}

        # Sort cards by test name for stable output
        cards_sorted = sorted(cards, key=lambda c: c.get("test", ""))

        # Report-level feature flags via env vars
        hide_empty = os.environ.get("HIDE_EMPTY_CARDS") == "1"
        only_model_calls = os.environ.get("ONLY_MODEL_CALLS") == "1"
        group_by_module = os.environ.get("GROUP_BY_MODULE") == "1"

        # Counters for summary
        counts_cards = {"PASS": 0, "MISSING": 0, "NO CALL": 0}

        # Optionally group cards by file/module
        prev_file = None
        display_index = 1
        for c in cards_sorted:
            file = c.get("file")
            ans = c.get("answer", "")

            # Skip empty placeholders when requested
            if only_model_calls and (not ans or ans == "(no model call)"):
                continue
            if hide_empty and (not ans or ans == "(no model call)"):
                continue

            # Grouping header
            if group_by_module and file and file != prev_file:
                console.print(Panel(Text(f"{file}", style=f"bold {PALETTE['primary']}"), box=box.MINIMAL, expand=True, border_style=PALETTE['accent2']))
                prev_file = file

            # Pretty title with result badge
            measurement = c.get("test", "unknown")
            override = overrides.get(measurement, {})

            if ans == "(no model call)":
                description = override.get("description") or (
                    "Live model integration — expected a model-emitted tool call" if any(k in measurement.lower() for k in ("live", "integration", "ollama", "stream")) else "No model interaction expected"
                )
                expected = override.get("expected") or ("Model call required" if "expected" not in override and "live" in measurement.lower() else override.get("expected", "N/A"))
                if "model" in expected.lower() and "required" in expected.lower():
                    result_text = "MISSING"
                    result_style = "bold white on red"
                else:
                    result_text = "NO CALL"
                    result_style = f"bold {PALETTE['muted']}"
            else:
                description = override.get("description") or "Model interaction recorded"
                expected = override.get("expected") or "Model call occurred"
                result_text = "PASS"
                result_style = "bold white on green"

            counts_cards.setdefault(result_text, 0)
            counts_cards[result_text] = counts_cards.get(result_text, 0) + 1

            # Render answer with syntax highlighting
            try:
                parsed = json.loads(ans)
                ans_render = Syntax(json.dumps(parsed, indent=2), "json", theme="monokai", line_numbers=False)
            except Exception:
                ans_render = Syntax(ans or "(no model call)", "text", theme="monokai", line_numbers=False)

            # Build card body
            sub = Table.grid(expand=False)
            sub.add_column(ratio=1)

            # Context lines
            ctx_lines = []
            line = c.get("line")
            markers = c.get("markers") or []
            if file:
                ctx_lines.append(f"File: {file}{(':' + str(line)) if line else ''}")
            if markers:
                ctx_lines.append("Markers: " + ", ".join(markers))
            if ctx_lines:
                sub.add_row(Text("Context:", style=f"bold {PALETTE['primary']}"))
                for cl in ctx_lines:
                    sub.add_row(Text(cl, style=PALETTE['muted']))

            sub.add_row(Text("Description:", style=f"bold {PALETTE['primary']}"))
            sub.add_row(Text(c.get('description', '(no test description)'), style=PALETTE['muted']))

            snippet = c.get('test_snippet')
            if snippet and (not c.get('prompt') or c.get('prompt') == '(no prompt logged)'):
                sub.add_row(Text("Test snippet:", style=f"bold {PALETTE['primary']}"))
                from rich.syntax import Syntax

                lines = snippet.splitlines()[:4]
                sub.add_row(Syntax("\n".join(lines), "python", theme="monokai", line_numbers=False))

            sub.add_row(Text("Prompt:", style=f"bold {PALETTE['primary']}"))
            sub.add_row(Text(c.get('prompt', ''), style=PALETTE['muted']))

            sub.add_row(Text("Answer:", style=f"bold {PALETTE['primary']}"))
            sub.add_row(ans_render)

            # Parsed tool if present
            parsed_tool = c.get('parsed_tool')
            if parsed_tool:
                try:
                    parsed_json = json.dumps(parsed_tool, indent=2)
                    sub.add_row(Text("Parsed tool:", style=f"bold {PALETTE['primary']}"))
                    sub.add_row(Syntax(parsed_json, "json", theme="monokai", line_numbers=False))
                except Exception:
                    sub.add_row(Text("Parsed tool:", style=f"bold {PALETTE['primary']}"))
                    sub.add_row(Text(str(parsed_tool), style=PALETTE['muted']))

            sub.add_row(Text("Intent:", style=f"bold {PALETTE['primary']}"))
            sub.add_row(Text(c.get('intent', ''), style=PALETTE['muted']))

            sub.add_row(Text("Result:", style=f"bold {PALETTE['primary']}"))
            sub.add_row(Text(result_text, style=result_style))

            # Title includes index and shortcut info
            short_title = f"{display_index}. {measurement}"
            badge = Text(f" {result_text} ", style=result_style)
            card_panel = Panel(sub, title=short_title, subtitle=badge, border_style=("red" if result_text == "MISSING" else PALETTE['accent1']), expand=True, box=box.ROUNDED)
            console.print(card_panel)

            display_index += 1

        # Summary: how many tests vs cards
        # Summary: how many tests vs cards
        total = len(collected_tests)
        with_cards = len([c for c in cards_sorted if c.get('answer') and c.get('answer') != '(no model call)'])
        missing = total - with_cards
        summary_tbl = Table.grid(expand=True)
        summary_tbl.add_column()
        summary_tbl.add_column(justify="right")
        summary_tbl.add_row("Collected tests", str(total))
        summary_tbl.add_row("Model call cards", str(len(cards_sorted)))
        summary_tbl.add_row("Tests with no model call", f"[yellow]{missing}[/yellow]")
        console.print(Panel(summary_tbl, title="Cards Summary", border_style=PALETTE['primary'], box=box.ROUNDED))

    console.rule(Text("End report", style="bold"))


def main():
    p = argparse.ArgumentParser(description="Run pytest and print a terminal-only report")
    p.add_argument("--no-run", action="store_true", help="Don't run pytest; read from stdin")
    args = p.parse_args()

    if args.no_run:
        console.print("Reading pytest output from stdin... (pipe output into this script)")
        output = sys.stdin.read()
    else:
        output = run_pytest()

    render_report(output)



if __name__ == "__main__":
    main()
