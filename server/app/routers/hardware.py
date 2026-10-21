import re
import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, status
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import get_database
from app.core.ws import ws_manager
from app.models.hardware import (
    HardwareSerialEventPayload,
    HardwareBridgeHeartbeatPayload,
    HardwareBridgeStatusResponse
)
from app.repositories.hardware import HardwareRepository
from app.repositories.user import UserRepository
from app.repositories.audit import AuditRepository

logger = logging.getLogger("hardware.router")

router = APIRouter(prefix="/hardware", tags=["hardware"])

# Sliding window in-memory cache to prevent event replay
_recent_event_ids: Dict[str, datetime] = {}

def verify_bridge_key(
    x_bridge_key: Optional[str] = Header(None, alias="X-Bridge-Key"),
    auth_header: Optional[str] = Header(None, alias="Authorization"),
    key_query: Optional[str] = Query(None, alias="bridge_key")
):
    """Enforce authentication for the local Python serial bridge."""
    expected_key = settings.HARDWARE_BRIDGE_SECRET
    provided_key = x_bridge_key or key_query
    
    if not provided_key and auth_header and auth_header.startswith("Bearer "):
        provided_key = auth_header.replace("Bearer ", "").strip()
        
    if not provided_key or provided_key != expected_key:
        logger.warning("Hardware bridge authentication failed: invalid or missing key")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid or missing bridge authentication key (X-Bridge-Key header required)."
        )
    return True

@router.post("/events", status_code=status.HTTP_201_CREATED)
async def ingest_hardware_serial_event(
    payload: HardwareSerialEventPayload,
    request: Request,
    _: bool = Depends(verify_bridge_key)
):
    """
    Ingest a validated hardware event parsed from the ESP32 USB serial bridge.
    - Validates message format and parameters.
    - Maps RFID UID to registered investigator records.
    - Distinguishes hardware-reported status from backend-verified identity.
    - Persists audit trail in MongoDB without bypassing standard authentication.
    """
    db = get_database()
    hardware_repo = HardwareRepository(db)
    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)

    # 1. Replay & Duplicate Protection
    event_id = payload.event_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    # Prune old cache entries older than 30 seconds
    for k in list(_recent_event_ids.keys()):
        if (now - _recent_event_ids[k]).total_seconds() > 30.0:
            _recent_event_ids.pop(k, None)

    if event_id in _recent_event_ids:
        logger.info(f"Duplicate event {event_id} ignored via replay protection.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "status": "duplicate_ignored",
                "event_id": event_id,
                "message": "Event already processed"
            }
        )
    _recent_event_ids[event_id] = now

    # 2. Normalize and Map RFID UID to an Investigator
    clean_uid = re.sub(r'[\s:-]', '', payload.uid).upper()
    try:
        user = await user_repo.get_by_rfid(payload.uid)
    except Exception as dbe:
        logger.error(f"Database lookup error during investigator mapping: {dbe}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable during hardware event processing."
        )

    mapped_investigator = None
    is_identity_verified = False
    verification_notes = ""

    if user:
        if not user.get("is_active", True):
            is_identity_verified = False
            verification_notes = f"Investigator account ({user.get('email')}) is deactivated."
        else:
            mapped_investigator = {
                "id": str(user["_id"]),
                "name": user.get("name"),
                "email": user.get("email"),
                "role": user.get("role"),
                "rfid": user.get("rfid")
            }
            if payload.status == "GRANTED":
                is_identity_verified = True
                verification_notes = f"Identity verified: {user.get('name')} ({user.get('email')})"
            else:
                is_identity_verified = False
                verification_notes = f"UID belongs to {user.get('name')}, but ESP32 reported DENIED ({payload.reason})."
    else:
        # Crucial: Never invent identities or map arbitrary users for unknown UIDs!
        is_identity_verified = False
        verification_notes = f"Unregistered RFID UID '{payload.uid}'. No forensic investigator mapped."

    # 3. Construct and Save Hardware Event Record
    event_doc = {
        "event_id": event_id,
        "protocol_version": payload.protocol_version,
        "device_id": payload.device_id,
        "status": payload.status,
        "uid": payload.uid,
        "normalized_uid": clean_uid,
        "reason": payload.reason,
        "is_identity_verified": is_identity_verified,
        "mapped_investigator": mapped_investigator,
        "verification_notes": verification_notes,
        "raw_message": payload.raw_message,
        "timestamp": now
    }

    try:
        saved_event = await hardware_repo.create_event(event_doc)
    except Exception as e:
        logger.error(f"Failed to persist hardware event document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record hardware event: {str(e)}"
        )

    # 4. Integrate into MongoDB Audit Log (Forensic Chain of Custody)
    try:
        audit_action = "hardware_auth_granted" if payload.status == "GRANTED" else "hardware_auth_denied"
        await audit_repo.create_log(
            user_id=mapped_investigator["id"] if mapped_investigator else None,
            action=audit_action,
            ip_address=request.client.host if request.client else "127.0.0.1",
            user_agent="USB_SERIAL_BRIDGE",
            device_id=payload.device_id,
            details=(
                f"ESP32 USB Event: {payload.status} | UID={payload.uid} | "
                f"Reason={payload.reason} | Identity Verified={is_identity_verified} | "
                f"Notes={verification_notes}"
            )
        )
    except Exception as ae:
        logger.error(f"Failed to create audit log entry for hardware event: {ae}")

    # 5. Broadcast to connected WebSocket clients for real-time dashboard updates
    try:
        await ws_manager.broadcast({
            "type": "hardware_serial_event",
            "event": saved_event
        })
    except Exception as wse:
        logger.warning(f"WebSocket broadcast error: {wse}")

    return {
        "success": True,
        "event_id": event_id,
        "status": payload.status,
        "is_identity_verified": is_identity_verified,
        "mapped_investigator": mapped_investigator,
        "notes": verification_notes,
        "timestamp": now.isoformat()
    }

@router.post("/bridge-heartbeat")
async def update_bridge_heartbeat(
    payload: HardwareBridgeHeartbeatPayload,
    _: bool = Depends(verify_bridge_key)
):
    """Receive periodic telemetry and status from the Python USB serial bridge."""
    db = get_database()
    hardware_repo = HardwareRepository(db)
    
    updated = await hardware_repo.update_bridge_heartbeat(
        port=payload.port,
        status=payload.status,
        baud_rate=payload.baud_rate,
        device_id=payload.device_id,
        error_message=payload.error_message
    )
    
    # Broadcast bridge status change to frontend
    try:
        await ws_manager.broadcast({
            "type": "hardware_bridge_status",
            "bridge": updated
        })
    except Exception as wse:
        logger.warning(f"WebSocket broadcast error: {wse}")

    return {"status": "acknowledged", "server_time": datetime.now(timezone.utc).isoformat()}

@router.get("/bridge-status", response_model=HardwareBridgeStatusResponse)
async def get_bridge_status():
    """
    Get live connection health and status of the Python USB Serial Bridge.
    Returns:
    - 'Connected' only if active heartbeats received in the last 12 seconds.
    - 'Error' if serial port is blocked or an exception occurred.
    - 'Disconnected' if bridge is stopped or unresponsive.
    """
    db = get_database()
    hardware_repo = HardwareRepository(db)
    state = await hardware_repo.get_bridge_state()
    latest_event = await hardware_repo.get_latest_event()

    if not state:
        return {
            "status": "Disconnected",
            "port": settings.ESP32_COM_PORT,
            "baud_rate": settings.ESP32_BAUD_RATE,
            "last_heartbeat": None,
            "last_event": latest_event,
            "error_message": "Serial bridge has not registered yet."
        }

    now = datetime.now(timezone.utc)
    last_hb = state.get("last_heartbeat")
    if last_hb and last_hb.tzinfo is None:
        last_hb = last_hb.replace(tzinfo=timezone.utc)

    # Check freshness: Must have sent heartbeat within 12 seconds
    is_fresh = last_hb and (now - last_hb).total_seconds() <= 12.0
    reported_status = state.get("status", "Disconnected")

    if not is_fresh:
        effective_status = "Disconnected"
    elif reported_status == "Error":
        effective_status = "Error"
    elif reported_status == "Connected":
        effective_status = "Connected"
    else:
        effective_status = "Disconnected"

    return {
        "status": effective_status,
        "port": state.get("port", settings.ESP32_COM_PORT),
        "baud_rate": state.get("baud_rate", settings.ESP32_BAUD_RATE),
        "last_heartbeat": last_hb.isoformat() if last_hb else None,
        "last_event": latest_event,
        "error_message": state.get("error_message")
    }

@router.get("/events")
async def list_hardware_events(
    limit: int = Query(25, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status")
):
    """Retrieve recent hardware serial authentication events."""
    db = get_database()
    hardware_repo = HardwareRepository(db)
    events = await hardware_repo.list_events(limit=limit, status_filter=status_filter)
    return {"events": events, "count": len(events)}
