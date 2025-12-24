#!/usr/bin/env bash
# Lightweight development shim to run the local Singularity CLI
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
exec "${SCRIPT_DIR}/.venv/bin/python" "${SCRIPT_DIR}/singularity_cli.py" "$@"
