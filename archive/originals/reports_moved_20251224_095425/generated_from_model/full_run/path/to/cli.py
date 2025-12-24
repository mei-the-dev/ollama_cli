#!/usr/bin/env python3
import argparse
import json
import os

import yaml


def load_config(config_path):
    """
    Load configuration from a JSON or YAML file.

    Args:
        config_path (str): Path to the configuration file.

    Returns:
        dict: Configuration data.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValueError: If the configuration file is neither JSON nor YAML.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file {config_path} not found.")

    with open(config_path, "r") as config_file:
        if config_path.endswith(".json"):
            return json.load(config_file)
        elif config_path.endswith((".yaml", ".yml")):
            return yaml.safe_load(config_file)
        else:
            raise ValueError("Configuration file must be JSON or YAML.")


def main():
    parser = argparse.ArgumentParser(description="CLI tool with configuration support.")
    parser.add_argument("--config", required=True, help="Path to the configuration file.")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        print("Configuration loaded successfully:", config)
    except Exception as e:
        print(f"Error loading configuration: {e}")


if __name__ == "__main__":
    main()
