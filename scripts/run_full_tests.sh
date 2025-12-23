#!/usr/bin/env bash
# Run full test suite including ref imports and optional live model tests.
# Usage:
#   ./scripts/run_full_tests.sh         # runs tests with ALLOW_REF_IMPORTS=1
#   RUN_LIVE_OLLAMA=1 ./scripts/run_full_tests.sh  # also run live model tests

set -euo pipefail

# Prefer .venv Python if present
VENV_PY=".venv/bin/python"
if [ -x "$VENV_PY" ]; then
  PYTHON="$VENV_PY"
else
  PYTHON="$(command -v python || command -v python3)"
fi

# Default: allow reference imports
export ALLOW_REF_IMPORTS=1

# Simple arg handling: --live enables RUN_LIVE_OLLAMA=1, pass other pytest args through
RUN_LIVE_ENV="0"
PYTEST_ARGS=()
for arg in "$@"; do
  case "$arg" in
    --live)
      RUN_LIVE_ENV="1"
      ;;
    *)
      PYTEST_ARGS+=("$arg")
      ;;
  esac
done

if [ "$RUN_LIVE_ENV" = "1" ]; then
  export RUN_LIVE_OLLAMA=1
  echo "Running full tests with live-model tests enabled (RUN_LIVE_OLLAMA=1)"
else
  echo "Running full tests with reference imports enabled. To enable live tests pass --live or set RUN_LIVE_OLLAMA=1"
fi

# Run pytest using the selected Python executable from venv when available
"$PYTHON" -m pytest "${PYTEST_ARGS[@]}"
