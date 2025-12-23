#!/usr/bin/env python3
import os
import sys

def detect_virtualenv_path():
    """
    Detects the path to the virtual environment being used in a cross-platform manner.
    Returns the path if found, otherwise returns None.
    """
    # Check for VIRTUAL_ENV environment variable which is set by activate script
    if 'VIRTUAL_ENV' in os.environ:
        return os.environ['VIRTUAL_ENV']
    
    # For Windows, check for Scripts/activate.bat
    if sys.platform == 'win32':
        base_path = os.path.dirname(sys.executable)
        activate_script = os.path.join(base_path, 'Scripts', 'activate.bat')
        if os.path.exists(activate_script):
            return base_path
    
    # For Unix-like systems (Linux/Mac), check for bin/activate script
    else:
        base_path = os.path.dirname(sys.executable)
        activate_script = os.path.join(base_path, 'bin', 'activate')
        if os.path.exists(activate_script):
            return base_path
    
    # If no virtual environment is detected, return None
    return None

if __name__ == '__main__':
    env_path = detect_virtualenv_path()
    if env_path:
        print(f'Virtual environment path: {env_path}')
    else:
        print('No virtual environment detected.')