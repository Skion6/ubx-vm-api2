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

async def schedule_container_deletion(container_id: str, minutes: int):
    """Background task to wait 'minutes' and then forcefully delete the container."""
    await asyncio.sleep(minutes * 60)
    try:
        # Re-fetch the container to make sure it exists
        container = client.containers.get(container_id)
        container.stop(timeout=5)
        container.remove(force=True)
        print(f"Auto-deleted container {container_id} after {minutes} minutes.")
    except Exception as e:
        print(f"Failed to auto-delete container {container_id}: {e}")

@app.get("/api/create")
def create_vm(request: Request, background_tasks: BackgroundTasks, developer_id: str, site_limit: int = 5, delete_after: int = None):
    """
    Spins up a new VM container for a developer, ensuring they don't exceed their site_limit.
    Optionally auto-deletes the VM after 'delete_after' minutes.
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
        # By default, Docker containers are isolated from each other.
        # They have their own filesystem space, separate networking stacks, and separate IPC namespaces.
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
            nano_cpus=int(allocated_cpus * 1e9), # Dynamically bound cores
            mem_limit="8g"            # 8 gigs of RAM
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start container: {str(e)}")

    # 4. Schedule auto-deletion if requested
    if delete_after is not None and delete_after > 0:
        background_tasks.add_task(schedule_container_deletion, container.id, delete_after)
        
    # 5. Build dynamic return URL based on requested host
    # request.client.host gets the IP of the requester, request.url.hostname gets the server's IP/domain
    server_hostname = request.url.hostname
    protocol = request.url.scheme
    
    return {
        "status": "success",
        "container_id": container.id,
        "name": container.name,
        "port": host_port,
        "developer_id": developer_id,
        "auto_delete_minutes": delete_after,
        "message": f"VM created successfully.",
        "url": f"https://{server_hostname}/vm/{host_port}/"
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
