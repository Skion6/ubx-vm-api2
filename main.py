import socket
import uuid
import docker
import asyncio
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends
from fastapi.security import APIKeyQuery, APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="VM Management API", description="API to provision and manage KasmVNC Ubuntu VMs")

# Hardcoded password for administrative actions
#CHANGE IT!!!
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

MAX_SESSION_MINUTES = 60  # Hard cap: all sessions deleted after 60 minutes

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
async def create_vm(request: Request, background_tasks: BackgroundTasks, developer_id: str, site_limit: int = 5, delete_after: int = None):
    """
    Spins up a new VM container for a developer, ensuring they don't exceed their site_limit.

    - delete_after: seconds of inactivity (idle CPU < 1%) before the VM is auto-deleted.
    - All sessions are hard-capped at 60 minutes regardless of activity.
    """
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
        def _run_container():
            return client.containers.run(
                "gamingoncodespaces",
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
                labels={"developer_id": developer_id},
                nano_cpus=int(allocated_cpus * 1e9),
                mem_limit="8g"
            )
        container = await asyncio.to_thread(_run_container)
        print(f"Successfully started container {container.name} ({container.id})")
        # change mem if u have shitty server
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
async def delete_vm(container_id: str, authorized: bool = Depends(verify_password)):
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
async def list_vms(developer_id: str = None, authorized: bool = Depends(verify_password)):
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
        res.append({
            "id": c.id,
            "name": c.name,
            "status": c.status,
            "port": host_port,
            "developer_id": c.labels.get("developer_id")
        })
    return {"status": "success", "vms": res}
