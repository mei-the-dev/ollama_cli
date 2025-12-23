#!/usr/bin/env python3
import os
from urllib.parse import unquote

def normalize_path(user_input):
    # Decode URL-encoded characters to handle special characters in paths
    decoded_input = unquote(user_input)
    
    # Use os.path.abspath to get the absolute path and resolve any relative components
    abs_path = os.path.abspath(decoded_input)
    
    # Use os.path.commonprefix to ensure the path is within a safe directory (e.g., '/safe/directory')
    safe_directory = '/safe/directory'
    common_prefix = os.path.commonprefix([abs_path, safe_directory])
    
    if common_prefix != safe_directory:
        raise ValueError('Path traversal detected or path outside of allowed directory.')
    
    return abs_path

# Example usage
if __name__ == '__main__':
    user_input = input('Enter the file path: ')
    try:
        normalized_path = normalize_path(user_input)
        print(f'Normalized Path: {normalized_path}')
    except ValueError as e:
        print(e)