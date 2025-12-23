#!/usr/bin/env python3
import os
import sys

def check_world_readable(file_path):
    # Get the file permissions using stat
    st = os.stat(file_path)
    # Check if the file is world-readable
    return bool(st.st_mode & 0o4)

def warn_if_sensitive_files_are_world_readable(directory, sensitive_extensions=['.env', '.conf', '.ini']):
    # Walk through all files in the directory and its subdirectories
    for root, dirs, files in os.walk(directory):
        for file in files:
            # Check if the file has a sensitive extension
            if any(file.endswith(ext) for ext in sensitive_extensions):
                file_path = os.path.join(root, file)
                # Check if the file is world-readable
                if check_world_readable(file_path):
                    print(f'Warning: Sensitive file {file_path} is world-readable.')

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python check_file_permissions.py <directory>')
        sys.exit(1)
    directory = sys.argv[1]
    warn_if_sensitive_files_are_world_readable(directory)