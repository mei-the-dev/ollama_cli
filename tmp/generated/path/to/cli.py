#!/usr/bin/env python3
import argparse
import json
import yaml
import os

def load_config(config_path):
    """
    Load configuration from a JSON or YAML file.
    :param config_path: Path to the configuration file.
    :return: Configuration dictionary.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f'Configuration file {config_path} does not exist.')

    _, ext = os.path.splitext(config_path)
    try:
        with open(config_path, 'r') as config_file:
            if ext.lower() == '.json':
                return json.load(config_file)
            elif ext.lower() in ['.yaml', '.yml']:
                return yaml.safe_load(config_file)
            else:
                raise ValueError(f'Unsupported configuration file format: {ext}')
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise ValueError(f'Failed to parse configuration file {config_path}: {e}') from e

def main():
    parser = argparse.ArgumentParser(description='CLI tool with config support.')
    parser.add_argument('--config', required=True, help='Path to the configuration file (JSON or YAML).')
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        print(f'Configuration loaded successfully: {config}')
    except Exception as e:
        print(f'Error: {e}')
        exit(1)

if __name__ == '__main__':
    main()