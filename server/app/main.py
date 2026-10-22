import sys
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.core.ws import ws_manager
from app.routers import auth, settings as settings_router, audit, cases, evidence, events, analytics, reports, security, diary, hardware, portal_manager
from app.routers import backup as backup_router
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from app.services.security_tracking_service import SecurityTrackingService

# Route logging to stdout so cloud deployment consoles (Railway, Render, GCP) don't display normal INFO logs in red stderr bars
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
for _log_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    _logger = logging.getLogger(_log_name)
    for _handler in _logger.handlers:
        _handler.setStream(sys.stdout)

# Background task to monitor device status and mark timed-out devices offline
async def monitor_device_heartbeats():
    print("Starting ESP32 heartbeat monitor background worker...")
    while True:
        try:
            await asyncio.sleep(5)
            db = get_database()
            # Threshold: 15 seconds since last seen
            threshold = datetime.now(timezone.utc) - timedelta(seconds=15)
            
            # Find devices that are online but haven't sent heartbeats recently
            cursor = db["devices"].find({
                "status": "online",
                "last_seen": {"$lt": threshold}
            })
            
            async for device in cursor:
                # Update status to offline
                await db["devices"].update_one(
                    {"_id": device["_id"]},
                    {"$set": {"status": "offline"}}
                )
                
                # Log the event in Chain of Custody
                await db["audit_logs"].insert_one({
                    "user_id": None,
                    "action": "device_offline",
                    "ip_address": "127.0.0.1",
                    "user_agent": "SYSTEM_WORKER",
                    "device_id": device["device_id"],
                    "details": f"Device {device['device_id']} went offline due to missed heartbeat.",
                    "timestamp": datetime.now(timezone.utc)
                })
                
                # Broadcast status update
                await ws_manager.broadcast({
                    "type": "device_status",
                    "device_id": device["device_id"],
                    "status": "offline"
                })
                print(f"Device {device['device_id']} timed out and marked OFFLINE.")
                
        except RuntimeError:
            # Database client might not be initialized yet during startup
            pass
        except Exception as e:
            print(f"Error in heartbeat monitor: {e}")

from app.core.bootstrap import ensure_default_users

db_startup_error = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_startup_error
    # Startup: Connect to MongoDB
    try:
        await connect_to_mongo()
        # Ensure default users and configurations are present & healthy
        await ensure_default_users()
        # Sync settings from DB into memory cache
        await settings_router.sync_settings_from_db()
        db_startup_error = None
    except Exception as e:
        db_startup_error = str(e)
        print(f"\n{'='*70}\n[STARTUP WARNING] Database connection error during startup:\n{e}\n"
              "Server will continue running to bind port and provide diagnostics.\n"
              "Please configure a valid MONGO_URL in your cloud environment variables.\n"
              f"{'='*70}\n")
    
    # Start device status background checker
    heartbeat_task = asyncio.create_task(monitor_device_heartbeats())
    
    yield
    
    # Shutdown: Cancel background tasks and close DB client
    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass
    await close_mongo_connection()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
@app.get("/health")
async def health_check():
    """Diagnostic health check for cloud load balancers and deployment verification."""
    if db_startup_error:
        return {
            "status": "degraded",
            "message": "CRYPTEVID Forensic Server is active, but MongoDB connection failed.",
            "database_error": db_startup_error,
            "instruction": "Please set a valid MONGO_URL in your Render dashboard environment variables."
        }
    return {
        "status": "healthy",
        "service": "CRYPTEVID Forensic Intelligence Server",
        "database": "connected"
    }

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"^https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(auth.router, prefix="")  # Support /auth/login and /hardware/authenticate directly
app.include_router(settings_router.router, prefix=settings.API_V1_STR)
app.include_router(audit.router, prefix=settings.API_V1_STR)
app.include_router(cases.router, prefix=settings.API_V1_STR)
app.include_router(evidence.router, prefix=settings.API_V1_STR)
app.include_router(events.router, prefix=settings.API_V1_STR)
app.include_router(analytics.router, prefix=settings.API_V1_STR)
app.include_router(reports.router, prefix=settings.API_V1_STR)
app.include_router(security.router, prefix=settings.API_V1_STR)
app.include_router(backup_router.router, prefix=settings.API_V1_STR)
app.include_router(diary.router, prefix=settings.API_V1_STR)
app.include_router(hardware.router, prefix=settings.API_V1_STR)
app.include_router(hardware.router, prefix="")
app.include_router(portal_manager.router, prefix=settings.API_V1_STR)
app.include_router(portal_manager.router, prefix="")

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """
    Forensic security interceptor:
    Automatically records 401 Unauthorized and 403 Forbidden events
    on sensitive API endpoints into security_events.
    """
    if exc.status_code in (401, 403) and request.url.path.startswith(settings.API_V1_STR):
        # /auth/login is tracked via dedicated failed-login tracker
        if not request.url.path.endswith("/auth/login"):
            try:
                await SecurityTrackingService.record_http_security_event(request, exc.status_code, str(exc.detail))
            except Exception as e:
                print(f"[SECURITY_TRACKING_ERR] Failed to record security event: {e}")

    headers = getattr(exc, "headers", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    tb = traceback.format_exc()
    print(f"\n[UNHANDLED SERVER EXCEPTION on {request.method} {request.url.path}]:\n{tb}\n")
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal Server Error: {str(exc)}",
            "type": type(exc).__name__,
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )
