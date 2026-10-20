from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from app.core.database import get_database
from app.routers.auth import get_current_user
from app.models.user import UserRole
from app.models.security_event import (
    SecurityEventResponse,
    SecurityEventListResponse,
    SecurityAlertResponse,
    SecurityAlertListResponse,
    AlertStatusUpdatePayload,
    SecurityMetricsResponse,
    SecurityAlertStatus
)

router = APIRouter(prefix="/security", tags=["security"])

def verify_security_view_permission(current_user: Dict[str, Any]):
    """Enforce RBAC for viewing security logs and alerts."""
    role = current_user.get("role")
    if role in (UserRole.ADMIN, UserRole.INVESTIGATOR):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="UNAUTHORIZED: Viewers cannot access detailed security events and incident logs"
    )

def verify_security_admin_permission(current_user: Dict[str, Any]):
    """Enforce Admin-only permission for critical operations."""
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="UNAUTHORIZED: Only administrators can perform this security operation"
        )

# ==============================================================================
# SECURITY EVENTS ENDPOINTS
# ==============================================================================

@router.get("/events", response_model=SecurityEventListResponse)
async def list_security_events(
    event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    case_id: Optional[str] = Query(None),
    evidence_id: Optional[str] = Query(None),
    ip_address: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve filtered, paginated unauthorized access and security events."""
    verify_security_view_permission(current_user)
    db = get_database()

    query: Dict[str, Any] = {}
    if event_type:
        query["event_type"] = event_type
    if severity:
        query["severity"] = severity
    if case_id:
        query["case_id"] = case_id
    if evidence_id:
        query["evidence_id"] = evidence_id
    if ip_address:
        query["ip_address"] = ip_address

    # Role scoping: Investigators see their assigned cases or unassigned security events
    if current_user.get("role") == UserRole.INVESTIGATOR:
        user_id = str(current_user["_id"])
        # Find cases where investigator is assigned
        user_cases_cursor = db["cases"].find({"$or": [{"assigned_investigator": ObjectId(user_id)}, {"created_by": ObjectId(user_id)}]})
        user_cases = await user_cases_cursor.to_list(length=500)
        user_case_ids = [str(c["_id"]) for c in user_cases]
        
        # Scoped query: either belonging to investigator's cases, or unassigned global security events
        if case_id and case_id not in user_case_ids:
            return SecurityEventListResponse(total=0, skip=skip, limit=limit, events=[])
        if not case_id:
            query["$or"] = [
                {"case_id": {"$in": user_case_ids}},
                {"case_id": None},
                {"user_id": user_id}
            ]

    total = await db["security_events"].count_documents(query)
    cursor = db["security_events"].find(query).sort("timestamp", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)

    events = []
    for d in docs:
        d["_id"] = str(d["_id"])
        events.append(SecurityEventResponse(**d))

    return SecurityEventListResponse(
        total=total,
        skip=skip,
        limit=limit,
        events=events
    )

@router.get("/events/{event_id}", response_model=SecurityEventResponse)
async def get_security_event(
    event_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Inspect detailed security event provenance and fingerprint."""
    verify_security_view_permission(current_user)
    db = get_database()

    doc = await db["security_events"].find_one({
        "$or": [{"event_id": event_id}, {"_id": ObjectId(event_id) if ObjectId.is_valid(event_id) else None}]
    })
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SECURITY_EVENT_NOT_FOUND")

    doc["_id"] = str(doc["_id"])
    return SecurityEventResponse(**doc)

# ==============================================================================
# SECURITY ALERTS ENDPOINTS
# ==============================================================================

@router.get("/alerts", response_model=SecurityAlertListResponse)
async def list_security_alerts(
    alert_status: Optional[str] = Query(None, alias="status"),
    severity: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    case_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve security alerts across the platform."""
    verify_security_view_permission(current_user)
    db = get_database()

    query: Dict[str, Any] = {}
    if alert_status:
        query["status"] = alert_status
    if severity:
        query["severity"] = severity
    if alert_type:
        query["alert_type"] = alert_type
    if case_id:
        query["case_id"] = case_id

    total = await db["security_alerts"].count_documents(query)
    open_count = await db["security_alerts"].count_documents({"status": SecurityAlertStatus.OPEN.value})

    cursor = db["security_alerts"].find(query).sort("timestamp", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)

    alerts = []
    for d in docs:
        d["_id"] = str(d["_id"])
        alerts.append(SecurityAlertResponse(**d))

    return SecurityAlertListResponse(
        total=total,
        open_count=open_count,
        alerts=alerts
    )

@router.get("/alerts/{alert_id}", response_model=SecurityAlertResponse)
async def get_security_alert(
    alert_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve security alert record."""
    verify_security_view_permission(current_user)
    db = get_database()

    doc = await db["security_alerts"].find_one({
        "$or": [{"alert_id": alert_id}, {"_id": ObjectId(alert_id) if ObjectId.is_valid(alert_id) else None}]
    })
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SECURITY_ALERT_NOT_FOUND")

    doc["_id"] = str(doc["_id"])
    return SecurityAlertResponse(**doc)

@router.patch("/alerts/{alert_id}/status", response_model=SecurityAlertResponse)
async def update_alert_status(
    alert_id: str,
    payload: AlertStatusUpdatePayload,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update security alert resolution status with notes."""
    verify_security_view_permission(current_user)
    db = get_database()

    doc = await db["security_alerts"].find_one({
        "$or": [{"alert_id": alert_id}, {"_id": ObjectId(alert_id) if ObjectId.is_valid(alert_id) else None}]
    })
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SECURITY_ALERT_NOT_FOUND")

    now = datetime.now(timezone.utc)
    updates: Dict[str, Any] = {
        "status": payload.status.value,
        "updated_at": now
    }
    if payload.notes:
        updates["resolution_notes"] = payload.notes
    if payload.status in (SecurityAlertStatus.RESOLVED, SecurityAlertStatus.DISMISSED):
        updates["resolved_by"] = current_user.get("name", "Investigator")
        updates["resolved_at"] = now

    await db["security_alerts"].update_one({"_id": doc["_id"]}, {"$set": updates})

    updated_doc = await db["security_alerts"].find_one({"_id": doc["_id"]})
    updated_doc["_id"] = str(updated_doc["_id"])
    return SecurityAlertResponse(**updated_doc)

@router.get("/stats", response_model=SecurityMetricsResponse)
async def get_security_statistics(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Summary counts of security alerts and unauthorized attempts."""
    verify_security_view_permission(current_user)
    db = get_database()

    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)

    open_alerts = await db["security_alerts"].count_documents({"status": SecurityAlertStatus.OPEN.value})
    total_alerts = await db["security_alerts"].count_documents({})

    unauthorized_attempts_24h = await db["security_events"].count_documents({
        "timestamp": {"$gte": day_ago},
        "event_type": {"$in": [
            "UNAUTHORIZED_ACCESS_ATTEMPT",
            "AUTHENTICATED_BUT_UNAUTHORIZED",
            "TAMPER_ATTEMPT"
        ]}
    })

    failed_logins_24h = await db["security_events"].count_documents({
        "timestamp": {"$gte": day_ago},
        "event_type": "FAILED_LOGIN"
    })

    critical_events_count = await db["security_events"].count_documents({
        "severity": "CRITICAL"
    })

    # Find distinct suspicious IPs with >= 2 security events
    pipeline = [
        {"$match": {"timestamp": {"$gte": day_ago}}},
        {"$group": {"_id": "$ip_address", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gte": 2}}},
        {"$limit": 10}
    ]
    ip_cursor = db["security_events"].aggregate(pipeline)
    suspicious_ips_docs = await ip_cursor.to_list(length=10)
    suspicious_ips = [d["_id"] for d in suspicious_ips_docs if d.get("_id")]

    return SecurityMetricsResponse(
        open_alerts=open_alerts,
        total_alerts=total_alerts,
        unauthorized_attempts_24h=unauthorized_attempts_24h,
        failed_logins_24h=failed_logins_24h,
        suspicious_ips=suspicious_ips,
        critical_events_count=critical_events_count
    )
