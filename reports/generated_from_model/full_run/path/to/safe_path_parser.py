# safe_path_parser.py
import os
from urllib.parse import unquote

def sanitize_filename(filename):
    # Remove any characters that are not alphanumeric or underscores
    sanitized = ''.join(c for c in filename if c.isalnum() or c == '_')
    return sanitized

def normalize_path(base_dir, user_input):
    # Unquote URL-encoded characters
    decoded_input = unquote(user_input)
    
    # Join the base directory with the user input to create a full path
    full_path = os.path.join(base_dir, decoded_input)
    
    # Resolve any symbolic links and relative paths
    normalized_path = os.path.abspath(full_path)
    
    # Ensure the path is within the base directory
    if not normalized_path.startswith(os.path.abspath(base_dir)):
        raise ValueError('Path traversal detected')
    
    return normalized_path

if __name__ == '__main__':
    base_directory = '/safe/base/directory'
    user_input = input('Enter the file path: ')
    try:
        safe_path = normalize_path(base_directory, user_input)
        print(f'Safe and normalized path: {safe_path}')
    except ValueError as e:
        print(e)