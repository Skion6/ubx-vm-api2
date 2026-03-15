#!/bin/bash
set -e

echo "Setting up VM Management API..."

# Ensure we're in the vm-api directory
cd "$(dirname "$0")"

# Optional: Create a virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing requirements..."
pip install -r requirements.txt

echo "Setup complete! To run the API, execute:"
echo "source venv/bin/activate"
echo "uvicorn main:app --host 0.0.0.0 --port 8000"

# Note: In production you might want to run this as a service using systemd or docker
