#!/usr/bin/env python3
import os
from urllib.parse import unquote


def normalize_path(user_input):
    # Decode URL-encoded characters to handle special cases like %2F for /
    decoded_input = unquote(user_input)

    # Use os.path.abspath to get the absolute path and resolve any relative components
    abs_path = os.path.abspath(decoded_input)

    # Get the root directory of the current working directory
    root_dir = os.path.abspath(os.sep)

    # Ensure the normalized path is within the root directory to prevent traversal
    if not abs_path.startswith(root_dir):
        raise ValueError("Path traversal detected")

    return abs_path


if __name__ == "__main__":
    user_input = input("Enter a file path: ")
    try:
        normalized_path = normalize_path(user_input)
        print(f"Normalized Path: {normalized_path}")
    except ValueError as e:
        print(e)
