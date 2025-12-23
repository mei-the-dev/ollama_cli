#!/usr/bin/env python3

def atomic_write(path, content):
    """
    Writes content to a file atomically by first writing to a temporary file and then renaming it.
    This avoids the risk of leaving partial files in case of an interruption during write.

    Args:
        path (str): The target file path where the content should be written.
        content (str): The content to write to the file.
    """
    import os
    import tempfile
    import shutil

    # Create a temporary file in the same directory as the target file
    temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(path))
    try:
        with os.fdopen(temp_fd, 'w') as f:
            f.write(content)
        # Atomically replace the target file with the temporary file
        shutil.move(temp_path, path)
    except Exception as e:
        # Clean up the temporary file in case of an error
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e
