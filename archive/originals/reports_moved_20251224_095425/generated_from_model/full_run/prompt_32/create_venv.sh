#!/bin/bash

# Check if virtualenv is installed
if ! command -v virtualenv &> /dev/null; then
    echo "virtualenv could not be found, please install it first."
    exit 1
fi

# Create a new virtual environment in the current directory
virtualenv venv

# Activate the virtual environment
source venv/bin/activate

# Install packages from requirements.txt
pip install -r requirements.txt

# Deactivate the virtual environment
deactivate