#!/usr/bin/env python3
import os
import sys


def detect_virtualenv_path():
    # Check if the script is running inside a virtual environment
    if hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix):
        return sys.prefix
    else:
        return None


if __name__ == "__main__":
    # Get the virtualenv path
    venv_path = detect_virtualenv_path()
    if venv_path:
        print(f"Virtual environment detected at: {venv_path}")
    else:
        print("No virtual environment detected.")
