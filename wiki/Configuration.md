# Configuration & Limits

Xcloud uses a `.env` file to manage its configuration. These can be set interactively during setup or manually edited.

## .env File Variables

- **ADMIN_PASSWORD**: The password required for administrative actions (`/api/list`, `/api/delete`).
- **MAX_VMS_PER_DEV**: The hard cap for concurrent VMs per developer ID (Default: 100).
- **MAX_INACTIVITY_MINUTES**: The maximum inactivity time in minutes allowed before a VM is auto-deleted (Default: 5).
- **MAX_SESSION_MINUTES**: The absolute hard cap for any VM session, regardless of activity (Default: 60).

## Resource Capping

Each VM is automatically limited to:
- **CPU**: 4 Cores (default, scales down for low-end servers).
- **RAM**: 8GB (mem_limit).
- **SHM**: 2GB (shm_size).
