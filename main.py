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
MAX_FREE_VMS = int(os.getenv("MAX_FREE_VMS", "10"))
MAX_PREMIUM_VMS = int(os.getenv("MAX_PREMIUM_VMS", "0"))
MAX_PREMIUM_VMS_PER_CODE = int(os.getenv("MAX_PREMIUM_VMS_PER_CODE", "1"))
MAX_CPU_THREADS = int(os.getenv("MAX_CPU_THREADS", "4"))
MAX_RAM_GB = int(os.getenv("MAX_RAM_GB", "8"))
HIGH_USAGE_THRESHOLD = 90

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

# Global queue for VM creation requests when capacity is exhausted
# Stores pending requests as dicts: {token, developer_id, effective_site_limit, effective_delete_after, is_premium, server_hostname, requested_at}
from collections import deque
import secrets
vm_request_queue = deque()
# Results mapping for tokens -> status/result
vm_queue_results = {}
# Lock guarding access to the queue/results
vm_queue_lock = asyncio.Lock()
# Maximum number of concurrent VMs allowed (global cap). Can be set via env.
MAX_GLOBAL_VMS = int(os.getenv("MAX_GLOBAL_VMS", "10"))
# Whitelist configuration: allow all developers by default, or restrict to a comma-separated list
ALLOW_ALL_DEVELOPERS = os.getenv("ALLOW_ALL_DEVELOPERS", "1")
ALLOW_ALL_DEVELOPERS_BOOL = str(ALLOW_ALL_DEVELOPERS).lower() in ("1", "true", "yes", "y")
DEV_WHITELIST = os.getenv("DEV_WHITELIST", "")
DEV_WHITELIST_SET = set([s.strip() for s in DEV_WHITELIST.split(",") if s.strip()]) if DEV_WHITELIST else set()

def is_developer_allowed(dev_id: str) -> bool:
    """Return True if the developer_id is permitted to create VMs."""
    if ALLOW_ALL_DEVELOPERS_BOOL:
        return True
    return dev_id in DEV_WHITELIST_SET

# Serve frontend static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")

@app.get("/admin")
async def serve_admin():
    return FileResponse("static/admin/index.html")


@app.get("/admin/")
async def serve_admin_slash():
    return FileResponse("static/admin/index.html")


@app.get("/api/admin/containers")
async def admin_containers(request: Request, authorized: bool = Depends(verify_password)):
    """Admin endpoint returning container list and basic CPU stats."""
    if not client:
        raise HTTPException(status_code=500, detail="Docker client not initialized.")

    def _list_all():
        return client.containers.list(all=True)
    containers = await asyncio.to_thread(_list_all)

    res = []
    for c in containers:
        port_info = c.attrs.get('NetworkSettings', {}).get('Ports', {}).get('3000/tcp')
        host_port = port_info[0]['HostPort'] if port_info else None
        premium = True if (c.labels and c.labels.get("premium", "false").lower() == "true") else False
        cpu_percent = None
        try:
            stats = c.stats(stream=False)
            precpu = stats.get('precpu_stats') or {}
            cpu_stats = stats.get('cpu_stats') or {}
            cpu_delta = cpu_stats.get('cpu_usage', {}).get('total_usage', 0) - precpu.get('cpu_usage', {}).get('total_usage', 0)
            sys_delta = cpu_stats.get('system_cpu_usage', 0) - precpu.get('system_cpu_usage', 0)
            num_cpus = float(cpu_stats.get('online_cpus') or len(cpu_stats.get('cpu_usage', {}).get('percpu_usage') or [1]))
            if sys_delta > 0 and cpu_delta > 0:
                cpu_percent = (cpu_delta / sys_delta) * num_cpus * 100.0
            else:
                cpu_percent = 0.0
        except Exception:
            cpu_percent = None

        res.append({
            "id": c.id,
            "name": c.name,
            "status": c.status,
            "port": host_port,
            "developer_id": c.labels.get("developer_id") if c.labels else None,
            "premium": premium,
            "cpu_percent": cpu_percent
        })

    system_cpu = None
    system_memory = None
    try:
        import psutil
        system_cpu = psutil.cpu_percent(interval=0.5)
        system_memory = psutil.virtual_memory().percent
    except Exception:
        system_cpu = None
        system_memory = None

    return {"status": "success", "system_cpu": system_cpu, "system_memory": system_memory, "vms": res}


@app.get("/api/queue_status")
async def queue_status(token: str):
    """Check the status of a queued VM request by token."""
    async with vm_queue_lock:
        if token in vm_queue_results:
            return vm_queue_results[token]
        for idx, item in enumerate(vm_request_queue):
            if item.get("token") == token:
                return {"status": "queued", "position": idx + 1}
    raise HTTPException(status_code=404, detail="Token not found")


@app.get("/api/queue_cancel")
async def queue_cancel(token: str):
    """Cancel a queued VM request."""
    async with vm_queue_lock:
        for item in list(vm_request_queue):
            if item.get("token") == token:
                vm_request_queue.remove(item)
                vm_queue_results[token] = {"status": "cancelled"}
                return {"status": "success", "message": "Queued request cancelled"}
    raise HTTPException(status_code=404, detail="Token not found")

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
    # After a container is removed, attempt to process any queued VM requests
    try:
        await process_queue()
    except Exception as e:
        print(f"Error processing VM queue after deletion: {e}")

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

            # Threshold: 10% of total system CPU.
            # VMs using less than this are considered idle and count toward inactivity timeout.
            # VMs above this are considered active (resets idle timer).
            IDLE_CPU_THRESHOLD = 10.0
            if cpu_percent >= IDLE_CPU_THRESHOLD:
                idle_since = time.time()
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


async def count_running_vms():
    """Return the number of currently running VMs created by this service."""
    if not client:
        return 0
    def _list_running():
        # default all=False -> only running containers
        return client.containers.list(filters={"label": "developer_id"})
    try:
        containers = await asyncio.to_thread(_list_running)
        return len(containers)
    except Exception:
        return 0


async def count_free_vms():
    """Return the number of currently running non-premium VMs."""
    if not client:
        return 0
    def _list_running():
        return client.containers.list(filters={"label": "developer_id"})
    try:
        containers = await asyncio.to_thread(_list_running)
        return sum(1 for c in containers if c.labels.get("premium", "false").lower() != "true")
    except Exception:
        return 0


async def count_premium_vms():
    """Return the number of currently running premium VMs."""
    if not client:
        return 0
    def _list_running():
        return client.containers.list(filters={"label": "developer_id"})
    try:
        containers = await asyncio.to_thread(_list_running)
        return sum(1 for c in containers if c.labels.get("premium", "false").lower() == "true")
    except Exception:
        return 0


async def count_premium_vms_by_code(premium_code: str):
    """Return the number of currently running premium VMs for a specific code."""
    if not client:
        return 0
    def _list_running():
        return client.containers.list(filters={"label": "developer_id"})
    try:
        containers = await asyncio.to_thread(_list_running)
        return sum(1 for c in containers if c.labels.get("premium", "false").lower() == "true" and c.labels.get("premium_code", "") == premium_code)
    except Exception:
        return 0


async def get_system_usage():
    """Get system CPU and RAM usage percentages. Returns (cpu_percent, memory_percent)."""
    cpu_percent = 0.0
    memory_percent = 0.0
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        memory_percent = mem.percent
    except Exception:
        pass
    return cpu_percent, memory_percent


async def delete_non_premium_vms(count: int):
    """Delete up to 'count' non-premium VMs to free up resources."""
    if not client:
        return 0
    def _list_all():
        return client.containers.list(filters={"label": "developer_id"})
    try:
        containers = await asyncio.to_thread(_list_all)
        non_premium = [c for c in containers if c.labels.get("premium", "false").lower() != "true"]
        deleted = 0
        for c in non_premium[:count]:
            await _delete_container(c.id, "high server resource usage")
            deleted += 1
        return deleted
    except Exception as e:
        print(f"Error deleting non-premium VMs: {e}")
        return 0


async def _spawn_and_wait(developer_id: str, effective_delete_after: int, is_premium: bool, server_hostname: str, use_background_tasks: bool = False, background_tasks: BackgroundTasks = None, premium_code: str = None):
    """Spawn a container and wait for its service to be ready. Returns dict with container, host_port and url."""
    import multiprocessing
    total_cpus = float(multiprocessing.cpu_count())
    allocated_cpus = min(float(MAX_CPU_THREADS), total_cpus)

    host_port = get_free_port()
    container_name = f"vm-{developer_id}-{uuid.uuid4().hex[:8]}"
    ram_limit = f"{MAX_RAM_GB}g"

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
                labels={"developer_id": developer_id, "premium": str(is_premium).lower(), "premium_code": premium_code if premium_code else ""},
                nano_cpus=int(allocated_cpus * 1e9),
                mem_limit=ram_limit
            )
        container = await asyncio.to_thread(_run_container)
    except Exception as e:
        raise

    # Schedule deletion for non-premium VMs
    if not is_premium:
        if effective_delete_after > 0:
            if use_background_tasks and background_tasks:
                background_tasks.add_task(schedule_container_deletion, container.id, effective_delete_after)
            else:
                asyncio.create_task(schedule_container_deletion(container.id, effective_delete_after))
        else:
            if use_background_tasks and background_tasks:
                background_tasks.add_task(schedule_hard_cap_deletion, container.id)
            else:
                asyncio.create_task(schedule_hard_cap_deletion(container.id))

    # Wait for the container's service to accept connections
    import time
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
                    await asyncio.sleep(1.0)
                    continue
                await asyncio.sleep(0.5)
            except httpx.RequestError:
                await asyncio.sleep(0.5)

    if not ready:
        # cleanup container if service didn't become ready
        try:
            await asyncio.to_thread(lambda: client.containers.get(container.id).remove(force=True, v=True))
        except Exception:
            pass
        raise Exception(f"Container started but service not ready on port {host_port} within {STARTUP_TIMEOUT}s")

    url = f"http://{server_hostname}:{host_port}"
    return {"container": container, "host_port": host_port, "url": url}


async def process_queue():
    """Attempt to allocate VMs for queued requests while capacity allows."""
    async with vm_queue_lock:
        # iterate while we have capacity and queued requests
        while vm_request_queue:
            item = vm_request_queue.popleft()
            token = item.get("token")
            developer_id = item.get("developer_id")
            effective_site_limit = item.get("effective_site_limit")
            effective_delete_after = item.get("effective_delete_after")
            is_premium = item.get("is_premium")
            server_hostname = item.get("server_hostname")
            premium_code = item.get("premium_code")
            queue_type = item.get("type", "global_limit")

            # Check capacity based on queue type
            if queue_type == "free_limit":
                current_free = await count_free_vms()
                if current_free >= MAX_FREE_VMS:
                    vm_request_queue.appendleft(item)  # Put back at front
                    break
            elif queue_type == "premium_limit":
                # Check per-code limit for premium VMs
                if premium_code and MAX_PREMIUM_VMS_PER_CODE > 0:
                    current_premium_by_code = await count_premium_vms_by_code(premium_code)
                    if current_premium_by_code >= MAX_PREMIUM_VMS_PER_CODE:
                        vm_queue_results[token] = {"status": "failed", "reason": f"Premium code limit of {MAX_PREMIUM_VMS_PER_CODE} VMs reached for code '{premium_code}'"}
                        continue
                if MAX_PREMIUM_VMS > 0:
                    current_premium = await count_premium_vms()
                    if current_premium >= MAX_PREMIUM_VMS:
                        vm_request_queue.appendleft(item)
                        break
            else:
                current = await count_running_vms()
                if current >= MAX_GLOBAL_VMS:
                    vm_request_queue.appendleft(item)
                    break

            # Check developer site limit before allocating
            def _list_dev():
                return client.containers.list(filters={"label": f"developer_id={developer_id}"})
            try:
                dev_containers = await asyncio.to_thread(_list_dev)
            except Exception as e:
                vm_queue_results[token] = {"status": "failed", "reason": f"Docker error listing developer containers: {e}"}
                continue

            if len(dev_containers) >= effective_site_limit:
                vm_queue_results[token] = {"status": "failed", "reason": "site limit reached for developer when processing queue"}
                continue

            # Try to spawn and wait for the VM
            try:
                info = await _spawn_and_wait(developer_id, effective_delete_after, is_premium, server_hostname, premium_code=premium_code)
                container = info["container"]
                vm_queue_results[token] = {
                    "status": "allocated",
                    "container_id": container.id,
                    "name": container.name,
                    "port": info["host_port"],
                    "url": info["url"],
                    "message": "VM allocated from queue"
                }
            except Exception as e:
                vm_queue_results[token] = {"status": "failed", "reason": str(e)}
                continue

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
    # Enforce developer whitelist first
    if not is_developer_allowed(developer_id):
        raise HTTPException(status_code=403, detail=f"Developer '{developer_id}' is not allowed to create VMs")

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
    
    # Check system resource usage and delete non-premium VMs if critical
    cpu_percent, memory_percent = await get_system_usage()
    if cpu_percent >= HIGH_USAGE_THRESHOLD or memory_percent >= HIGH_USAGE_THRESHOLD:
        print(f"High system usage detected: CPU {cpu_percent:.1f}%, RAM {memory_percent:.1f}%. Attempting to free resources by deleting non-premium VMs.")
        deleted = await delete_non_premium_vms(3)
        if deleted > 0:
            print(f"Deleted {deleted} non-premium VMs due to high resource usage")
            cpu_percent, memory_percent = await get_system_usage()
            if cpu_percent >= HIGH_USAGE_THRESHOLD or memory_percent >= HIGH_USAGE_THRESHOLD:
                deleted2 = await delete_non_premium_vms(5)
                print(f"Deleted additional {deleted2} non-premium VMs")

    # Check capacity limits based on VM type (free vs premium)
    server_hostname = request.url.hostname
    
    if is_premium:
        # Check premium code per-code limit
        if MAX_PREMIUM_VMS_PER_CODE > 0:
            current_premium_by_code = await count_premium_vms_by_code(premium)
            if current_premium_by_code >= MAX_PREMIUM_VMS_PER_CODE:
                raise HTTPException(status_code=400, detail=f"Premium code limit of {MAX_PREMIUM_VMS_PER_CODE} VMs reached for code '{premium}'")
        
        # Check premium VM limit (0 means unlimited)
        if MAX_PREMIUM_VMS > 0:
            current_premium = await count_premium_vms()
            if current_premium >= MAX_PREMIUM_VMS:
                token = secrets.token_urlsafe(8)
                queued_item = {
                    "token": token,
                    "developer_id": developer_id,
                    "effective_site_limit": effective_site_limit,
                    "effective_delete_after": effective_delete_after,
                    "is_premium": is_premium,
                    "server_hostname": server_hostname,
                    "premium_code": premium,
                    "requested_at": int(__import__('time').time())
                }
                async with vm_queue_lock:
                    vm_request_queue.append(queued_item)
                    position = len(vm_request_queue)
                    vm_queue_results[token] = {"status": "queued", "position": position, "type": "premium_limit"}
                return {"status": "queued", "token": token, "position": position, "message": "Premium VM limit reached; your request has been queued."}
    else:
        # Check free VM limit
        current_free = await count_free_vms()
        if current_free >= MAX_FREE_VMS:
            token = secrets.token_urlsafe(8)
            queued_item = {
                "token": token,
                "developer_id": developer_id,
                "effective_site_limit": effective_site_limit,
                "effective_delete_after": effective_delete_after,
                "is_premium": is_premium,
                "server_hostname": server_hostname,
                "premium_code": premium,
                "requested_at": int(__import__('time').time())
            }
            async with vm_queue_lock:
                vm_request_queue.append(queued_item)
                position = len(vm_request_queue)
                vm_queue_results[token] = {"status": "queued", "position": position, "type": "free_limit"}
            return {"status": "queued", "token": token, "position": position, "message": "Free VM limit reached; your request has been queued."}
    
    # Also check global VM limit as hard cap
    current_running = await count_running_vms()
    if current_running >= MAX_GLOBAL_VMS:
        token = secrets.token_urlsafe(8)
        queued_item = {
            "token": token,
            "developer_id": developer_id,
            "effective_site_limit": effective_site_limit,
            "effective_delete_after": effective_delete_after,
            "is_premium": is_premium,
            "server_hostname": server_hostname,
            "premium_code": premium,
            "requested_at": int(__import__('time').time())
        }
        async with vm_queue_lock:
            vm_request_queue.append(queued_item)
            position = len(vm_request_queue)
            vm_queue_results[token] = {"status": "queued", "position": position, "type": "global_limit"}

        return {"status": "queued", "token": token, "position": position, "message": "All VMs currently in use; your request has been queued."}

    # Start container and wait for it to be ready
    try:
        info = await _spawn_and_wait(developer_id, effective_delete_after, is_premium, server_hostname, use_background_tasks=True, background_tasks=background_tasks, premium_code=premium)
        container = info["container"]
        host_port = info["host_port"]
        url = info["url"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start container: {str(e)}")
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
