# Configuration & Limits

Xcloud uses a `.env` file to manage its configuration. These can be set interactively during setup, via command-line arguments, or manually edited.

## Running setup.py with nohup

The setup script can be run non-interactively, which is useful when running with `nohup` or in automated deployments:

```bash
# Using defaults (uses existing .env values or built-in defaults)
nohup python setup.py --non-interactive &

# Using specific values via command-line arguments
nohup python setup.py -a mypass -m 50 -i 10 -s 120 -p "CODE1,CODE2" --max-free-vms 15 --max-premium-vms 5 --max-cpu-threads 4 --max-ram-gb 8 &

# Or use setup.sh which passes through arguments
nohup ./setup.sh -a mypass -m 50 -i 10 -s 120 -p "CODE1,CODE2" --max-free-vms 15 --max-premium-vms 5 --max-cpu-threads 4 --max-ram-gb 8 &

# Windows (Command Prompt)
start /b python setup.py -a mypass -m 50 -i 10 -s 120 -p "CODE1,CODE2" --max-free-vms 15 --max-premium-vms 5 --max-cpu-threads 4 --max-ram-gb 8
```

**Command-line options:**

- `-a, --admin-password`: API Admin Password
- `-m, --max-vms`: Max VMs per Developer
- `-i, --max-inactivity`: Max Inactivity Time (minutes)
- `-s, --max-session`: Max Session Lifetime (minutes)
- `-p, --premium-code`: Premium Code(s), comma-separated
- `-g, --max-global-vms`: Global max concurrent VMs (hard limit)
- `-w, --dev-whitelist`: Comma-separated developer IDs to whitelist
- `--max-free-vms`: Maximum concurrent free VMs (premium VMs excluded from this limit)
- `--max-premium-vms`: Maximum concurrent premium VMs (0 = unlimited)
- `--max-cpu-threads`: Maximum CPU threads (cores) per VM instance
- `--max-ram-gb`: Maximum RAM (GB) per VM instance
- `-n, --non-interactive`: Use defaults without prompting

## .env File Variables

### Core Variables
- **ADMIN_PASSWORD**: The password required for administrative actions (`/api/list`, `/api/delete`).
- **MAX_VMS_PER_DEV**: The hard cap for concurrent VMs per developer ID (Default: 100).
- **MAX_INACTIVITY_MINUTES**: The maximum inactivity time in minutes allowed before a VM is auto-deleted (Default: 5).
- **MAX_SESSION_MINUTES**: The absolute hard cap for any VM session, regardless of activity (Default: 60).
- **PREMIUM_CODE**: Comma-separated list of premium codes (optional). Premium VMs are never auto-deleted.

### Capacity & Access Control
- **MAX_GLOBAL_VMS**: The global hard cap for concurrently running VMs across all developers (Default: 10). If reached, new requests will be queued.
- **MAX_FREE_VMS**: Maximum concurrent free VMs. Premium VMs are excluded from this count (Default: 10). If reached, free VM requests will be queued.
- **MAX_PREmium_VMS**: Maximum concurrent premium VMs. Set to 0 for unlimited (Default: 0). If reached, premium VM requests will be queued.
- **MAX_CPU_THREADS**: Maximum CPU threads (cores) allocated per VM instance (Default: 4).
- **MAX_RAM_GB**: Maximum RAM (GB) allocated per VM instance (Default: 8).
- **ALLOW_ALL_DEVELOPERS**: When set to `1` (default) any `developer_id` may request VMs. Set to `0` to restrict creation to a whitelist.
- **DEV_WHITELIST**: Comma-separated list of `developer_id` values that are allowed to create VMs when `ALLOW_ALL_DEVELOPERS=0`.

### Server Configuration
- **HOST**: The host to bind to (Default: `0.0.0.0`).
- **PORT**: The port to listen on (Default: `8000`).
- **DEV_RELOAD**: Set to `1` to enable auto-reload in development (Default: `0`).

### Container Configuration
- **CONTAINER_STARTUP_TIMEOUT**: Seconds to wait for container service to be ready (Default: 60).

### TLS/HTTPS Support (Optional)
- **SSL_CERTFILE**: Path to PEM certificate file.
- **SSL_KEYFILE**: Path to PEM key file.
- **SSL_KEYFILE_PASSWORD**: Optional password for encrypted key files.

## Resource Capping

Each VM is automatically limited to:

- **CPU**: Configurable via MAX_CPU_THREADS (default: 4 cores, scales down for low-end servers).
- **RAM**: Configurable via MAX_RAM_GB (default: 8GB, mem_limit).
- **SHM**: 2GB (shm_size).

## High Usage Protection

When server CPU or RAM usage exceeds **90%**, the system will automatically attempt to free resources by deleting non-premium VMs:

1. First, up to 3 non-premium VMs are deleted
2. If usage remains critical, up to 5 more non-premium VMs are deleted
3. Premium VMs are **never** deleted automatically

This ensures the server remains operational even under heavy load.

## Queue System

When any VM limit is reached (global, free, or premium), new VM creation requests are queued. The queue system:

- Returns a `token` to the client for tracking
- Allows checking status via `/api/queue_status?token=<token>`
- Allows cancellation via `/api/queue_cancel?token=<token>`
- Automatically processes queued requests when capacity becomes available
- Queues are processed per-limit-type: free VMs only process when free slots open, premium when premium slots open, etc.

## Premium Features

VMs created with a valid premium code:
- Never auto-delete due to inactivity
- Never auto-delete due to max session lifetime
- Never auto-delete due to high server resource usage
- Can only be deleted via `/api/delete` endpoint
- Are marked with `premium: true` in API responses
- Do not count towards MAX_FREE_VMS limit (they use MAX_PREMIUM_VMS instead)
