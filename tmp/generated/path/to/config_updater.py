#!/usr/bin/env python3
import json
import os

def update_config(config_path, updates):
    """
    Update a JSON config file with the provided key-value pairs.
    If a key is missing, it will be added. Existing keys will not be overwritten unless specified.
    
    :param config_path: Path to the JSON configuration file.
    :param updates: Dictionary of key-value pairs to update in the config file.
    """
    if not os.path.exists(config_path):
        config = {}
    else:
        with open(config_path, 'r') as f:
            config = json.load(f)

    for key, value in updates.items():
        if key not in config:
            config[key] = value

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)

def test_update_config():
    # Create a temporary file for testing
    temp_file = '/tmp/test_config.json'
    try:
        # Initial config
        initial_config = {
            'key1': 'value1',
            'key2': 'value2'
        }
        with open(temp_file, 'w') as f:
            json.dump(initial_config, f)

        # Updates to apply
        updates = {
            'key2': 'new_value2',  # Existing key, should not change
            'key3': 'value3'       # New key, should be added
        }

        # Apply updates
        update_config(temp_file, updates)

        # Check the updated config
        with open(temp_file, 'r') as f:
            updated_config = json.load(f)

        assert updated_config == {
            'key1': 'value1',
            'key2': 'value2',  # Existing key remains unchanged
            'key3': 'value3'    # New key is added
        }

    finally:
        os.remove(temp_file)

if __name__ == '__main__':
    test_update_config()
