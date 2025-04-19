#!/bin/bash
set -e

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Install requirements
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Fix permissions for hardware access
echo "Setting GPIO permissions..."
sudo usermod -a -G gpio $USER || true

# Run controller with virtual environment Python
echo "Starting controller..."
sudo -E venv/bin/python3 controller.py