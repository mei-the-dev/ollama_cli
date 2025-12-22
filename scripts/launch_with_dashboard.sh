#!/usr/bin/env bash
# Launch helper for local dev: starts Ollama (optional), the MCP server, the CLI, and the dashboard
# - Uses tmux if available to open each service in its own pane
# - Falls back to backgrounded processes with logs in ./logs/

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$REPO_ROOT/logs"
mkdir -p "$LOG_DIR"

OMARCHY_SESSION="omarchy"
SKIP_OLLAMA=${SKIP_OLLAMA:-0}
OMARCHY_MODEL=${OMARCHY_MODEL:-"qwen2.5-coder:14b-instruct-q4_K_M"}

wait_for_http() {
  local url="$1"
  local tries=${2:-30}
  local i
  for i in $(seq 1 "$tries"); do
    if curl -sSf "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

wait_for_mcp() {
  local url="http://localhost:8080/mcp"
  local tries=${1:-30}
  local i
  for i in $(seq 1 "$tries"); do
    if curl -sSf -X POST -H 'Content-Type: application/json' -d '{"method":"tools/list","params":{}}' "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

start_tmux_session() {
  # Create session with named windows for each service
  tmux new-session -d -s "$OMARCHY_SESSION" -n "ollama" || true

  if [[ "$SKIP_OLLAMA" != "1" ]]; then
    tmux send-keys -t "$OMARCHY_SESSION:ollama" "echo 'Starting Ollama serve...' && ollama serve 2>&1 | tee -a \"$LOG_DIR/ollama.log\"" C-m
  else
    tmux send-keys -t "$OMARCHY_SESSION:ollama" "echo 'SKIP_OLLAMA=1 set — not starting ollama'" C-m
  fi

  tmux new-window -t "$OMARCHY_SESSION" -n "mcp"
  tmux send-keys -t "$OMARCHY_SESSION:mcp" "echo 'Starting MCP server...' && python3 $REPO_ROOT/mcp_server.py 2>&1 | tee -a \"$LOG_DIR/mcp_server.log\"" C-m

  # wait until MCP is ready, then attach CLI and dashboard windows
  tmux new-window -t "$OMARCHY_SESSION" -n "wait" 
  tmux send-keys -t "$OMARCHY_SESSION:wait" "echo 'Waiting for services to be ready...' && \"$0\" --wait-ready" C-m

  # CLI and dashboard windows will be created by the wait-ready branch
  tmux attach-session -t "$OMARCHY_SESSION"
}

start_background_processes() {
  if [[ "$SKIP_OLLAMA" != "1" ]]; then
    (echo "Starting Ollama in background..."; ollama serve >>"$LOG_DIR/ollama.log" 2>&1) &
    echo "ollama started (background), log: $LOG_DIR/ollama.log"
  else
    echo "SKIP_OLLAMA=1 set — not starting ollama"
  fi

  (echo "Starting MCP server in background..."; python3 "$REPO_ROOT/mcp_server.py" >>"$LOG_DIR/mcp_server.log" 2>&1) &
  echo "mcp_server started (background), log: $LOG_DIR/mcp_server.log"

  echo "Waiting for Ollama and MCP to become ready (30s timeout)..."
  if [[ "$SKIP_OLLAMA" != "1" ]]; then
    if wait_for_http "http://localhost:11434/api/tags" 30; then
      echo "Ollama ready"
    else
      echo "Warning: Ollama did not become ready in time"
    fi
  fi

  if wait_for_mcp 30; then
    echo "MCP ready"
  else
    echo "Warning: MCP did not become ready in time"
  fi

  echo "Starting CLI (omarchy) and dashboard in background logs..."
  (echo "Starting CLI..."; (command -v singularity >/dev/null 2>&1 && exec singularity) || python3 "$REPO_ROOT/omarchy_cli.py") >>"$LOG_DIR/cli.log" 2>&1 &
  (echo "Starting Dashboard..."; python3 "$REPO_ROOT/ref/singularity_dashboard.py") >>"$LOG_DIR/dashboard.log" 2>&1 &
  echo "CLI log: $LOG_DIR/cli.log"
  echo "Dashboard log: $LOG_DIR/dashboard.log"
}

if [[ "${1:-}" == "--wait-ready" ]]; then
  # Called from tmux wait window — wait for services and then create CLI & Dashboard windows
  if [[ "$SKIP_OLLAMA" != "1" ]]; then
    if wait_for_http "http://localhost:11434/api/tags" 30; then
      tmux new-window -t "$OMARCHY_SESSION" -n "cli"
      tmux send-keys -t "$SINGULARITY_SESSION:cli" "echo 'Starting CLI...' && (command -v singularity >/dev/null 2>&1 && exec singularity) || python3 $REPO_ROOT/omarchy_cli.py" C-m
    else
      tmux new-window -t "$OMARCHY_SESSION" -n "cli"
      tmux send-keys -t "$OMARCHY_SESSION:cli" "echo 'Ollama not ready — you can start the CLI manually'" C-m
    fi
  else
    tmux new-window -t "$OMARCHY_SESSION" -n "cli"
    tmux send-keys -t "$OMARCHY_SESSION:cli" "echo 'SKIP_OLLAMA set — starting CLI' && (command -v omarchy >/dev/null 2>&1 && exec omarchy) || python3 $REPO_ROOT/omarchy_cli.py" C-m
  fi

  if wait_for_mcp 30; then
    tmux new-window -t "$OMARCHY_SESSION" -n "dashboard"
    tmux send-keys -t "$OMARCHY_SESSION:dashboard" "echo 'Starting Dashboard...' && python3 $REPO_ROOT/ref/omarchy_dashboard.py" C-m
  else
    tmux new-window -t "$OMARCHY_SESSION" -n "dashboard"
    tmux send-keys -t "$OMARCHY_SESSION:dashboard" "echo 'MCP not ready — start dashboard manually after MCP is up'" C-m
  fi

  exit 0
fi

# Main entry
if command -v tmux >/dev/null 2>&1; then
  echo "tmux found — launching services in tmux session '$OMARCHY_SESSION'"
  start_tmux_session
else
  echo "tmux not found — falling back to background processes with logs"
  start_background_processes
fi
