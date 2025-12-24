#!/usr/bin/env python3


def check_sensitive_files(file_paths):
    """
    Check if the given files are world-readable.

    Args:
        file_paths (list): List of file paths to check.

    Returns:
        list: List of files that are world-readable.
    """
    import os

    world_readable_files = []

    for file_path in file_paths:
        # Check if the file exists
        if not os.path.exists(file_path):
            print(f"Warning: File {file_path} does not exist.")
            continue

        # Get the file permissions
        file_permissions = oct(os.stat(file_path).st_mode)[
            -3:
        ]  # Last three digits represent user, group, others permissions

        # Check if the file is world-readable (others have read permission)
        if file_permissions[2] in ["7", "6", "5", "4"]:
            world_readable_files.append(file_path)
            print(f"Warning: File {file_path} is world-readable with permissions {file_permissions}.")

    return world_readable_files


if __name__ == "__main__":
    # Example usage
    sensitive_files = ["/etc/passwd", "/etc/shadow"]  # Add paths to sensitive files here
    check_sensitive_files(sensitive_files)
