#!/usr/bin/env python3
"""Run a battery of code-generation prompts against a local model (Ollama) and save results.

Usage:
  RUN_LIVE_OLLAMA=1 python scripts/prompt_tester.py

Outputs:
  reports/prompt_test_results.jsonl

This script is resilient: if Ollama is not reachable, it records failures and saves prompts for later.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "prompt_test_results.jsonl"
OUT.parent.mkdir(parents=True, exist_ok=True)

OLLAMA_BASE = os.environ.get("OLLAMA_URL") or "http://localhost:11434"
OLLAMA_URL = OLLAMA_BASE + "/api/chat"
USE_LIVE = os.environ.get("RUN_LIVE_OLLAMA") == "1"
TIMEOUT = 10


PROMPTS: List[str] = [
    # 1-10: basic helpers
    "Write a Python function `read_file(path)` that returns file contents with proper error handling and docstring.",
    "Write a CLI command (argparse) `count-lines` that prints the number of lines in a file and handles missing files gracefully.",
    "Generate a small Python module `fsutils.py` with `ensure_dir(path)` and tests for it.",
    "Provide a robust `parse_args(argv)` function that supports subcommands `init` and `run` and prints helpful usage.",
    "Write a function `atomic_write(path, content)` that writes to a temp file and renames to avoid partial files.",
    "Generate unit tests (pytest) for a function `is_valid_email(s)` with edge cases.",
    "Write a function that detects a project's virtualenv path cross-platform (Windows/Linux/Mac).",
    "Provide a small script that performs idempotent config file updates (adds key if missing), with tests.",
    "Write a code example that safely runs a shell command and captures stdout/stderr using subprocess.run.",
    "Suggest a good logging configuration for a CLI tool that writes to console and file with rotating logs.",

    # 11-20: CLI-specific code generation
    "Create a function `prompt_user_yes_no(prompt, default=True)` that handles CTRL-C and returns boolean.",
    "Write a function to pretty-print JSON colorized for terminal using 'rich' if available, fallback to print.",
    "Generate a `setup_logging()` helper that accepts a debug flag and configures logging accordingly.",
    "Write an interactive REPL loop that reads user commands, provides help, and supports `exit`/`quit`.",
    "Create a serializer that dumps dataclasses to JSON with support for datetime objects.",
    "Write code that validates config file schema (using pydantic or simple checks) and reports useful error messages.",
    "Generate a small plugin system loader that discovers entry points in a `plugins/` directory.",
    "Implement a retry decorator with exponential backoff and jitter for network calls.",
    "Write a CLI function that opens a URL in the user's preferred browser in a cross-platform way.",
    "Provide code to safely parse and normalize file paths, avoiding path traversal when given user input.",

    # 21-30: security and edge cases
    "Write a function that securely stores API tokens in the OS keyring with a fallback to file encryption.",
    "Generate code to sandbox execution of untrusted Python code (`ast` + restricted globals) and explain limitations.",
    "Write a function that validates and sanitizes filenames provided by users to prevent injection or traversal.",
    "Provide an example of how to limit subprocess resource usage (timeout + memory) on Linux.",
    "Implement a function that checks file permissions and warns if sensitive files are world-readable.",
    "Generate tests that simulate concurrent writes to a file and assert atomicity and correctness.",
    "Write code that performs safe JSON streaming parsing (for large JSON logs) without loading all into memory.",
    "Create a function to detect the OS distribution/version and print a friendly message.",
    "Write a linter-like function that checks for TODO or FIXME in repo files and returns a report.",
    "Provide example code for migrating a configuration schema with backward compatibility tests.",

    # 31-40: developer ergonomics
    "Create a helper that watches a folder for file changes and triggers a callback (use watchdog if present).",
    "Write a small script that creates a Python virtualenv and installs packages from requirements.txt.",
    "Generate an example of a CLI progress bar for long-running file downloads (chunked, resumable).",
    "Write code to generate a markdown report from test results and save it to reports/test_summary.md.",
    "Provide a fast approximate file search function for a repo using indexing (simple Python implementation).",
    "Create a debug helper that prints the current git branch, last commit, and uncommitted files in a single report.",
    "Write a function to run external linters (flake8/black) and parse their output into structured JSON.",
    "Generate CLI code that supports a `--config` flag and loads JSON/YAML configuration gracefully.",
    "Write a small utility that safely opens an editor for the user to edit a temp file and returns content.",
    "Provide code for a `--yes` / `--no` prompt wrapper used in scripts for non-interactive operation.",

    # 41-50: higher-level/quality checks
    "Write a function that annotates a piece of code with line numbers and shows a snippet for diagnostics.",
    "Generate an example of a SQL-safe query builder that prevents injection by parameterized queries.",
    "Create a test that ensures CLI exit codes are meaningful and documented for success/failure cases.",
    "Write code to run a quick health-check that validates external dependencies (DB, network, services) before starting.",
    "Provide a script to collect telemetry-like metrics (memory, cpu, runtime) for a command and write JSON.",
    "Implement a function to normalize timestamps to timezone-aware ISO format across the codebase.",
    "Write a generator that yields lines from a file but skips binary files and handles different encodings.",
    "Provide code that creates a minimal HTTP server to serve static test artifacts for local integration tests.",
    "Generate a small example that uses multiprocessing to parallelize CPU-bound tasks safely.",
    "Write a function that performs task cancellation and cleanup when SIGINT/SIGTERM are received.",
]


def call_ollama(prompt: str) -> dict:
    """Call local Ollama endpoint to generate a response. Tries to detect a model first.

    Supports both /api/chat and /api/generate styles depending on local Ollama.
    """
    # discover models
    try:
        tags = requests.get(OLLAMA_BASE + "/api/tags", timeout=3).json()
        models = [m.get('name') for m in (tags.get('models') or []) if m.get('name')]
    except Exception:
        models = []

    # prefer a coder model if present
    model = None
    for m in models:
        if 'coder' in m or 'code' in m:
            model = m
            break
    if not model and models:
        model = models[0]

    # try /api/generate if available
    gen_url = OLLAMA_BASE + "/api/generate"
    try:
        payload = {"model": model, "prompt": prompt, "max_tokens": 1024} if model else {"prompt": prompt, "max_tokens": 1024}
        r = requests.post(gen_url, json=payload, timeout=TIMEOUT)
        if r.status_code == 200:
            j = r.json()
            # Ollama generate returns {'id':..., 'choices': [{'content': '...'}], ...}
            choices = j.get('choices') or []
            if choices:
                content = choices[0].get('content') or ''
            else:
                content = json.dumps(j)
            return {"ok": True, "raw": j, "response": content}
    except Exception:
        pass

    # fallback to /api/chat
    try:
        payload = {"messages": [{"role": "user", "content": prompt}], "max_tokens": 1024, "model": model}
        r = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        j = r.json()
        content = None
        if isinstance(j, dict):
            choices = j.get('choices') or []
            if choices and isinstance(choices, list):
                msg = choices[0].get('message') if isinstance(choices[0], dict) else None
                if msg and isinstance(msg, dict):
                    content = msg.get('content')
        if content is None:
            content = json.dumps(j)
        return {"ok": True, "raw": j, "response": content}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run_all(prompts: List[str], cli_mode: str = "code", timeout: int = 60, retries: int = 1):
    """Run each prompt through the CLI in the specified `cli_mode` and capture outputs and structured events.

    - Uses the project's `singularity_cli.py` to exercise real flows (mcp_server, tool execution).
    - Writes a per-run TEST_MODEL_EVENTS_PATH (logs/test_model_events_prompt_<i>.jsonl) so the CLI records structured events.
    """
    results = []

    # Decide Python executable to run the CLI with (prefer venv)
    py = ROOT / ".venv" / "bin" / "python"
    if not py.exists():
        py = Path(sys.executable)

    cli_script = ROOT / "singularity_cli.py"
    if not cli_script.exists():
        raise FileNotFoundError("singularity_cli.py not found in repo root")

    for i, p in enumerate(prompts, start=1):
        ts = datetime.now(timezone.utc).isoformat()
        print(f"[{i}/{len(prompts)}] Prompt: {p[:80]}...")
        rec = {"i": i, "ts": ts, "prompt": p}

        # Create a unique events path for this run so we can inspect structured events
        events_path = ROOT / "logs" / f"test_model_events_prompt_{i}.jsonl"
        try:
            events_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        env = os.environ.copy()
        env["TEST_MODEL_EVENTS_PATH"] = str(events_path)
        env["RUN_LIVE_OLLAMA"] = "1" if USE_LIVE else "0"

        cmd = [str(py), str(cli_script), p, "-m", cli_mode, "--no-startup-config"]

        attempt = 0
        success = False
        last_err = None
        out_text = ""
        err_text = ""
        retcode = None
        while attempt <= retries and not success:
            attempt += 1
            try:
                pproc = __import__('subprocess').run(
                    cmd,
                    stdout=__import__('subprocess').PIPE,
                    stderr=__import__('subprocess').PIPE,
                    env=env,
                    timeout=timeout,
                    text=True,
                )
                out_text = (pproc.stdout or "").strip()
                err_text = (pproc.stderr or "").strip()
                retcode = pproc.returncode

                # Read structured events if present
                events = []
                if events_path.exists():
                    try:
                        with open(events_path, "r", encoding="utf-8") as fh:
                            for ln in fh:
                                try:
                                    events.append(json.loads(ln))
                                except Exception:
                                    continue
                    except Exception:
                        events = []

                # Consider success if retcode == 0 and we have either assistant or parsed_tool events
                has_model_events = any(e.get("event") in ("ASSISTANT", "PARSED_TOOL", "PROMPT") for e in events)
                if retcode == 0 and (has_model_events or out_text):
                    success = True
                    rec.update({
                        "ok": True,
                        "returncode": retcode,
                        "stdout": out_text,
                        "stderr": err_text,
                        "events": events,
                    })
                else:
                    last_err = f"retcode={retcode}; has_model_events={has_model_events}"
                    rec.update({
                        "ok": False,
                        "returncode": retcode,
                        "stdout": out_text,
                        "stderr": err_text,
                        "events": events,
                        "error": last_err,
                    })

            except __import__('subprocess').TimeoutExpired as e:
                last_err = f"timeout after {timeout}s"
                rec.update({"ok": False, "error": last_err, "stdout": e.stdout, "stderr": e.stderr})
            except Exception as e:
                last_err = str(e)
                rec.update({"ok": False, "error": last_err})

            if not success and attempt <= retries:
                print(f"Attempt {attempt} failed: {last_err}. Retrying...")
                time.sleep(1)

        # Save incremental
        with open(OUT, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        results.append(rec)
        # small pause to avoid overwhelming local services
        time.sleep(0.2)

    return results


if __name__ == "__main__":
    print(f"Using live Ollama: {USE_LIVE}; endpoint: {OLLAMA_URL}")
    res = run_all(PROMPTS)
    succ = len([r for r in res if r.get('ok')])
    print(f"Done. {succ}/{len(res)} prompts succeeded. Results written to: {OUT}")
    sys.exit(0 if succ == len(res) else 2)
