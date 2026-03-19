# Troubleshooting

Common issues and how to fix them.

## 1. 502 Bad Gateway
- **Cause**: Docker container is still starting up.
- **Fix**: Wait 5-10 seconds and refresh.

## 2. Docker is not running
- **Fix**: Ensure `docker service` (Linux) or `Docker Desktop` (Windows) is actually running before starting the API.

## 3. Port Conflicts
- **Fix**: Xcloud will attempt to find a free port automatically. If it fails, ensure your firewall allows high-range ports (10000+).

## 4. Resource Errors
- **Fix**: Each VM needs 8GB of RAM. If you are on a small VPS, you may need to lower the `mem_limit` in `main.py`.
