#!/usr/bin/env python3

import os
import importlib.util

def load_plugins(plugin_dir):
    # List all files in the plugin directory
    plugins = []
    for filename in os.listdir(plugin_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            # Construct full file path
            filepath = os.path.join(plugin_dir, filename)
            # Load the module dynamically
            spec = importlib.util.spec_from_file_location(filename[:-3], filepath)
            plugin_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin_module)
            plugins.append(plugin_module)
    return plugins

def main():
    # Define the directory where plugins are located
    plugin_dir = 'plugins/'
    # Load all plugins from the specified directory
    loaded_plugins = load_plugins(plugin_dir)
    print(f'Loaded {len(loaded_plugins)} plugins.')

if __name__ == '__main__':
    main()
