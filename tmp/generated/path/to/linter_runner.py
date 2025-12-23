#!/usr/bin/env python3
import subprocess
import json

def run_linters(file_path):
    # Run flake8 linter and capture its output
    flake8_result = subprocess.run(['flake8', file_path], capture_output=True, text=True)
    # Run black formatter and capture its output
    black_result = subprocess.run(['black', '--check', file_path], capture_output=True, text=True)

    # Parse flake8 output into structured JSON
    flake8_issues = []
    for line in flake8_result.stdout.splitlines():
        parts = line.split(':')
        if len(parts) >= 4:
            issue = {
                'line': int(parts[1]),
                'column': int(parts[2]),
                'code': parts[-2],
                'message': ': '.join(parts[3:])
            }
            flake8_issues.append(issue)

    # Parse black output into structured JSON
    black_issues = []
    if 'reformatted' in black_result.stdout:
        black_issues.append({
            'message': 'File needs formatting'
        })

    # Combine results into a single JSON object
    result = {
        'flake8': flake8_issues,
        'black': black_issues
    }

    return json.dumps(result, indent=4)

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print('Usage: python linter_runner.py <file_path>')
        sys.exit(1)
    file_path = sys.argv[1]
    output = run_linters(file_path)
    print(output)