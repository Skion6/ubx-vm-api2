# Configuration & Limits

Xcloud uses a `.env` file to manage its configuration. These can be set interactively during setup, via command-line arguments, or manually edited.

## Running setup.py with nohup

The setup script can be run non-interactively, which is useful when running with `nohup` or in automated deployments:

```bash
# Using defaults (uses existing .env values or built-in defaults)
nohup python setup.py --non-interactive &

# Using specific values via command-line arguments
nohup python setup.py -a mypass -m 50 -i 10 -s 120 -p "CODE1,CODE2" &

# Or use setup.sh which passes through arguments
nohup ./tools/setup.sh -a mypass -m 50 -i 10 -s 120 -p "CODE1,CODE2" &

# Windows (Command Prompt)
start /b python setup.py -a mypass -m 50 -i 10 -s 120 -p "CODE1,CODE2"
```

**Command-line options:**

- `-a, --admin-password`: API Admin Password
- `-m, --max-vms`: Max VMs per Developer
- `-i, --max-inactivity`: Max Inactivity Time (minutes)
- `-s, --max-session`: Max Session Lifetime (minutes)
- `-p, --premium-code`: Premium Code(s), comma-separated
- `-n, --non-interactive`: Use defaults without prompting

## .env File Variables

- **ADMIN_PASSWORD**: The password required for administrative actions (`/api/list`, `/api/delete`).
- **MAX_VMS_PER_DEV**: The hard cap for concurrent VMs per developer ID (Default: 100).
- **MAX_INACTIVITY_MINUTES**: The maximum inactivity time in minutes allowed before a VM is auto-deleted (Default: 5).
- **MAX_SESSION_MINUTES**: The absolute hard cap for any VM session, regardless of activity (Default: 60).
- **PREMIUM_CODE**: Comma-separated list of premium codes (optional).

Additional variables added in recent releases:

- **MAX_GLOBAL_VMS**: The global hard cap for concurrently running VMs across all developers (Default: 10). If reached, new requests will be queued.
- **ALLOW_ALL_DEVELOPERS**: When set to `1` (default) any `developer_id` may request VMs. Set to `0` to restrict creation to a whitelist.
- **DEV_WHITELIST**: Comma-separated list of `developer_id` values that are allowed to create VMs when `ALLOW_ALL_DEVELOPERS=0`.

## Resource Capping

Each VM is automatically limited to:

- **CPU**: 4 Cores (default, scales down for low-end servers).
- **RAM**: 8GB (mem_limit).
- **SHM**: 2GB (shm_size).
