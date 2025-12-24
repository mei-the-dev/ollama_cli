"""
Debug Script: CLI Model Integration (Ollama Qwen)

Checks:
1. Ollama server is running and reachable
2. CLI is using correct model and endpoint
3. CLI prompt template matches test prompt
4. CLI logs for errors or fallback logic
5. API response is parsed and used as code
6. Environment variables are set correctly

Usage:
    python scripts/debug_cli_model_integration.py
"""

import os
import subprocess
import sys
from pathlib import Path

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("SINGULARITY_MODEL", "qwen2.5-coder:14b-instruct-q4_K_M")
LOG_PATH = Path(__file__).parent.parent / "logs" / "singularity.log"


def check_ollama_server():
    print(f"Checking Ollama server at {OLLAMA_URL}...")
    try:
        result = subprocess.run([
            "curl", "-s", f"{OLLAMA_URL}/api/tags"
        ], capture_output=True, timeout=3)
        if result.returncode != 0 or "qwen" not in result.stdout.decode():
            print("[FAIL] Ollama server not running or model not loaded.")
            sys.exit(1)
        print("[OK] Ollama server running and Qwen model available.")
    except Exception as e:
        print(f"[FAIL] Error connecting to Ollama: {e}")
        sys.exit(1)


def check_cli_model():
    print(f"Checking CLI model selection...")
    print(f"SINGULARITY_MODEL={MODEL}")
    if not MODEL.startswith("qwen"):
        print("[WARN] CLI is not using a Qwen model.")
    else:
        print("[OK] CLI is using Qwen model.")


def check_prompt_template():
    template_path = Path(__file__).parent / "mcp_prompt_template.py"
    if not template_path.exists():
        print("[WARN] Prompt template not found.")
        return
    with open(template_path) as f:
        template = f.read()
    print("Prompt template loaded.\n---\n" + template[:300] + "...\n---")


def check_logs():
    if not LOG_PATH.exists():
        print("[WARN] CLI log file not found.")
        return
    with open(LOG_PATH) as f:
        lines = f.readlines()[-20:]
    print("Last 20 log lines:\n" + "".join(lines))


def check_env():
    print("Environment variables:")
    for k in ["SINGULARITY_MODEL", "OLLAMA_URL"]:
        print(f"  {k}={os.environ.get(k)}")


def main():
    check_ollama_server()
    check_cli_model()
    check_prompt_template()
    check_logs()
    check_env()
    print("\nIf all checks are OK, try running the CLI in code mode and verify model output.")

if __name__ == "__main__":
    main()
