#!/usr/bin/env python3
import subprocess
import tempfile


def edit_temp_file():
    # Create a temporary file and write some initial content to it.
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
        temp_path = temp_file.name
        temp_file.write("Initial content of the file.")
        temp_file.flush()

    # Open the default text editor for the user to edit the temporary file.
    subprocess.run(["editor", temp_path])

    # Read the edited content from the temporary file.
    with open(temp_path, "r") as file:
        edited_content = file.read()

    # Remove the temporary file after reading its content.
    import os

    os.remove(temp_path)

    return edited_content
