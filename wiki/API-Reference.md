# API Reference

Detailed documentation for Xcloud API endpoints.

## Base URL
`http://<your-server-ip>:8000`

---

## 1. Create a VM
**`GET /api/create`**

Spins up a new Ubuntu VM with KasmVNC.

### Parameters
- `developer_id` (string): **Required.** Unique ID for the site.
- `site_limit` (integer): _Optional_ (Default: 5). Max concurrent VMs for this dev. Capped at `MAX_VMS_PER_DEV`.
- `delete_after` (integer): _Optional_. Secs of inactivity before auto-deletion. Capped at `MAX_INACTIVITY_MINUTES`.

### Response
```json
{
  "status": "success",
  "container_id": "...",
  "name": "vm-dev1-abc12345",
  "port": 49156,
  "developer_id": "dev1",
  "inactivity_timeout_seconds": 300,
  "url": "http://your-server-ip:49156"
}
```

---

## 2. List VMs
**`GET /api/list`**

Lists all running VMs. Requires administrative authentication.

### Authentication
- Pass via query: `?password=your_admin_password`
- Pass via header: `X-Admin-Password: your_admin_password`

### Parameters
- `developer_id` (string): _Optional_. Filter results by developer.

---

## 3. Delete a VM
**`GET /api/delete/{container_id}`**

Manually destroy a VM. Requires administrative authentication.
