#!/usr/bin/env python3


def atomic_write(path, content):
    """
    Writes content to a file atomically by first writing to a temporary file and then renaming it.

    Args:
        path (str): The destination file path where the content should be written.
        content (str): The content to write to the file.
    """
    import os
    import tempfile

    # Create a temporary file in the same directory as the target file
    temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(path))
    try:
        with os.fdopen(temp_fd, "w") as temp_file:
            temp_file.write(content)
        # Atomically replace the original file with the new content
        os.replace(temp_path, path)
    except Exception as e:
        # Clean up the temporary file in case of an error
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e
