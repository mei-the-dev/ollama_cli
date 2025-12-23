# Singularity Rework — Detailed Task Specifications

This document contains detailed specifications for each task in the rebrand / stabilization / feature plan. For each task you will find: **Goal**, **Motivation**, **Inputs & Outputs**, **Implementation Steps**, **API / Contracts**, **Tests & Verification**, **Acceptance Criteria**, **Rollback / Safety**, and **Estimates**.

---

## 1) Start MCP server subprocess (PRIORITY: CRITICAL)

- Goal
  - Start a local MCP server process from the CLI, capture the actual listening address (host:port), and store the URL on the agent instance.

- Motivation
  - The CLI must talk to a real MCP server for tools (write_code, search_files, execute_code, etc.). Starting it reliably is required before any tool calls.

- Inputs
  - Candidate MCP server locations (in order): `~/.singularity/mcp_server.py`, `./mcp_server.py`, `./fast_mcp_server.py`.
  - Optional CLI flags: `--mcp-path`, `--mcp-host`, `--mcp-port`.

- Outputs
  - `self.mcp_process` pointing to the subprocess
  - `self.mcp_server_url = 'http://host:port'`
  - Log lines indicating start or failure

- Implementation Steps
  1. Add method `SingularityAgent.start_mcp_server()` that:
     - Detects file to run (prefer user-installed path `~/.singularity/mcp_server.py`, fallback local files)
     - Launches subprocess via `asyncio.create_subprocess_exec(sys.executable, path, stdout=PIPE, stderr=PIPE)`
     - Reads stdout lines until it finds a recognizable listen announcement, e.g. `MCP server listening on 127.0.0.1:XXXXX` (use regex to extract host & port)
     - Timeout if announcement not seen in configurable window (default 5s)
     - Set `self.mcp_server_url` and return True on success; return False on failure
  2. Add `stop_mcp_server()` to terminate gracefully (SIGTERM then wait then SIGKILL fallback)
  3. Add proper logging & console feedback
  4. Add CLI flag `--startup-wait` and `--mcp-path` to override behavior for testing

- API / Contracts
  - No HTTP changes yet; spawns process; sets attribute `agent.mcp_server_url`

- Tests & Verification
  - Unit test: mock `asyncio.create_subprocess_exec` to supply a fake stdout that prints the listen line; assert the method returns True and sets URL
  - Integration: call `singularity --startup-check-only` and assert printed `Startup check: MCP server at http://...`

- Acceptance Criteria
  - `--startup-check-only` reliably starts server and prints the URL
  - `agent.mcp_server_url` set for later tool calls

- Rollback / Safety
  - If start fails, CLI should continue but mark MCP unavailable and offer informative instructions

- Estimate: 2–4 hours

---

## 2) Capture MCP server URL (PRIORITY: CRITICAL)

- Goal
  - Robustly parse process stdout to extract final bind address and port.

- Implementation Steps
  1. Use incremental reading of lines from `proc.stdout` with a short timeout & read loop
  2. Accept several message formats — use regex to find IPv4 address + port or `127.0.0.1:12345`
  3. If server uses dynamic port (port=0), ensure parent captures the printed port
  4. Provide diagnostic message if URL not recovered

- Tests
  - Unit: feed sample stdout variations to the parser and assert extracted URL
  - Integration: ensure `fast_mcp_server.py` prints the listen message and parent captures it

- Acceptance Criteria
  - In 95% of environment variations the URL is captured and stored

- Estimate: 1–2 hours

---

## 3) Implement MCP HTTP client (PRIORITY: CRITICAL)

- Goal
  - Provide a typed async client that calls the MCP server `/call` endpoint and returns normalized results.

- Motivation
  - All tool operations flow through the MCP HTTP API — this client standardizes errors & timeouts.

- Inputs
  - `mcp_server_url`, `name`, `arguments` dictionary

- Outputs
  - `ToolResult`-shaped dict: `{ status, data, error, warnings, execution_time_ms }`

- Implementation Steps
  1. Add `SingularityAgent.call_mcp_tool(name, arguments)` (async): uses `aiohttp.ClientSession()` and POST to `f'{mcp_url}/call'`
  2. Use `ClientTimeout(total=30)` and decode JSON; translate errors into structured dict
  3. Add safe retry policy for transient errors (2 retries with backoff)
  4. Surface structured errors to CLI with pretty printing

- API / Contracts
  - Expected server response of form: `{'status': 'SUCCESS', 'data': {...}}` or ToolResult-like dict

- Tests
  - Unit tests with aiohttp test server returning success, error, and timeouts

- Acceptance Criteria
  - Reliable JSON parsing & error handling; tests exercise success & error statuses

- Estimate: 2–3 hours

---

## 4) Integrate Ollama streaming (PRIORITY: CRITICAL)

- Goal
  - Replace curl subprocess usage with proper async streaming using `aiohttp` to `http://localhost:11434/api/chat`.

- Motivation
  - Real streaming is necessary for progressive UI updates and detecting tool calls mid-stream.

- Inputs
  - System messages (tools, instructions), conversation messages, model config

- Outputs
  - An async generator `generate_streaming(prompt, system)` that yields content chunks and indicates completion

- Implementation Steps
  1. Implement `SingularityAgent.generate_streaming(prompt, system)` using `aiohttp` POST with `stream=True`
  2. Parse line-delimited JSON chunks; yield content fragments as received
  3. Detect streaming 'done' events or final messages
  4. Integrate with CLI live streaming display (Rich Live / prompt_toolkit)
  5. Capture model-suggested tool calls when JSON object representing a tool is emitted

- Tests
  - Unit: mock aiohttp stream to emit sample JSON lines (including tool calls) and assert generator yields and final history updated
  - Integration: requires `ollama serve` running — add CI gating or mock server

- Acceptance Criteria
  - Prompts stream in UI, not in monolithic blocks; tool calls exposed

- Estimate: 4–8 hours

---

## 5) Parse and handle tool calls (PRIORITY: CRITICAL)

- Goal
  - When model returns JSON tool-call objects, detect them, call corresponding MCP tool, and inject results back into conversation.

- Implementation Steps
  1. After collecting streamed response chunk(s), check whether the final assistant content is a JSON tool call (or contains a single JSON object)
  2. Validate object: `{'tool': '<name>', 'args': {...}}` or follow alternative agreed schema
  3. Use `call_mcp_tool()` to execute, show execution progress, and present the result to the user
  4. Optionally append tool result as a system message and continue conversation (multi-turn)

- Tests
  - Simulate model output containing tool call; assert MCP client POST invoked and results printed and appended to history

- Acceptance Criteria
  - Tool calls execute and show success/failure; conversation continues post tool call

- Estimate: 4–6 hours

---

## 6) Implement @file provider (PRIORITY: HIGH)

- Goal
  - Expand `@file:PATH` support to reliably read files, clamp sizes, and inject content into the prompt (with proper escaping and truncation).

- Implementation Steps
  1. Add `parse_context(prompt)` that finds `@file:<path>` tokens
  2. Resolve relative paths against workspace root; support glob patterns `@file:src/*.py`
  3. Read file content, limit to X characters (configurable, 8k default), and append to prompt with a header marker
  4. Add completion support to help users pick paths (see task 10)

- Tests
  - Unit test reading local files and ensuring content insertion and truncation

- Acceptance Criteria
  - `@file:` context is included in the prompt sent to model; autocompletion suggests workspace files

- Estimate: 2–3 hours

---

## 7) Implement @web provider (PRIORITY: HIGH)

- Goal
  - Replace ad-hoc @web handling with formal provider that uses MCP `fetch_url` or direct `requests`/`aiohttp` with caching & sanitization.

- Implementation Steps
  1. Normalize `@web` query parsing and dispatch to `fetch_url` tool via MCP if available, else use `aiohttp` direct fetch
  2. For `@web weather for X` switch to `https://wttr.in` short format for stable results
  3. Add small LRU cache (in-memory) to prevent duplicate requests during a session

- Tests
  - Unit tests for parsing queries and verifying calls to `fetch_url`; integration tests with mocked responses

- Acceptance Criteria
  - `@web` returns meaningful short answers in CLI for both generic and weather queries

- Estimate: 3–4 hours

---

## 8) Implement @tree and @git (PRIORITY: MEDIUM)

- Goal
  - Provide workspace tree and git-aware context providers.

- Implementation Steps
  1. Implement `@tree` using `git ls-files` if a repo exists or `os.walk` fallback; limit depth and length
  2. Implement `@git` provider to run `git status`, `git log -n 5 --oneline` or `git diff` as requested via arguments
  3. Optional: expose `git` as MCP tool `git_operation` (already exists on server)

- Tests
  - Integration tests in a repo fixture; unit tests for parsing

- Acceptance Criteria
  - `@tree` and `@git` provide concise contextual snippets used for model prompts

- Estimate: 2–4 hours

---

## 9) Add MCP tool handlers on CLI side (PRIORITY: HIGH)

- Goal
  - Implement convenience wrappers and UX for calling common tools from CLI commands (e.g., `/search`, `/exec`, `/analyze`, `/read file`)

- Implementation Steps
  1. Implement `cmd_search` to call `search_files` via `call_mcp_tool` and pretty-print results
  2. Implement `cmd_exec` to call `execute_code` and stream outputs (capture stdout & stderr separately)
  3. Implement `cmd_read` to call `read_code` and page or display content
  4. Ensure these commands work in interactive and direct prompt modes

- Tests
  - Unit tests mocking MCP server responses; integration tests requiring local MCP server

- Acceptance Criteria
  - Commands return real results from MCP tools, not 'coming soon'

- Estimate: 3–4 hours

---

## 10) Enhance file autocomplete (PRIORITY: MEDIUM)

- Goal
  - Provide richer completions for `@file:` including file metadata, re-index on demand, and sustainable performance for large trees.

- Implementation Steps
  1. Improve indexer to run on background task at startup and on demand when `@file:` token is used
  2. Add metadata (size, modified timestamp) to completions via display_meta
  3. Implement a lightweight in-memory file cache with TTL to refresh every X seconds

- Tests
  - Unit: indexer returns expected list; integration: tab completion reveals workspace files

- Acceptance Criteria
  - Autocomplete is quick (<100ms typical) and accurate for top-file types

- Estimate: 2–4 hours

---

## 11) Add/Improve CLI command handlers (PRIORITY: HIGH)

- Goal
  - Make `/exec`, `/search`, `/mode`, `/config show`, `/dashboard` and other commands fully functional.

- Implementation Steps
  1. Add missing `/search` and `/analyze` implementations that use MCP tools
  2. Ensure `/config show` reads the merged config (env + ~/.singularity/config.json)
  3. Implement `/dashboard` startup using `start_dashboard()` (MCP URL passthrough)

- Tests
  - Unit + integration tests for each command

- Acceptance Criteria
  - All major commands perform their intended operations and return success or clear error messages

- Estimate: 3–5 hours

---

## 12) Add integration tests (PRIORITY: HIGH)

- Goal
  - Add pytests that spin up a real MCP server process and mock Ollama streaming to exercise the full roundtrip flows.

- Implementation Steps
  1. Add test fixtures that launch `production_mcp_server.py` on a temp port and yield the URL
  2. Add a test that runs `singularity --startup-check-only` and asserts printed URL
  3. Add tests for `cmd_search`, `cmd_exec`, `@file` provider, and simulated tool call flows
  4. Add small mocked streaming server to emulate Ollama chunks for `generate_streaming`

- Acceptance Criteria
  - CI runs include these tests and they are reliable locally

- Estimate: 6–10 hours

---

## 13) Refactor MCP server code (PRIORITY: MEDIUM)

- Goal
  - Clean duplication, ensure each tool returns a consistent `ToolResult`, and simplify fetch implementations.

- Implementation Steps
  1. Consolidate duplicate methods and ensure consistent `ToolResult` usage
  2. Move helper utilities into small modules for maintainability
  3. Add improved logging & errors for each tool

- Tests
  - Unit tests for each tool method and behavior

- Acceptance Criteria
  - Code is easier to read, fewer duplicates, and consistent JSON outputs

- Estimate: 4–8 hours

---

## 14) Add logging and metrics (PRIORITY: LOW)

- Goal
  - Add structured logging, include execution time for tool calls, and (optional) counters for usage.

- Implementation Steps
  1. Use `logging` module with JSON-friendly formatter or plain but consistent format
  2. Add `execution_time_ms` to MCP responses (already in ref) and log slow calls
  3. Optionally add an internal metrics endpoint to the server (e.g., `/metrics`)

- Tests
  - Unit test that slow tool logs a warning

- Acceptance Criteria
  - Slow operations are visible in logs; `execution_time_ms` is present

- Estimate: 2–4 hours

---

## 15) Update docs and open PR (PRIORITY: LOW)

- Goal
  - Document the changes in `ref/` and top-level README, add upgrade notes for users (omarchy → singularity), and open a PR with summary and checklists.

- Implementation Steps
  1. Draft CHANGELOG entry and README improvements
  2. Add usage examples for `--startup-check-only`, `@file`, `@web`, and `/search`
  3. Open PR and include the testing matrix and what to review

- Tests
  - Manual verification + CI passing

- Acceptance Criteria
  - PR ready with clear description, tests, and CI green

- Estimate: 1–2 hours

---

## Implementation Notes & Conventions
**Testing policy (MANDATORY):** Every task MUST include automated tests (unit and/or integration as appropriate). Tests must be added to `tests/` alongside the implementation and executed locally (and in CI) before the task is marked completed. If the task touches integration boundaries, include a fixture or a mocked server to keep tests deterministic.

- Use `aiohttp` for all async HTTP interactions (MCP + Ollama) instead of `curl` subprocesses.
- Keep all tool results standardized into `ToolResult` objects and return as JSON with `status, data, error, warnings, metadata`.
- For streamed responses, parse line-delimited JSON (the Ollama streaming format) and yield content chunks as they arrive.
- Add feature flags or environment-based toggles to ease testing (e.g., `SINGULARITY_USE_LOCAL_MCP` to avoid attempting to start a system-installed mcp)

---

## Testing & CI
- Add new pytest integration tests to `tests/` and mark them with `@pytest.mark.integration` where appropriate.
- Ensure GitHub Actions has a job that runs integration tests in a matrix and allows a `--skip-integration` option for quick PRs.

---

## Final: Next Step
Implement Task #1 (Start MCP server subprocess) and add unit tests for the URL parsing and failure modes. Once ready, mark the todo as completed and move to Task #2.
