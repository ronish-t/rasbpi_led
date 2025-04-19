#!/bin/bash

# LED Controller Startup Script
set -e

# Activate Python virtual environment if exists
if [ -d "venv" ]; then
    echo "Activating virtual environment"
    source venv/bin/activate
fi

# Ensure required permissions
echo "Setting execute permissions"
chmod +x controller.py

# Start the controller
echo "Starting LED controller..."
sudo python3 controller.py

# Show process status
echo "LED controller running with PID: $!"