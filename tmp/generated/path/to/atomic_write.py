#!/usr/bin/env python3

def atomic_write(path, content):
    """
    Writes content to a file at the specified path in an atomic manner.
    This function writes the content to a temporary file and then renames it to the target path,
    ensuring that the operation is atomic and avoids partial files in case of interruption.

    :param path: str, The path where the content should be written.
    :param content: str or bytes, The content to write to the file.
    """
    import os
    import tempfile

    # Create a temporary file in the same directory as the target path
    temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(path))
    try:
        with os.fdopen(temp_fd, 'w') as f:
            f.write(content)
        # Rename the temporary file to the target path atomically
        os.rename(temp_path, path)
    except Exception as e:
        # Clean up the temporary file if an error occurs
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise e
