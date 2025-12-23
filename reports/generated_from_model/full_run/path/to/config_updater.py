#!/usr/bin/env python3

import json
import os

def update_config(config_path, updates):
    """
    Update a JSON config file with the provided key-value pairs.
    If a key is missing, it will be added. If a key exists, its value will be updated.
    
    :param config_path: Path to the JSON configuration file.
    :param updates: Dictionary of key-value pairs to update in the config file.
    """
    if not os.path.exists(config_path):
        with open(config_path, 'w') as f:
            json.dump({}, f)

    with open(config_path, 'r+') as f:
        config = json.load(f)
        config.update(updates)
        f.seek(0)
        json.dump(config, f, indent=4)
        f.truncate()

def test_update_config():
    # Create a temporary file for testing
    temp_file = '/tmp/config_test.json'
    try:
        # Test case 1: Update an empty config file
        update_config(temp_file, {'key1': 'value1'})
        with open(temp_file, 'r') as f:
            assert json.load(f) == {'key1': 'value1'}

        # Test case 2: Add a new key to an existing config file
        update_config(temp_file, {'key2': 'value2'})
        with open(temp_file, 'r') as f:
            assert json.load(f) == {'key1': 'value1', 'key2': 'value2'}

        # Test case 3: Update an existing key in the config file
        update_config(temp_file, {'key1': 'new_value1'})
        with open(temp_file, 'r') as f:
            assert json.load(f) == {'key1': 'new_value1', 'key2': 'value2'}
    finally:
        os.remove(temp_file)

if __name__ == '__main__':
    test_update_config()
