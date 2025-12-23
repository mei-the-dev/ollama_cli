#!/bin/bash

# Ensure the script stops if any command fails
set -e

# Define the directory for the virtual environment
VENV_DIR="venv"

# Create a Python virtual environment in the specified directory
python3 -m venv $VENV_DIR

# Activate the virtual environment
source $VENV_DIR/bin/activate

# Install packages from requirements.txt
pip install -r requirements.txt

# Deactivate the virtual environment
deactivate