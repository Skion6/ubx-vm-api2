# Xcloud

A lightweight Python FastAPI application that provisions and manages isolated Linux (Ubuntu) VMs equipped with KasmVNC. This repository provides a scalable backend for allowing developers or websites to dynamically spin up fully-functional desktop environments via their browser.

> [!TIP]
> Check out the [Wiki](/wiki/Home.md) for detailed guides and API references.

## Features

- **Dynamic VM Provisioning**: Spin up Ubuntu desktops on-demand via a simple API call.
- **Hardware Constraints**: Each container is tightly limited to 4 CPU cores and 8GB of RAM.
- **Developer Limits**: Easily restrict how many VMs a specific developer or site can host concurrently (Default Max: 100).
- **Time Limits**: Automatically shut down and clean up containers after a set amount of inactivity (Default Max: 5 minutes).
- **Docker Image**: VMs use the `xcloud` Docker image.
- **Dynamic Routing**: Internal KasmVNC (port 3000) is dynamically mapped to free host ports.

## Requirements

To host this API, your server must have:

- Python 3.10+
- Docker Engine (or Docker Desktop) installed and running.

---

## 🚀 Easy Setup

### Linux / Mac

Run the built-in setup script from your terminal:

```bash
chmod +x tools/setup.sh
./tools/setup.sh
```

### Windows

Double click the `tools/setup.bat` file, or run it in your terminal:

```cmd
tools\setup.bat
```

The script will automatically build the `xcloud` Docker template, install Python dependencies, and launch the API server on **Port 8000**.
 
## 🧑‍💻 Developer / Local Setup

Run the service locally for development or debugging.

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

Notes:
- `python setup.py` runs the repository configuration helper and writes a `.env` file with defaults.
- Use `tools/setup.sh` or `tools/setup.bat` for the full production-oriented setup (builds the Docker image and configures the host).
- If a `venv/` directory exists in your repository, it's recommended to remove it from version control (add to `.gitignore` then run `git rm -r --cached venv`) rather than committing it.

---

## 🔌 API Endpoints

Once the server is running on `http://localhost:8000`, the following endpoints are available:

### 1. Create a VM

**`GET /api/create`**

Parameters:

- `developer_id` (string): **Required.** Unique identifier for the site or developer requesting the VM.
- `site_limit` (integer): _Optional_ (default: 5). The maximum number of concurrent VMs allowed for this `developer_id`.
- `delete_after` (integer): _Optional_. Automatically stop and destroy the container after this many minutes.

_Example Response:_

```json
{
  "status": "success",
  "container_id": "eb36b9c92cc",
  "name": "vm-test_dev-a1b2c3d4",
  "port": 49156,
  "developer_id": "test_dev",
  "auto_delete_minutes": 60,
  "message": "VM created successfully.",
  "url": "http://your_server_ip:49156"
}
```

**Accessing the VM:** Navigate to the returned `url` in your browser.

### 2. List VMs

**`GET /api/list`**

Parameters:

- `developer_id` (string): _Optional_. Filter the returned VMs by developer.

### 3. Delete a VM

**`GET /api/delete/{container_id}`**

Path parameter:

- `container_id` (string): **Required.** The ID of the container you wish to destroy.
