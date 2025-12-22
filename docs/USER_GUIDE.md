# Singularity User Guide

## Overview
Omarchy is an AI coding assistant that combines an interactive CLI and a local MCP server that exposes developer tools. It focuses on safe code edits, context-aware actions, and reproducible workflows.

## CLI Highlights
- Artistic, distraction-less banner and layout
- Context providers: use `@file:src/foo.py`, `@web:http://...`, `@diff`, `@tree` in prompts to inject context
- Tool-calls: The model will emit JSON tool calls (e.g. `{ "tool": "write_code", "args": {...} }`) to request actions. The CLI executes them safely and optionally prompts for confirmation.

## Configuration (`~/.singularity/config.json`)
Key fields:
- `allow_sudo`: boolean (default `false`) — opt-in to allow sudo in server `execute_code`
- `auto_apply`: boolean (default `false`) — opt-in to let the CLI auto-apply `write_code` requests

## Startup Workflow
On first start, Omarchy asks to:
1. Transfer knowledge (loads `~/.singularity/knowledge/*.json` into system prompt)
2. Transfer conversation context (loads `~/.singularity/context/context.json`) 
3. Enable auto-apply for file writes
4. Enable sudo and optionally store sudo password for the session

## Safety
- Sudo requires explicit opt-in and `sudo -n` is used to avoid interactive prompts.
- File writes require confirmation unless `auto_apply` is enabled.

## Examples
- Generate code and write directly to `src/main.py`:
  - `/mode code` → "Create a FastAPI app that returns status" → If the model returns `{ "tool": "write_code", "args": {"filepath": "src/main.py", "content": "...", "mode": "overwrite"}}`, the CLI will ask to apply.

## Development & Tests
Run tests with `./.venv/bin/python -m pytest -q`. Use `SINGULARITY_SKIP_OLLAMA=1` in CI.

## Contributing
Please open PRs against the main repo and include tests for new tools or behaviors.
