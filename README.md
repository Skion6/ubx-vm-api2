# VM Management API (GamingOnCodespaces)

# Powered by UBX

A lightweight Python FastAPI application that provisions and manages isolated Linux (Ubuntu) VMs equipped with KasmVNC. This repository provides a scalable backend for allowing developers or websites to dynamically spin up fully-functional desktop environments via their browser.

## Features

- **Dynamic VM Provisioning**: Spin up Ubuntu desktops on-demand via a simple API call.
- **Hardware Constraints**: Each container is tightly limited to 4 CPU cores and 8GB of RAM.
- **Developer Limits**: Easily restrict how many VMs a specific developer or site can host concurrently.
- **Time Limits**: Automatically shut down and clean up containers after a set amount of minutes.
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
chmod +x setup.sh
./setup.sh
```

### Windows

Double click the `setup.bat` file, or run it in your terminal:

```cmd
setup.bat
```

The script will automatically build the `gamingoncodespaces` Docker template, install Python dependencies, and launch the API server on **Port 8000**.

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
