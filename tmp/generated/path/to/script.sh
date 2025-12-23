#!/bin/bash

# This script creates a Python virtual environment and installs packages from requirements.txt.

# Define the directory for the virtual environment
VENV_DIR="venv"

# Create the virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv $VENV_DIR
fi

# Activate the virtual environment
source $VENV_DIR/bin/activate

# Install packages from requirements.txt
pip install -r requirements.txt

# Deactivate the virtual environment
deactivate
