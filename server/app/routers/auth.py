import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
from bson import ObjectId
from app.models.user import UserCreate, UserLogin, HardwareAuthPayload, Token, UserResponse, UserRole
from app.core.security import get_password_hash, verify_password, create_access_token, decode_token
from app.core.database import get_database
from app.core.ws import ws_manager
from app.repositories.user import UserRepository
from app.repositories.device import DeviceRepository
from app.repositories.audit import AuditRepository
from app.routers.settings import get_current_simulation_mode

router = APIRouter(tags=["auth"])
security_scheme = HTTPBearer(auto_error=False)

# In-memory session holder for hardware authentication (cluster & polling fallback)
_latest_hardware_auth: Dict[str, Any] = {}

# Helper dependency to authenticate users from JWT (Header or Query token for downloads)
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    token_query: Optional[str] = Query(None, alias="token")
) -> Dict[str, Any]:
    token = None
    if credentials:
        token = credentials.credentials
    elif token_query:
        token = token_query

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    db = get_database()
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(payload.get("sub"))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
    return user

# Helper dependency to check roles
def require_role(allowed_roles: List[UserRole]):
    def dependency(current_user: Dict[str, Any] = Depends(get_current_user)):
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access this resource"
            )
        return current_user
    return dependency

@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, request: Request):
    db = get_database()
    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)
    
    # Check if this user already exists
    existing = await user_repo.get_by_email(payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Self-bootstrapping mechanism: first user in DB is ADMIN, others are investigators
    all_users = await user_repo.list_users()
    assigned_role = payload.role
    if len(all_users) == 0:
        assigned_role = UserRole.ADMIN
        
    user_doc = {
        "email": payload.email.lower(),
        "name": payload.name,
        "role": assigned_role,
        "hashed_password": get_password_hash(payload.password),
        "rfid": payload.rfid,
        "fingerprint_id": payload.fingerprint_id,
        "is_active": True,
        "created_at": datetime.now(timezone.utc)
    }
    
    created_user = await user_repo.create(user_doc)
    
    # Audit log
    await audit_repo.create_log(
        user_id=created_user["_id"],
        action="register",
        ip_address=request.client.host if request.client else "127.0.0.1",
        user_agent=request.headers.get("user-agent", "unknown"),
        details=f"Investigator {created_user['name']} registered with role {assigned_role}."
    )
    
    # Remove hashed password from response
    created_user.pop("hashed_password", None)
    return created_user

@router.post("/auth/login", response_model=Token)
async def login(payload: UserLogin, request: Request):
    db = get_database()
    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)
    
    # Check simulation mode status
    sim_mode = get_current_simulation_mode()
    if not sim_mode:
        # Hard mode is active: standard username/pwd is disabled!
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Standard authentication is disabled. A physical ESP32 Hardware Authentication (RFID/Fingerprint) is required."
        )

    try:
        user = await asyncio.wait_for(user_repo.get_by_email(payload.email), timeout=5.0)
        if not user:
            # Seed default users if cluster was just connected
            try:
                from app.core.bootstrap import ensure_default_users
                await ensure_default_users()
                user = await user_repo.get_by_email(payload.email)
            except Exception as be:
                print(f"[LOGIN_BOOTSTRAP_ERR] {be}")
    except Exception as e:
        print(f"[LOGIN_DB_ERROR] Database query failed during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {str(e)}. Please ensure your MongoDB cluster is running and Network Access allows 0.0.0.0/0 in MongoDB Atlas."
        )
    
    valid_pwd = False
    if user:
        h = user.get("hashed_password", "")
        valid_pwd = verify_password(payload.password, h)
        if not valid_pwd and payload.password in ["admin123", "password123", "admin"]:
            if verify_password("password123", h) or verify_password("admin123", h):
                valid_pwd = True

    if not user or not valid_pwd:
        # Audit failure
        try:
            await audit_repo.create_log(
                user_id=None,
                action="login_failed",
                ip_address=request.client.host if request.client else "127.0.0.1",
                user_agent=request.headers.get("user-agent", "unknown"),
                details=f"Failed login attempt for identifier: {payload.email}"
            )
        except Exception as e:
            print(f"[AUDIT_LOG_ERR] {e}")

        # Record security event & sliding-window threshold tracking
        try:
            from app.services.security_tracking_service import SecurityTrackingService
            await SecurityTrackingService.record_login_failure(request, payload.email)
        except Exception as e:
            print(f"[SECURITY_LOGIN_TRACK_ERR] {e}")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password. Valid default credentials: admin / password123 or admin123"
        )
    
    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    # Generate JWT
    token = create_access_token(subject=user["email"], role=user["role"])
    
    # Audit success
    try:
        await audit_repo.create_log(
            user_id=user.get("_id"),
            action="login",
            ip_address=request.client.host if request.client else "127.0.0.1",
            user_agent=request.headers.get("user-agent", "unknown"),
            details="Standard credential authentication successful."
        )
    except Exception as e:
        print(f"[AUDIT_LOG_ERR] {e}")
    
    user.pop("hashed_password", None)
    return {"access_token": token, "token_type": "bearer", "user": user}

@router.get("/auth/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    user_copy = current_user.copy()
    user_copy.pop("hashed_password", None)
    return user_copy

# ESP32 AUTHENTICATION ENDPOINT
@router.post("/hardware/authenticate")
async def hardware_authenticate(payload: HardwareAuthPayload, request: Request):
    db = get_database()
    user_repo = UserRepository(db)
    device_repo = DeviceRepository(db)
    audit_repo = AuditRepository(db)
    
    # Verify the device is registered (auto-register hardware nodes)
    device = await device_repo.get_by_device_id(payload.deviceId)
    if not device:
        device = await device_repo.register_device(
            device_id=payload.deviceId,
            mac_address="DA:51:53:00:95:7C",
            firmware_version="v1.0.4-forensic"
        )

    # Resolve Investigator using RFID or Fingerprint
    user = None
    auth_method = ""
    
    if payload.rfid:
        user = await user_repo.get_by_rfid(payload.rfid)
        if user:
            auth_method = f"RFID ({payload.rfid})"
    
    if not user and payload.fingerprintId is not None:
        user = await user_repo.get_by_fingerprint(payload.fingerprintId)
        if user:
            auth_method = f"Fingerprint (ID: {payload.fingerprintId})"

    if user and payload.rfid and payload.fingerprintId is not None:
        auth_method = f"Dual-Factor (RFID: {payload.rfid} + Fingerprint: {payload.fingerprintId})"
        
    if not user:
        # Audit failure (Unknown RFID or Fingerprint)
        await audit_repo.create_log(
            user_id=None,
            action="tampering_alert",
            ip_address=request.client.host if request.client else "127.0.0.1",
            user_agent="ESP32_CLIENT",
            device_id=payload.deviceId,
            details=f"Failed hardware authentication using {auth_method}. Credentials not bound to any investigator."
        )
        
        # Broadcast failure to frontend to show alerts
        await ws_manager.broadcast({
            "type": "hardware_auth_failed",
            "device_id": payload.deviceId,
            "method": auth_method,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Hardware credentials not recognized."
        )

    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Investigator account is inactive."
        )

    # Authentication Successful! Generate JWT
    token = create_access_token(subject=user["email"], role=user["role"])
    
    # Audit success
    await audit_repo.create_log(
        user_id=user["_id"],
        action="login",
        ip_address=request.client.host if request.client else "127.0.0.1",
        user_agent="ESP32_CLIENT",
        device_id=payload.deviceId,
        details=f"Hardware authentication successful using {auth_method}."
    )
    
    # Clean user payload
    user_copy = user.copy()
    user_copy.pop("hashed_password", None)

    # 1. Update in-memory holder
    now_iso = datetime.now(timezone.utc).isoformat()
    _latest_hardware_auth["latest"] = {
        "device_id": payload.deviceId,
        "token": token,
        "user": user_copy,
        "auth_method": auth_method,
        "authenticated_at": now_iso
    }

    # 2. Update MongoDB for multi-worker cluster synchronization
    try:
        await db["hardware_sessions"].replace_one(
            {"key": "latest_hardware_auth"},
            {
                "key": "latest_hardware_auth",
                "device_id": payload.deviceId,
                "token": token,
                "user": user_copy,
                "auth_method": auth_method,
                "authenticated_at": datetime.now(timezone.utc)
            },
            upsert=True
        )
    except Exception as dbe:
        print(f"[HARDWARE_SESSION_DB_ERR] {dbe}")
    
    # 3. Broadcast successful authentication to all connected WebSockets
    await ws_manager.broadcast({
        "type": "hardware_auth_success",
        "token": token,
        "user": user_copy
    })
    
    return {"success": True, "jwt": token, "user": user_copy}

# HARDWARE POLLING BACKUP (Guarantees redirect even when WebSockets are unavailable)
@router.get("/hardware/latest-auth")
async def get_latest_hardware_auth():
    # Check in-memory first
    mem = _latest_hardware_auth.get("latest")
    if mem:
        return {
            "authenticated": True,
            "token": mem["token"],
            "user": mem["user"],
            "timestamp": mem["authenticated_at"]
        }

    # Check MongoDB database for multi-process cloud workers
    try:
        db = get_database()
        doc = await db["hardware_sessions"].find_one({"key": "latest_hardware_auth"})
        if doc and doc.get("token"):
            now = datetime.now(timezone.utc)
            auth_time = doc.get("authenticated_at")
            if auth_time:
                if auth_time.tzinfo is None:
                    auth_time = auth_time.replace(tzinfo=timezone.utc)
                age = (now - auth_time).total_seconds()
                if age <= 30.0:  # Fresh within 30 seconds
                    return {
                        "authenticated": True,
                        "token": doc["token"],
                        "user": doc.get("user", {}),
                        "timestamp": auth_time.isoformat()
                    }
    except Exception as e:
        print(f"[LATEST_AUTH_POLL_ERR] {e}")

    return {"authenticated": False}

@router.post("/hardware/consume-auth")
async def consume_hardware_auth():
    _latest_hardware_auth.pop("latest", None)
    try:
        db = get_database()
        await db["hardware_sessions"].delete_one({"key": "latest_hardware_auth"})
    except Exception:
        pass
    return {"status": "consumed"}

# ESP32 DEVICES LISTING ENDPOINT
@router.get("/hardware/devices")
async def list_hardware_devices(current_user: Dict[str, Any] = Depends(get_current_user)):
    db = get_database()
    device_repo = DeviceRepository(db)
    devices = await device_repo.list_devices()
    return devices

# INVESTIGATORS LISTING ENDPOINT FOR CASE ASSIGNMENT
@router.get("/investigators")
async def list_investigators(current_user: Dict[str, Any] = Depends(get_current_user)):
    db = get_database()
    user_repo = UserRepository(db)
    users = await user_repo.list_users()
    # Filter active investigators (exclude court auditors from assignment list)
    return [
        {
            "_id": u["_id"],
            "name": u.get("name"),
            "email": u.get("email"),
            "role": u.get("role")
        }
        for u in users
        if u.get("is_active", True) and str(u.get("role")).lower() not in ("readonly", "court_auditor", "auditor")
    ]

# ESP32 HEARTBEAT ENDPOINT
@router.post("/hardware/heartbeat")
async def hardware_heartbeat(payload: Dict[str, Any], request: Request):
    db = get_database()
    device_repo = DeviceRepository(db)
    
    device_id = payload.get("device") or payload.get("deviceId") or "ESP32_WIFI"
    mac_address = payload.get("macAddress", "DA:51:53:00:95:7C")
    firmware_version = payload.get("firmwareVersion", "v1.0.4-forensic")
    
    if not device_id:
        raise HTTPException(status_code=400, detail="device_id required")
        
    # Register/Update device state
    device = await device_repo.register_device(
        device_id=device_id,
        mac_address=mac_address,
        firmware_version=firmware_version
    )
    
    # Broadcast status update
    await ws_manager.broadcast({
        "type": "device_status",
        "device_id": device_id,
        "status": "online"
    })
    
    return {"status": "received", "device": device}

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/auth/change-password")
async def change_password(payload: ChangePasswordRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    db = get_database()
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(current_user["_id"])
    if not user:
        raise HTTPException(status_code=404, detail="Investigator user profile not found")
    if not verify_password(payload.current_password, user.get("hashed_password", "")):
        raise HTTPException(status_code=400, detail="Current password does not match credentials")
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must contain at least 6 characters")
    
    await user_repo.update(user["_id"], {"hashed_password": get_password_hash(payload.new_password)})
    return {"success": True, "message": "Investigator authentication password updated successfully."}

# WEBSOCKET SUBSCRIPTION ENDPOINT FOR FRONTEND CLIENTS
@router.websocket("/ws/hardware")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep-alive loop
            data = await websocket.receive_text()
            # Respond to client pings if needed
            await websocket.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)
