# API Reference

Detailed documentation for Xcloud API endpoints.

## Base URL
`http://<your-server-ip>:8000`

---

## 1. Create a VM
**`GET /api/create`**

Spins up a new Ubuntu VM with KasmVNC.

### Rate Limit
5 requests per minute.

### Parameters
- `developer_id` (string): **Required.** Unique ID for the site.
- `site_limit` (integer): _Optional_ (Default: 5). Max concurrent VMs for this dev. Capped at `MAX_VMS_PER_DEV`.
- `delete_after` (integer): _Optional_. Seconds of inactivity before auto-deletion. Capped at `MAX_INACTIVITY_MINUTES`.
- `premium` (string): _Optional_. Premium code to enable premium features (no auto-deletion).

### Response (Success)
```json
{
  "status": "success",
  "container_id": "abc123...",
  "name": "vm-dev1-abc12345",
  "port": 49156,
  "developer_id": "dev1",
  "inactivity_timeout_seconds": 300,
  "max_session_minutes": 60,
  "premium": false,
  "message": "VM created successfully.",
  "url": "http://your-server-ip:49156"
}
```

### Response (Queued)
```json
{
  "status": "queued",
  "token": "abc123...",
  "position": 1,
  "message": "All free VMs currently in use; your request has been queued."
}
```

---

## 2. Check Queue Status
**`GET /api/queue_status?token=<token>`**

Check the status of a queued VM request.

### Response
```json
{
  "status": "queued",
  "position": 1
}
```
Or when processed:
```json
{
  "status": "allocated",
  "container_id": "abc123...",
  "name": "vm-dev1-abc12345",
  "port": 49156,
  "url": "http://your-server-ip:49156",
  "message": "VM allocated from queue"
}
```

---

## 3. Cancel Queue Request
**`GET /api/queue_cancel?token=<token>`**

Cancel a queued VM request.

### Response
```json
{
  "status": "success",
  "message": "Queued request cancelled"
}
```

---

## 4. List VMs
**`GET /api/list`**

Lists all VMs. Requires administrative authentication.

### Rate Limit
10 requests per minute.

### Authentication
- Pass via query: `?password=your_admin_password`
- Pass via header: `X-Admin-Password: your_admin_password`

### Parameters
- `developer_id` (string): _Optional_. Filter results by developer.

### Response
```json
{
  "status": "success",
  "system_cpu": 45.2,
  "vms": [
    {
      "id": "abc123...",
      "name": "vm-dev1-abc12345",
      "status": "running",
      "port": 49156,
      "developer_id": "dev1",
      "premium": false
    }
  ]
}
```

---

## 5. Delete a VM
**`GET /api/delete/{container_id}`**

Manually destroy a VM. Requires administrative authentication.

### Rate Limit
10 requests per minute.

### Authentication
- Pass via query: `?password=your_admin_password`
- Pass via header: `X-Admin-Password: your_admin_password`

### Response
```json
{
  "status": "success",
  "message": "Container abc123... stopped and removed"
}
```

---

## 6. Admin Containers
**`GET /api/admin/containers`**

Admin endpoint returning container list with CPU stats. Requires administrative authentication.

### Response
```json
{
  "status": "success",
  "system_cpu": 45.2,
  "vms": [
    {
      "id": "abc123...",
      "name": "vm-dev1-abc12345",
      "status": "running",
      "port": 49156,
      "developer_id": "dev1",
      "premium": false,
      "cpu_percent": 12.5
    }
  ]
}
```

---

## 7. Health Check
**`GET /api/health`** or **`GET /health`**

Returns API health status.

### Response
```json
{
  "status": "ok"
}
```

---

## Frontend Endpoints

- `/` - Serves main frontend (`static/index.html`)
- `/admin` - Serves admin panel (`static/admin/index.html`)

---

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Unauthorized: Invalid or missing password"
}
```

### 403 Forbidden
```json
{
  "detail": "Developer 'dev1' is not allowed to create VMs"
}
```

### 404 Not Found
```json
{
  "detail": "Container not found"
}
```

### 429 Rate Limit Exceeded
```json
{
  "detail": "Rate limit exceeded: ..."
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to start container: ..."
}
```
