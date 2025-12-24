#!/usr/bin/env python3
import os
import subprocess
import tempfile


def edit_temp_file():
    # Create a temporary file and get its path
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
        temp_path = temp_file.name
        temp_file.close()

    try:
        # Open the default text editor for the user to edit the file
        subprocess.run(["editor", temp_path], check=True)

        # Read the content of the edited file
        with open(temp_path, "r") as file:
            content = file.read()

    finally:
        # Clean up by removing the temporary file
        os.remove(temp_path)

    return content
