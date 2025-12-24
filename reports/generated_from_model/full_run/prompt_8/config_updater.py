#!/usr/bin/env python3

import json
import os
from typing import Dict


def update_config(config_path: str, updates: Dict) -> None:
    """
    Update the configuration file with the provided key-value pairs.
    If a key is missing, it will be added. Existing keys will not be overwritten.

    :param config_path: Path to the JSON configuration file.
    :param updates: Dictionary of key-value pairs to update in the config.
    """
    if not os.path.exists(config_path):
        with open(config_path, "w") as f:
            json.dump({}, f)

    with open(config_path, "r+") as f:
        config = json.load(f)
        for key, value in updates.items():
            if key not in config:
                config[key] = value
        f.seek(0)
        json.dump(config, f, indent=4)
        f.truncate()


def test_update_config(tmp_path):
    # Create a temporary configuration file for testing
    config_path = tmp_path / "config.json"
    updates = {"key1": "value1", "key2": "value2"}
    update_config(config_path, updates)
    with open(config_path) as f:
        assert json.load(f) == updates

    # Test adding a new key to an existing config
    additional_updates = {"key3": "value3"}
    update_config(config_path, additional_updates)
    expected_config = {**updates, **additional_updates}
    with open(config_path) as f:
        assert json.load(f) == expected_config


if __name__ == "__main__":
    import doctest

    doctest.testmod()
