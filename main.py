import socket
import uuid
import docker
import asyncio
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends
from fastapi.security import APIKeyQuery, APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="VM Management API", description="API to provision and manage KasmVNC Ubuntu VMs")

# Hardcoded password for administrative actions
ADMIN_PASSWORD = "secret_password"

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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    client = docker.from_env()
except Exception as e:
    print(f"Error initializing Docker client: {e}")
    client = None

def get_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

MAX_SESSION_MINUTES = 60  # Hard cap: all sessions deleted after 60 minutes

async def _delete_container(container_id: str, reason: str):
    """Helper to stop and remove a container."""
    try:
        container = client.containers.get(container_id)
        container.stop(timeout=5)
        container.remove(force=True)
        print(f"Auto-deleted container {container_id}: {reason}")
    except Exception as e:
        print(f"Failed to auto-delete container {container_id}: {e}")

async def schedule_container_deletion(container_id: str, inactivity_seconds: int):
    """
    Background task that deletes a container after 'inactivity_seconds' of idle CPU,
    or after MAX_SESSION_MINUTES total lifetime — whichever comes first.

    Inactivity is measured by polling Docker CPU stats every 15 seconds.
    A container is considered "idle" when its CPU usage is below 1%.
    """
    import time

    start_time = time.time()
    max_lifetime = MAX_SESSION_MINUTES * 60
    idle_since = time.time()          # Track when the container last became idle
    poll_interval = 15                # Seconds between activity checks

    while True:
        await asyncio.sleep(poll_interval)

        elapsed = time.time() - start_time

        # --- Hard 60-minute cap ---
        if elapsed >= max_lifetime:
            await _delete_container(container_id, f"max session lifetime of {MAX_SESSION_MINUTES}m reached")
            return

        # --- Check CPU activity via Docker stats ---
        try:
            container = client.containers.get(container_id)
            stats = container.stats(stream=False)

            cpu_delta = (
                stats["cpu_stats"]["cpu_usage"]["total_usage"]
                - stats["precpu_stats"]["cpu_usage"]["total_usage"]
            )
            system_delta = (
                stats["cpu_stats"]["system_cpu_usage"]
                - stats["precpu_stats"]["system_cpu_usage"]
            )

            if system_delta > 0 and cpu_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * 100.0
            else:
                cpu_percent = 0.0

            if cpu_percent >= 1.0:
                # Container is active — reset the idle timer
                idle_since = time.time()
            else:
                # Container is idle — check if inactivity threshold exceeded
                if time.time() - idle_since >= inactivity_seconds:
                    await _delete_container(
                        container_id,
                        f"{inactivity_seconds}s of inactivity"
                    )
                    return

        except docker.errors.NotFound:
            # Container was already removed externally
            print(f"Container {container_id} no longer exists, stopping monitor.")
            return
        except Exception as e:
            print(f"Error checking stats for {container_id}: {e}")

async def schedule_hard_cap_deletion(container_id: str):
    """Enforces the hard 60-minute max session lifetime when no inactivity timeout is set."""
    await asyncio.sleep(MAX_SESSION_MINUTES * 60)
    await _delete_container(container_id, f"max session lifetime of {MAX_SESSION_MINUTES}m reached")

@app.get("/api/create")
def create_vm(request: Request, background_tasks: BackgroundTasks, developer_id: str, site_limit: int = 5, delete_after: int = None):
    """
    Spins up a new VM container for a developer, ensuring they don't exceed their site_limit.

    - delete_after: seconds of inactivity (idle CPU < 1%) before the VM is auto-deleted.
    - All sessions are hard-capped at 60 minutes regardless of activity.
    """
    if not client:
        raise HTTPException(status_code=500, detail="Docker client not initialized. Is Docker running?")

    # 1. Check current running VMs for the developer using labels
    containers = client.containers.list(filters={"label": f"developer_id={developer_id}"})
    if len(containers) >= site_limit:
        raise HTTPException(status_code=400, detail=f"Site limit of {site_limit} VMs reached for developer '{developer_id}'")
    
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
        container = client.containers.run(
            "gamingoncodespaces",
            name=container_name,
            detach=True,
            environment={
                "PUID": "1000",
                "PGID": "1000",
                "TZ": "Etc/UTC",
                "SUBFOLDER": "/",
                "TITLE": "VM API Instance"
            },
            ports={'3000/tcp': host_port},
            shm_size="2gb",
            security_opt=["seccomp=unconfined"],
            labels={"developer_id": developer_id},
            nano_cpus=int(allocated_cpus * 1e9),
            mem_limit="8g"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start container: {str(e)}")

    # 4. Schedule deletion
    if delete_after is not None and delete_after > 0:
        # Inactivity-based deletion (also enforces the 60m hard cap internally)
        background_tasks.add_task(schedule_container_deletion, container.id, delete_after)
    else:
        # No inactivity timeout — still enforce the 60-minute hard cap
        background_tasks.add_task(schedule_hard_cap_deletion, container.id)
        
    # 5. Build dynamic return URL based on requested host
    server_hostname = request.url.hostname
    
    return {
        "status": "success",
        "container_id": container.id,
        "name": container.name,
        "port": host_port,
        "developer_id": developer_id,
        "inactivity_timeout_seconds": delete_after,
        "max_session_minutes": MAX_SESSION_MINUTES,
        "message": "VM created successfully.",
        "url": f"http://{server_hostname}:{host_port}"
    }

@app.get("/api/delete/{container_id}")
def delete_vm(container_id: str, authorized: bool = Depends(verify_password)):
    """
    Stops and removes a VM using its container ID.
    """
    if not client:
        raise HTTPException(status_code=500, detail="Docker client not initialized.")

    try:
        container = client.containers.get(container_id)
        container.stop(timeout=5)
        container.remove(force=True)
        return {"status": "success", "message": f"Container {container_id} stopped and removed"}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Container not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/list")
def list_vms(developer_id: str = None, authorized: bool = Depends(verify_password)):
    """
    Lists all VMs, optionally filtered by developer_id.
    """
    if not client:
        raise HTTPException(status_code=500, detail="Docker client not initialized.")

    filters = {}
    if developer_id:
        filters["label"] = f"developer_id={developer_id}"
    
    containers = client.containers.list(all=True, filters=filters)
    
    res = []
    for c in containers:
        port_info = c.attrs['NetworkSettings']['Ports'].get('3000/tcp')
        host_port = port_info[0]['HostPort'] if port_info else None
        res.append({
            "id": c.id,
            "name": c.name,
            "status": c.status,
            "port": host_port,
            "developer_id": c.labels.get("developer_id")
        })
    return {"status": "success", "vms": res}
