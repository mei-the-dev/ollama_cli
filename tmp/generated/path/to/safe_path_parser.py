# safe_path_parser.py
import os
from urllib.parse import unquote

def normalize_path(user_input):
    # Decode URL-encoded characters to handle special cases like %2F for /
    decoded_input = unquote(user_input)
    
    # Use os.path.abspath to get the absolute path and resolve any relative components
    absolute_path = os.path.abspath(decoded_input)
    
    # Get the root directory of the current working directory
    root_dir = os.path.abspath(os.sep)
    
    # Ensure the absolute path is within the root directory to prevent traversal
    if not absolute_path.startswith(root_dir):
        raise ValueError('Invalid path: Path traversal detected')
    
    return absolute_path

# Example usage:
if __name__ == '__main__':
    user_input = input('Enter a file path: ')
    try:
        safe_path = normalize_path(user_input)
        print(f'Safe normalized path: {safe_path}')
    except ValueError as e:
        print(e)