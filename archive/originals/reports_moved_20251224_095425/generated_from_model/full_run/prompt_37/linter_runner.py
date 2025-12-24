#!/usr/bin/env python3
import json
import subprocess


def run_linters(file_path):
    # Run flake8 linter and capture its output
    flake8_result = subprocess.run(["flake8", file_path], capture_output=True, text=True)
    flake8_issues = parse_flake8_output(flake8_result.stdout)

    # Run black formatter and capture its output
    black_result = subprocess.run(["black", "--check", file_path], capture_output=True, text=True)
    black_issues = parse_black_output(black_result.stderr)

    # Combine results into a single JSON object
    results = {"flake8": flake8_issues, "black": black_issues}
    return json.dumps(results, indent=4)


def parse_flake8_output(output):
    issues = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 3:
            issue = {
                "file": parts[0],
                "line": int(parts[1]),
                "column": int(parts[2].split(":")[0]),
                "code": parts[2].split(":")[1],
                "message": " ".join(parts[3:]),
            }
            issues.append(issue)
    return issues


def parse_black_output(output):
    issues = []
    for line in output.splitlines():
        if "would reformat" in line:
            parts = line.split()
            issue = {"file": parts[1], "message": "File would be reformatted"}
            issues.append(issue)
    return issues


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python linter_runner.py <file_path>")
        sys.exit(1)
    file_path = sys.argv[1]
    results = run_linters(file_path)
    print(results)
