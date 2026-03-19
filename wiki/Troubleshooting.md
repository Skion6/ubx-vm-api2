# Troubleshooting

Common issues and how to fix them.

## 1. 502 Bad Gateway

- **Cause**: Docker container is still starting up.
- **Fix**: Wait 5-10 seconds and refresh.

## 2. Docker is not running

- **Fix**: Ensure `docker service` (Linux) or `Docker Desktop` (Windows) is actually running before starting the API.

## 3. Port Conflicts

- **Fix**: Xcloud will attempt to find a free port automatically. If it fails, ensure your firewall allows high-range ports (10000+).
