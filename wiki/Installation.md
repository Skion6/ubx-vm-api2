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
chmod +x setup.sh
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
- `-n, --non-interactive`: Use defaults without prompting

### 3. Configure API

During the interactive setup process, you will be prompted for:

- **Admin Password**: Used for sensitive API calls (`/api/list`, `/api/delete`).
- **Max VMs per Dev**: Hard cap for how many VMs a developer ID can host.
- **Max Inactivity Time**: How many minutes of idle time before a VM is auto-deleted.
- **Max Session Lifetime**: Absolute maximum session time regardless of activity.

Once complete, the API will be live at `http://localhost:8000`.
