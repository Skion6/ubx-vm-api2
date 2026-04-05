# Installation Guide

Follow these steps to set up Xcloud on your server.

## Prerequisites

- **Python 3.10+** (Recommend 3.11 for performance)
- **Docker Engine** (or Docker Desktop on Windows)
- **Git** (to clone the repo)

## Step-by-Step Setup

### 1. Clone & Enter Directory

```bash
git clone https://gitlab.com/lorem-group-us/ubx-vm-api.git
cd ubx-vm-api
```

### 2. Run Setup Script

**Interactive Mode (default):**

**Windows:**
Double-click `setup.bat` or run:

```cmd
setup.bat
```

**Linux/Mac:**

```bash
chmod +x /setup.sh
./setup.sh
```

**Non-interactive Mode (for nohup/automation):**

All command-line arguments are passed through to setup.py:

```bash

# Using defaults
./setup.sh --non-interactive

# With specific values
./setup.sh -a mypass -m 50 -i 10 -s 120 -p "CODE1,CODE2"

# Windows
setup.bat -a mypass -m 50 -i 10 -s 120 -p "CODE1,CODE2"
```

**Command-line options:**

- `-a, --admin-password`: API Admin Password
- `-m, --max-vms`: Max VMs per Developer
- `-i, --max-inactivity`: Max Inactivity Time (minutes)
- `-s, --max-session`: Max Session Lifetime (minutes)
- `-p, --premium-code`: Premium Code(s), comma-separated
- `-g, --max-global-vms`: Global max concurrent VMs (hard limit)
- `-w, --dev-whitelist`: Comma-separated developer IDs to whitelist
- `--max-free-vms`: Maximum concurrent free VMs
- `--max-premium-vms`: Maximum concurrent premium VMs (0 = unlimited)
- `--max-cpu-threads`: Maximum CPU threads (cores) per VM instance
- `--max-ram-gb`: Maximum RAM (GB) per VM instance
- `-n, --non-interactive`: Use defaults without prompting

### 3. Configure API

During the interactive setup process, you will be prompted for:

- **Admin Password**: Used for sensitive API calls (`/api/list`, `/api/delete`).
- **Max VMs per Dev**: Hard cap for how many VMs a developer ID can host.
- **Max Inactivity Time**: How many minutes of idle time before a VM is auto-deleted.
- **Max Session Lifetime**: Absolute maximum session time regardless of activity.

Once complete, the API will be live at `http://localhost:8000`.

### 4. Pull the Xcloud Docker Image

Before creating VMs, pull the required Docker image:

```bash
docker pull xcloud
```

## Developer / Local Setup

To run the service locally for development or debugging, create a Python virtual environment and install dependencies.

Windows (PowerShell):

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python setup.py
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Linux / macOS:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python setup.py
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

If you previously committed a `venv/` directory to the repository, remove it from version control and add it to `.gitignore`:

```bash
git rm -r --cached venv
git commit -m "Remove committed virtualenv and ignore it"
```

## Running in Production

### Using the setup script with nohup

```bash
# Linux/Mac
nohup python setup.py --non-interactive &

# Windows
start /b python setup.py --non-interactive
```

### Using systemd (Linux)

Create a service file at `/etc/systemd/system/xcloud.service`:

```ini
[Unit]
Description=Xcloud VM Management API
After=network.target docker.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/path/to/ubx-vm-api
ExecStart=/path/to/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Then enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable xcloud
sudo systemctl start xcloud
```

### TLS/HTTPS Setup

The API itself runs over HTTP. To enable HTTPS, use Caddy as a reverse proxy.

**1. Install Caddy:**

```bash
# Linux
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo tee /etc/apt/trusted.gpg.d/caddy.asc
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/deb.debian.txt' | sudo tee /etc/apt/sources.list.d/caddy.list
sudo apt update
sudo apt install caddy

# macOS
brew install caddy

# Windows (PowerShell)
scoop install caddy
```

**2. Create a Caddyfile:**

Create a `Caddyfile` in your project directory:

./Caddyfile

**3. Run Caddy:**

```bash
# Development (auto HTTPS)
caddy run

# Production
caddy run --environment
```

Caddy will automatically obtain and renew TLS certificates from Let's Encrypt.

## Features

- **Queue System**: When global VM capacity is reached, requests are queued automatically
- **Premium Codes**: Create VMs that never auto-delete
- **Developer Whitelist**: Restrict VM creation to specific developer IDs
- **Admin Panel**: Access `/admin` for a web-based management interface
- **Rate Limiting**: Built-in rate limits prevent abuse
- **Resource Monitoring**: Real-time CPU stats for all containers
