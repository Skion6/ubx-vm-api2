#!/bin/bash
set -e

echo "=========================================="
echo "    VM API - Setup Script      "
echo "=========================================="

echo "1. Checking Dependencies..."
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed or not in PATH."
    echo "Please install Docker and try again."
    exit 1
fi
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 is not installed or not in PATH."
    exit 1
fi

echo "2. Building Docker Image..."
# Build the Ubuntu KasmVNC image locally
docker build -t gamingoncodespaces .

echo "3. Creating Python Virtual Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo "4. Installing Python Requirements..."
pip install -r requirements.txt

echo "=========================================="
echo " Setup Complete! Starting API Server...   "
echo " (Press CTRL+C to stop)                   "
echo "=========================================="

# Start the uvicorn API server on port 8000
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
