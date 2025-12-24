#!/usr/bin/env python3
"""
Post-process generated code files for style, syntax, and basic validation.
- Runs black, isort, autoflake on all .py files in a target directory.
- Reports any syntax errors or duplicate filenames.
"""
import os
import sys
import subprocess
from pathlib import Path
import ast

def run_tool(cmd):
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=False)

def postprocess_dir(target_dir):
    py_files = list(Path(target_dir).rglob('*.py'))
    # Run autoflake to remove unused imports
    run_tool([sys.executable, '-m', 'autoflake', '--in-place', '--remove-unused-variables', '--remove-all-unused-imports'] + [str(f) for f in py_files])
    # Run isort for import sorting
    run_tool([sys.executable, '-m', 'isort'] + [str(f) for f in py_files])
    # Run black for formatting
    run_tool([sys.executable, '-m', 'black', '--line-length', '120'] + [str(f) for f in py_files])
    # Check for syntax errors and duplicate filenames
    seen = set()
    for f in py_files:
        try:
            with open(f, 'r', encoding='utf-8') as src:
                ast.parse(src.read(), filename=str(f))
        except Exception as e:
            print(f"Syntax error in {f}: {e}")
        name = f.name
        if name in seen:
            print(f"Duplicate filename detected: {name}")
        seen.add(name)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else 'reports/generated_from_model/full_run'
    postprocess_dir(target)
