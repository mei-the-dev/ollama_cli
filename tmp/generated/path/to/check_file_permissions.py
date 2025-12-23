#!/usr/bin/env python3
import os
import stat

def check_sensitive_files(directory):
    # List of sensitive file extensions to check
    sensitive_extensions = ['.env', '.conf', '.ini', '.json']
    
    # Walk through the directory
    for root, dirs, files in os.walk(directory):
        for file in files:
            # Check if the file has a sensitive extension
            if any(file.endswith(ext) for ext in sensitive_extensions):
                filepath = os.path.join(root, file)
                # Get the file permissions
                file_permissions = oct(os.stat(filepath).st_mode)[-3:]
                
                # Check if the file is world-readable
                if '6' in file_permissions or '7' in file_permissions:
                    print(f"Warning: {filepath} is world-readable with permissions {file_permissions}")

if __name__ == '__main__':
    directory_to_check = '/path/to/your/directory'
    check_sensitive_files(directory_to_check)
