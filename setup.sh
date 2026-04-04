#!/bin/bash
set -e

echo "=========================================="
echo "    Xcloud - Setup Script      "
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

echo "2. Running Configuration Script..."
echo "Note: new setup options available: --max-global-vms (-g), --dev-whitelist (-w), --max-free-vms, --max-premium-vms, --max-premium-vms-per-code, --max-cpu-threads, --max-ram-gb"
echo "Example: ./setup.sh -g 20 -w \"siteA,siteB\" --max-free-vms 15 --max-premium-vms 5 --max-premium-vms-per-code 1 --max-cpu-threads 4 --max-ram-gb 8 --non-interactive"
python3 setup.py "$@"

echo "3. Building Docker Image..."
docker build -t xcloud .

echo "4. Creating Python Virtual Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo "5. Installing Python Requirements..."
pip install -r requirements.txt

echo "6. Installing Caddy (if missing)..."
if ! command -v caddy &> /dev/null; then
    if command -v apt-get &> /dev/null; then
        echo "Installing Caddy via apt (requires sudo)..."
        sudo apt-get update
        sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo apt-key add -
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
        sudo apt-get update
        sudo apt-get install -y caddy
    elif command -v brew &> /dev/null; then
        echo "Installing Caddy via brew..."
        brew install caddy
    else
        echo "Could not automatically install Caddy. Please install it manually and re-run this script."
    fi
else
    echo "Caddy already installed"
fi

if [ -f "Caddyfile" ]; then
    echo "Copying repository Caddyfile to /etc/caddy/Caddyfile (requires sudo)"
    sudo cp Caddyfile /etc/caddy/Caddyfile || echo "Warning: failed to copy Caddyfile to /etc/caddy/Caddyfile"
    echo "Reloading Caddy service (if available)"
    sudo systemctl restart caddy || sudo service caddy restart || echo "Please restart Caddy manually"
fi

echo "=========================================="
echo " Setup Complete! Starting API Server...   "
echo " (Press CTRL+C to stop)                   "
echo "=========================================="

# Start the uvicorn API server on port 8000
# If `SSL_CERTFILE` and `SSL_KEYFILE` are set in the environment, run with TLS.
if [ -n "${SSL_CERTFILE:-}" ] && [ -n "${SSL_KEYFILE:-}" ]; then
    echo "Starting Uvicorn with TLS (SSL_CERTFILE and SSL_KEYFILE detected)"
    python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --ssl-certfile "$SSL_CERTFILE" --ssl-keyfile "$SSL_KEYFILE"
else
    python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
fi
