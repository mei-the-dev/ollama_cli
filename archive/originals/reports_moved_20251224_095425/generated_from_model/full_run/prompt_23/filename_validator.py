# filename_validator.py


def validate_and_sanitize_filename(filename):
    # Import necessary libraries
    import os
    import re

    # Define a regular expression pattern for valid filenames
    valid_chars = r"[^a-zA-Z0-9._-]"

    # Check if the filename is empty or contains invalid characters
    if not filename or re.search(valid_chars, filename):
        raise ValueError("Invalid filename. Please use only alphanumeric characters and ._-.")

    # Prevent directory traversal by ensuring no path separators are present
    if os.path.sep in filename:
        raise ValueError(f"Filename cannot contain path separators ({os.path.sep}).")

    return filename
