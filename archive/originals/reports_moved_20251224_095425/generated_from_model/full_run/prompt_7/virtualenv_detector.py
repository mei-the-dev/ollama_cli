# This script detects the project's virtual environment path cross-platform (Windows/Linux/Mac)

import os
import sys


def detect_virtualenv_path():
    # Check if running inside a virtual environment
    if hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix):
        return sys.prefix

    # Check for common virtual environment directories
    possible_paths = [
        os.path.join(os.getcwd(), ".venv"),
        os.path.join(os.getcwd(), "venv"),
        os.path.join(os.getcwd(), "env"),
        os.path.join(os.getcwd(), "virtualenv"),
        os.path.join(os.getcwd(), "envs", "default"),
    ]

    for path in possible_paths:
        if os.path.exists(path) and os.path.isdir(path):
            return path

    # If no virtual environment is found, return None
    return None


if __name__ == "__main__":
    venv_path = detect_virtualenv_path()
    if venv_path:
        print(f"Virtual environment detected at: {venv_path}")
    else:
        print("No virtual environment found.")
