#!/usr/bin/env python3
import subprocess


def get_git_branch():
    # Get the current git branch name
    return subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode("utf-8").strip()


def get_last_commit():
    # Get the last commit hash and message
    return subprocess.check_output(["git", "log", "-1", "--pretty=format:%h - %s"]).decode("utf-8").strip()


def get_uncommitted_files():
    # List uncommitted files
    try:
        return subprocess.check_output(["git", "status", "--porcelain"]).decode("utf-8").strip()
    except subprocess.CalledProcessError:
        return "No uncommitted changes"


def generate_report():
    branch = get_git_branch()
    last_commit = get_last_commit()
    uncommitted_files = get_uncommitted_files()

    report = f"Current Branch: {branch}\nLast Commit: {last_commit}\nUncommitted Files:\n{uncommitted_files}"
    return report


if __name__ == "__main__":
    print(generate_report())
