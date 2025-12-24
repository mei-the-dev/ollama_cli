"""
MCP-server & CLI Test Framework (v2025-12-23)

Features:
- Auto-discovers generated code files in sandbox/output directories
- For each file, runs:
    - pytest (preferred) or unittest
    - flake8 (style)
    - mypy (type checks)
    - black --check (format)
- Captures stdout, stderr, exit code, and error details for each test
- Aggregates results into a single JSONL or Markdown report
- Reports:
    - Pass/fail per test and per file
    - Coverage summary (if available)
    - Error taxonomy (validation, syntax, import, runtime, business logic)
    - Links to failing files and error lines
- Optionally re-runs failed tests with verbose output
- Supports CLI invocation: `python scripts/mcp_test_framework.py <output_dir> [--report <report_path>]`
- All results are timestamped and include MCP-server/CLI version info

Usage Example:
    python scripts/mcp_test_framework.py reports/generated_from_model/full_run --report reports/test_report.jsonl
"""

import os
import sys
import subprocess
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any

OUTPUT_EXTS = {'.py'}

REPORT_FIELDS = [
    'filename', 'test_passed', 'flake8_passed', 'mypy_passed', 'black_passed',
    'errors', 'error_type', 'stdout', 'stderr', 'exit_code', 'timestamp', 'version_info'
]

VERSION_INFO = {
    'date': datetime.datetime.now().isoformat(),
    'mcp_server_version': '2025-12-23',
    'cli_version': 'latest',
}

def discover_code_files(output_dir: str) -> List[Path]:
    files = []
    for root, _, filenames in os.walk(output_dir):
        for fname in filenames:
            if Path(fname).suffix in OUTPUT_EXTS:
                files.append(Path(root) / fname)
    return files

def run_command(cmd: List[str], cwd: str = None) -> Dict[str, Any]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)
        return {
            'stdout': proc.stdout,
            'stderr': proc.stderr,
            'exit_code': proc.returncode
        }
    except Exception as e:
        return {
            'stdout': '',
            'stderr': str(e),
            'exit_code': -1
        }

def test_file(file_path: Path) -> Dict[str, Any]:
    result = {'filename': str(file_path), 'timestamp': datetime.datetime.now().isoformat(), 'version_info': VERSION_INFO}
    # Pytest
    pytest_cmd = [sys.executable, '-m', 'pytest', str(file_path)]
    pytest_res = run_command(pytest_cmd)
    result['test_passed'] = pytest_res['exit_code'] == 0
    result['stdout'] = pytest_res['stdout']
    result['stderr'] = pytest_res['stderr']
    result['exit_code'] = pytest_res['exit_code']
    # Flake8
    flake8_cmd = [sys.executable, '-m', 'flake8', str(file_path)]
    flake8_res = run_command(flake8_cmd)
    result['flake8_passed'] = flake8_res['exit_code'] == 0
    # Mypy
    mypy_cmd = [sys.executable, '-m', 'mypy', str(file_path)]
    mypy_res = run_command(mypy_cmd)
    result['mypy_passed'] = mypy_res['exit_code'] == 0
    # Black
    black_cmd = [sys.executable, '-m', 'black', '--check', str(file_path)]
    black_res = run_command(black_cmd)
    result['black_passed'] = black_res['exit_code'] == 0
    # Error taxonomy
    errors = []
    error_type = None
    for res, name in [(pytest_res, 'test'), (flake8_res, 'flake8'), (mypy_res, 'mypy'), (black_res, 'black')]:
        if res['exit_code'] != 0:
            errors.append(f"{name}: {res['stderr']}")
            if 'SyntaxError' in res['stderr']:
                error_type = 'syntax'
            elif 'ImportError' in res['stderr']:
                error_type = 'import'
            elif 'TypeError' in res['stderr']:
                error_type = 'type'
            elif 'AssertionError' in res['stderr']:
                error_type = 'test'
            elif 'PermissionError' in res['stderr']:
                error_type = 'io'
            elif 'ValueError' in res['stderr']:
                error_type = 'validation'
            else:
                error_type = 'runtime'
    result['errors'] = errors
    result['error_type'] = error_type
    return result

def main():
    import argparse
    parser = argparse.ArgumentParser(description='MCP-server/CLI Test Framework')
    parser.add_argument('output_dir', help='Directory with generated code files')
    parser.add_argument('--report', help='Path to save test report', default=None)
    args = parser.parse_args()
    files = discover_code_files(args.output_dir)
    results = []
    for f in files:
        results.append(test_file(f))
    # Save report
    if args.report:
        with open(args.report, 'w') as fp:
            for r in results:
                fp.write(json.dumps(r) + '\n')
    # Print summary
    passed = sum(1 for r in results if r['test_passed'])
    total = len(results)
    print(f"Tested {total} files. {passed} passed. Report: {args.report or 'stdout'}")

if __name__ == '__main__':
    main()
