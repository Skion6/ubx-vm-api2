# Installation Guide

Follow these steps to set up Xcloud on your server.

## Prerequisites

- **Python 3.10+** (Recommend 3.11 for performance)
- **Docker Engine** (or Docker Desktop on Windows)
- **Git** (to clone the repo)

## Step-by-Step Setup

### 1. Clone & Enter Directory
```bash
git clone <your-repo-url>
cd ubx-vm-api
```

### 2. Run Setup Script

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

### 3. Configure API
During the setup process, you will be prompted for:
- **Admin Password**: Used for sensitive API calls (`/api/list`, `/api/delete`).
- **Max VMs per Dev**: Hard cap for how many VMs a developer ID can host.
- **Max Inactivity Time**: How many minutes of idle time before a VM is auto-deleted.

Once complete, the API will be live at `http://localhost:8000`.
