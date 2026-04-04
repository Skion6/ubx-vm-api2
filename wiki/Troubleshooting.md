# Troubleshooting

Common issues and how to fix them.

## 1. 502 Bad Gateway

- **Cause**: Docker container is still starting up.
- **Fix**: Wait 5-10 seconds and refresh. The API waits up to 60 seconds for the container to become ready.

## 2. Docker is not running

- **Fix**: Ensure `docker service` (Linux) or `Docker Desktop` (Windows) is actually running before starting the API.

## 3. Port Conflicts

- **Fix**: Xcloud will attempt to find a free port automatically. If it fails, ensure your firewall allows high-range ports (10000+).

## 4. Rate Limit Exceeded

- **Cause**: Too many requests to `/api/create` (5/min) or `/api/delete`/`/api/list` (10/min).
- **Fix**: Wait for the rate limit window to reset, or implement client-side caching.

## 5. "All free VMs currently in use"

- **Cause**: Global VM limit (`MAX_GLOBAL_VMS`) has been reached.
- **Fix**: 
  - Wait for existing VMs to be deleted
  - Check the queue position using the token returned
  - Cancel queued requests via `/api/queue_cancel?token=<token>` if no longer needed

## 6. "Developer is not allowed to create VMs"

- **Cause**: Developer whitelist is enabled but the `developer_id` is not in `DEV_WHITELIST`.
- **Fix**: 
  - Set `ALLOW_ALL_DEVELOPERS=1` in `.env`
  - Or add the developer ID to `DEV_WHITELIST`

## 7. "Invalid premium code"

- **Cause**: The premium code provided does not match any code in `PREMIUM_CODE`.
- **Fix**: Verify the premium code matches exactly (codes are comma-separated in `.env`).

## 8. Container starts but service not ready

- **Cause**: The Docker container started but the internal service didn't become responsive within the timeout.
- **Fix**: Check Docker logs for the container: `docker logs <container_name>`

## 9. VM not auto-deleting

- **Cause**: The VM is a premium VM (created with a valid premium code).
- **Fix**: Premium VMs never auto-delete. Delete manually via `/api/delete/{container_id}`.

## 10. "Site limit reached"

- **Cause**: The developer has already created the maximum number of VMs allowed by `site_limit` (capped by `MAX_VMS_PER_DEV`).
- **Fix**: Delete existing VMs or request a higher limit.

## Viewing Logs

```bash
# Linux - view API logs
journalctl -u xcloud -f

# Docker container logs
docker logs <container_name>

# Local development
python main.py
```

## Health Check

Verify the API is running:

```bash
curl http://localhost:8000/api/health
# Returns: {"status":"ok"}
```
