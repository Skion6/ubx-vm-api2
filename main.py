import socket
import uuid
import docker
import asyncio
import httpx
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends
from fastapi.security import APIKeyQuery, APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler

load_dotenv()
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Xcloud VM Management API", description="API to provision and manage Xcloud (Ubuntu) VMs")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configuration from environment variables
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "secret_password")
MAX_VMS_PER_DEV = int(os.getenv("MAX_VMS_PER_DEV", "100"))
MAX_INACTIVITY_MINUTES = int(os.getenv("MAX_INACTIVITY_MINUTES", "5"))
MAX_SESSION_MINUTES = int(os.getenv("MAX_SESSION_MINUTES", "60"))
PREMIUM_CODE = os.getenv("PREMIUM_CODE", "")

api_key_query = APIKeyQuery(name="password", auto_error=False)
api_key_header = APIKeyHeader(name="X-Admin-Password", auto_error=False)

def verify_password(
    password_query: str = Depends(api_key_query),
    password_header: str = Depends(api_key_header)
):
    if password_query == ADMIN_PASSWORD or password_header == ADMIN_PASSWORD:
        return True
    raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing password")

# Add CORS middleware to allow requests from websites
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production to specific domains if needed
    # Wildcard origins with credentials=True can cause CORS checks to fail
    # for WebSocket handshakes in some ASGI/CORS implementations. Use
    # explicit origins or disable credentials for websocket proxying.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    client = docker.from_env()
except Exception as e:
    print(f"Error initializing Docker client: {e}")
    client = None

# Serve frontend static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")

def get_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('', 0))
        port = s.getsockname()[1]
    except Exception as e:
        print(f"Error getting free port: {e}")
        # fallback to a random high port if bind fails
        import random
        port = random.randint(10000, 60000)
    finally:
        s.close()
    return port

@app.get("/api/health")
@app.get("/health")  # Redundant for external health checks (e.g. Caddy/AWS)
def health_check():
    return {"status": "ok"}


async def _delete_container(container_id: str, reason: str):
    """Helper to stop and remove a container using a thread to avoid blocking."""
    def _do_delete():
        try:
            container = client.containers.get(container_id)
            print(f"Stopping container {container_id} ({container.name}) due to: {reason}")
            container.stop(timeout=10)
            print(f"Removing container {container_id} (and its volumes)")
            container.remove(force=True, v=True)
            return f"Successfully deleted container {container_id}: {reason}"
        except docker.errors.NotFound:
             return f"Container {container_id} already deleted."
        except Exception as e:
            return f"Failed to delete container {container_id}: {e}"
            
    result = await asyncio.to_thread(_do_delete)
    print(result)

async def schedule_container_deletion(container_id: str, inactivity_seconds: int):
    """
    Background task that deletes a container after 'inactivity_seconds' of idle CPU,
    or after MAX_SESSION_MINUTES total lifetime — whichever comes first.

    Inactivity is measured by polling Docker CPU stats. A container is considered "idle" 
    when its CPU usage is below 0.5% of a *single core* (normalized to system CPUs).
    """
    import time
    import multiprocessing

    start_time = time.time()
    max_lifetime = MAX_SESSION_MINUTES * 60
    idle_since = time.time()
    poll_interval = 20  # interval between activity checks
    
    num_cpus = float(multiprocessing.cpu_count())

    while True:
        await asyncio.sleep(poll_interval)

        elapsed = time.time() - start_time
        if elapsed >= max_lifetime:
            await _delete_container(container_id, f"max session lifetime of {MAX_SESSION_MINUTES}m reached")
            return

        try:
            def _get_cpu_percent():
                """Takes two samples to get an accurate CPU usage delta."""
                c = client.containers.get(container_id)
                # Sample 1
                s1 = c.stats(stream=False)
                time.sleep(1.0) # 1-second delta for accuracy
                # Sample 2
                s2 = c.stats(stream=False)
                
                cpu_delta = s2["cpu_stats"]["cpu_usage"]["total_usage"] - s1["cpu_stats"]["cpu_usage"]["total_usage"]
                sys_delta = s2["cpu_stats"]["system_cpu_usage"] - s1["cpu_stats"]["system_cpu_usage"]
                
                if sys_delta > 0 and cpu_delta > 0:
                    # (delta / sys_delta) * num_cpus * 100.0 = % of total system capacity
                    # But we want to compare against "0.5% of one core" across all cores.
                    # docker stats style: (cpu_delta / system_delta) * system_cpu_count * 100
                    return (cpu_delta / sys_delta) * num_cpus * 100.0
                return 0.0

            cpu_percent = await asyncio.to_thread(_get_cpu_percent)

            # Threshold: 0.5% of a single core. 
            # If system has 8 cores, 0.5% of 1 core is 0.0625% total system CPU.
            # Using (delta / sys_delta) * num_cpus * 100 matches `docker stats`.
            if cpu_percent >= 0.5:
                idle_since = time.time()
                # print(f"Container {container_id} active: {cpu_percent:.2f}%") # noisy
            else:
                idle_duration = time.time() - idle_since
                if idle_duration >= inactivity_seconds:
                    await _delete_container(container_id, f"{inactivity_seconds}s of inactivity (CPU: {cpu_percent:.2f}%)")
                    return

        except docker.errors.NotFound:
            return
        except Exception as e:
            print(f"Error monitoring {container_id}: {e}")

async def schedule_hard_cap_deletion(container_id: str):
    """Enforces the hard 60-minute max session lifetime when no inactivity timeout is set."""
    await asyncio.sleep(MAX_SESSION_MINUTES * 60)
    await _delete_container(container_id, f"max session lifetime of {MAX_SESSION_MINUTES}m reached")

@app.get("/api/create")
@limiter.limit("5/minute")
async def create_vm(request: Request, background_tasks: BackgroundTasks, developer_id: str, site_limit: int = 5, delete_after: int = None, premium: str = None):
    """
    Spins up a new VM container for a developer, ensuring they don't exceed their site_limit.

    - delete_after: seconds of inactivity (idle CPU < 1%) before the VM is auto-deleted.
      Maximum allowed is MAX_INACTIVITY_MINUTES (default 5m).
    - All sessions are hard-capped at MAX_SESSION_MINUTES (default 60m) regardless of activity.
    - premium: optional premium code. If provided and matches PREMIUM_CODE, the VM will never
      be automatically deleted (premium VMs are only deleted via /api/delete).
    """
    # Validate premium code if provided (supports multiple codes separated by commas)
    is_premium = False
    if premium:
        valid_codes = [code.strip() for code in PREMIUM_CODE.split(",") if code.strip()]
        if premium in valid_codes:
            is_premium = True
        else:
            raise HTTPException(status_code=400, detail="Invalid premium code")

    # Enforce site_limit cap
    effective_site_limit = min(site_limit, MAX_VMS_PER_DEV)
    
    # Enforce inactivity cap (convert minutes to seconds)
    max_inactivity_seconds = MAX_INACTIVITY_MINUTES * 60
    if delete_after is None or delete_after > max_inactivity_seconds:
        effective_delete_after = max_inactivity_seconds
    else:
        effective_delete_after = delete_after

    # Premium VMs should never auto-delete, set to 0 (infinity)
    if is_premium:
        effective_delete_after = 0

    if not client:
        raise HTTPException(status_code=500, detail="Docker client not initialized. Is Docker running?")

    # 1. Check current running VMs for the developer using labels
    def _list_developer_containers():
        return client.containers.list(filters={"label": f"developer_id={developer_id}"})
        
    try:
        containers = await asyncio.to_thread(_list_developer_containers)
    except Exception as e:
        print(f"Error listing containers: {e}")
        raise HTTPException(status_code=500, detail="Failed to communicate with Docker")

    if len(containers) >= effective_site_limit:
        raise HTTPException(status_code=400, detail=f"Site limit of {effective_site_limit} VMs reached for developer '{developer_id}'")
    
    # 2. Get a free port on the host
    host_port = get_free_port()
    
    # 3. Start the container
    container_name = f"vm-{developer_id}-{uuid.uuid4().hex[:8]}"
    
    import multiprocessing
    # Get available system CPUs
    total_cpus = float(multiprocessing.cpu_count())
    # Cap at a maximum of 4 cores, but scale down if the server is low-end
    allocated_cpus = min(4.0, total_cpus)
    
    try:
        def _run_container():
            return client.containers.run(
                "xcloud",
                name=container_name,
                detach=True,
                environment={
                    "PUID": "1000",
                    "PGID": "1000",
                    "TZ": "Etc/UTC",
                    "SUBFOLDER": "/",
                    "TITLE": "Home - Classroom"
                },
                ports={'3000/tcp': host_port},
                shm_size="2gb",
                security_opt=["seccomp=unconfined"],
                labels={"developer_id": developer_id, "premium": str(is_premium).lower()},
                nano_cpus=int(allocated_cpus * 1e9),
                mem_limit="8g"
            )
        container = await asyncio.to_thread(_run_container)
        print(f"Successfully started container {container.name} ({container.id})")
        # change mem if u have shitty server
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start container: {str(e)}")

    # 4. Schedule deletion (skip for premium VMs - they only get deleted via /api/delete)
    if not is_premium:
        if effective_delete_after > 0:
            background_tasks.add_task(schedule_container_deletion, container.id, effective_delete_after)
        else:
            background_tasks.add_task(schedule_hard_cap_deletion, container.id)
        
    # Wait for the container's service to accept connections before returning the URL
    server_hostname = request.url.hostname

    import time
    # Increase the default startup timeout — some VMs take longer to fully initialize.
    STARTUP_TIMEOUT = int(os.getenv("CONTAINER_STARTUP_TIMEOUT", "60"))
    check_host = "127.0.0.1"
    check_url = f"http://{check_host}:{host_port}/"
    start_time = time.time()
    ready = False

    async with httpx.AsyncClient() as http_client:
        while time.time() - start_time < STARTUP_TIMEOUT:
            try:
                resp = await http_client.get(check_url, timeout=5.0)
                status = resp.status_code
                if status == 200:
                    ready = True
                    break
                if status == 502:
                    # Backend or proxy returned Bad Gateway — wait 1s and retry
                    await asyncio.sleep(1.0)
                    continue
                # Other non-200 statuses: wait briefly and retry
                await asyncio.sleep(0.5)
            except httpx.RequestError:
                # service not yet reachable; wait and retry
                await asyncio.sleep(0.5)

    if not ready:
        raise HTTPException(status_code=504, detail=f"Container started but service not returning 200 on port {host_port} within {STARTUP_TIMEOUT}s")

    url = f"http://{server_hostname}:{host_port}"
    return {
        "status": "success",
        "container_id": container.id,
        "name": container.name,
        "port": host_port,
        "developer_id": developer_id,
        "inactivity_timeout_seconds": effective_delete_after if not is_premium else None,
        "max_session_minutes": MAX_SESSION_MINUTES if not is_premium else None,
        "premium": is_premium,
        "message": "VM created successfully." + (" (premium - no auto-delete)" if is_premium else ""),
        "url": url
    }

@app.get("/api/delete/{container_id}")
@limiter.limit("10/minute")
async def delete_vm(request: Request, container_id: str, authorized: bool = Depends(verify_password)):
    """
    Stops and removes a VM using its container ID.
    """
    if not client:
        raise HTTPException(status_code=500, detail="Docker client not initialized.")

    try:
        def _do_delete():
            container = client.containers.get(container_id)
            container.stop(timeout=5)
            container.remove(force=True, v=True)
            
        await asyncio.to_thread(_do_delete)
        print(f"Manually deleted container {container_id}")
        return {"status": "success", "message": f"Container {container_id} stopped and removed"}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Container not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/list")
@limiter.limit("10/minute")
async def list_vms(request: Request, developer_id: str = None, authorized: bool = Depends(verify_password)):
    """
    Lists all VMs, optionally filtered by developer_id.
    """
    if not client:
        raise HTTPException(status_code=500, detail="Docker client not initialized.")

    filters = {}
    if developer_id:
        filters["label"] = f"developer_id={developer_id}"
    
    def _list_all():
        return client.containers.list(all=True, filters=filters)
        
    containers = await asyncio.to_thread(_list_all)
    
    res = []
    for c in containers:
        port_info = c.attrs['NetworkSettings']['Ports'].get('3000/tcp')
        host_port = port_info[0]['HostPort'] if port_info else None
        premium = True if (c.labels and c.labels.get("premium", "false").lower() == "true") else False
        res.append({
            "id": c.id,
            "name": c.name,
            "status": c.status,
            "port": host_port,
            "developer_id": c.labels.get("developer_id"),
            "premium": premium
        })

    # include system CPU if psutil available
    system_cpu = None
    try:
        import psutil
        system_cpu = psutil.cpu_percent(interval=0.5)
    except Exception:
        system_cpu = None

    return {"status": "success", "system_cpu": system_cpu, "vms": res}


if __name__ == "__main__":
    # Allow running the app directly with `python main.py` and bind to 0.0.0.0 by default.
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    # Enable reload only if DEV_RELOAD=1 in the environment (useful for development).
    reload_flag = os.getenv("DEV_RELOAD", "0") == "1"
    # Optional TLS/HTTPS support via environment variables:
    # - SSL_CERTFILE: path to PEM cert (or fullchain)
    # - SSL_KEYFILE: path to PEM key
    # - SSL_KEYFILE_PASSWORD: optional password for key
    ssl_cert = os.getenv("SSL_CERTFILE")
    ssl_key = os.getenv("SSL_KEYFILE")
    ssl_key_password = os.getenv("SSL_KEYFILE_PASSWORD")

    uvicorn_kwargs = {"host": host, "port": port, "reload": reload_flag}
    if ssl_cert and ssl_key:
        uvicorn_kwargs["ssl_certfile"] = ssl_cert
        uvicorn_kwargs["ssl_keyfile"] = ssl_key
        if ssl_key_password:
            uvicorn_kwargs["ssl_keyfile_password"] = ssl_key_password

    uvicorn.run(app, **uvicorn_kwargs)
