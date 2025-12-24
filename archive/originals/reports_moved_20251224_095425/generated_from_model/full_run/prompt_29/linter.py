#!/usr/bin/env python3


def check_todo_fixme(repo_path):
    import os

    report = {}
    for root, _, files in os.walk(repo_path):
        for file in files:
            if (
                not file.endswith(".py")
                and not file.endswith(".js")
                and not file.endswith(".java")
                and not file.endswith(".c")
                and not file.endswith(".cpp")
            ):
                continue
            file_path = os.path.join(root, file)
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line_number, line in enumerate(lines, start=1):
                if "TODO" in line or "FIXME" in line:
                    if file_path not in report:
                        report[file_path] = []
                    report[file_path].append((line_number, line.strip()))
    return report


if __name__ == "__main__":
    import sys

    repo_path = sys.argv[1]
    result = check_todo_fixme(repo_path)
    for file_path, issues in result.items():
        print(f"Issues found in {file_path}:")
        for line_number, issue in issues:
            print(f"Line {line_number}: {issue}")
