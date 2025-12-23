#!/usr/bin/env python3
import subprocess

def get_git_branch():
    """
    Returns the current git branch name.
    """
    try:
        result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], check=True, text=True, capture_output=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f'Error getting git branch: {e.stderr}')
        return None

def get_last_commit():
    """
    Returns the last commit hash and message.
    """
    try:
        result = subprocess.run(['git', 'log', '-1', '--pretty=format:%h %s'], check=True, text=True, capture_output=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f'Error getting last commit: {e.stderr}')
        return None

def get_uncommitted_files():
    """
    Returns a list of uncommitted files.
    """
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], check=True, text=True, capture_output=True)
        uncommitted_files = [line.strip() for line in result.stdout.splitlines() if line]
        return uncommitted_files
    except subprocess.CalledProcessError as e:
        print(f'Error getting uncommitted files: {e.stderr}')
        return None

def generate_report():
    """
    Generates a report with the current git branch, last commit, and uncommitted files.
    """
    branch = get_git_branch()
    last_commit = get_last_commit()
    uncommitted_files = get_uncommitted_files()

    print('Git Debug Report:')
    if branch:
        print(f'Current Branch: {branch}')
    else:
        print('Could not determine the current git branch.')

    if last_commit:
        print(f'Last Commit: {last_commit}')
    else:
        print('Could not retrieve the last commit information.')

    if uncommitted_files:
        print('Uncommitted Files:')
        for file in uncommitted_files:
            print(file)
    else:
        print('No uncommitted files found.')

if __name__ == '__main__':
    generate_report()
