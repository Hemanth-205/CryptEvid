from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId
from app.core.database import get_database
from app.routers.auth import get_current_user
from app.core.rbac import is_admin, require_case_access, can_view_all_cases
from app.models.user import UserRole
from app.models.event import (
    ForensicEventCreate,
    ForensicEventUpdate,
    ForensicEventResponse,
    TimelineResponse,
    TimelineStats
)
from app.repositories.case import CaseRepository
from app.repositories.event import EventRepository
from app.repositories.audit import AuditRepository
from app.services.timeline_service import TimelineService

router = APIRouter(tags=["events"])

@router.post("/cases/{case_id}/events", response_model=ForensicEventResponse, status_code=status.HTTP_201_CREATED)
async def create_case_event(
    case_id: str,
    payload: ForensicEventCreate,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a forensic event manually associated with a case.
    Enforces authorization and records an immutable audit log.
    """
    if current_user.get("role") == UserRole.READONLY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="UNAUTHORIZED: Read-only accounts cannot record forensic events"
        )

    db = get_database()
    case_repo = CaseRepository(db)
    event_repo = EventRepository(db)
    audit_repo = AuditRepository(db)

    case = await case_repo.get_by_id(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CASE_NOT_FOUND")

    require_case_access(current_user, case)

    event_data = payload.model_dump()
    event_data["case_id"] = str(case["_id"])
    event_data["created_by"] = str(current_user["_id"])
    if not event_data.get("actor_name"):
        event_data["actor_name"] = current_user.get("name", "Investigator")
    if not event_data.get("actor_id"):
        event_data["actor_id"] = str(current_user["_id"])
    event_data["is_system_generated"] = False

    created = await event_repo.create(event_data)

    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "FastAPI-Client")
    await audit_repo.create_log(
        user_id=str(current_user["_id"]),
        action="FORENSIC_EVENT_CREATED",
        ip_address=client_ip,
        user_agent=user_agent,
        device_id=payload.device_id or "INVESTIGATOR_WORKSTATION",
        case_id=str(case["_id"]),
        details=f"Created forensic event '{created['title']}' (Type: {created['event_type']}, Severity: {created['severity']})"
    )

    return created

@router.get("/cases/{case_id}/events", response_model=List[ForensicEventResponse])
async def list_case_events(
    case_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """List manual & stored forensic events for a case."""
    db = get_database()
    case_repo = CaseRepository(db)
    event_repo = EventRepository(db)

    case = await case_repo.get_by_id(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CASE_NOT_FOUND")

    require_case_access(current_user, case)

    events = await event_repo.list_by_case(
        case_id=str(case["_id"]),
        sort_field="event_time",
        sort_order=1,
        skip=skip,
        limit=limit
    )
    return events

@router.get("/cases/{case_id}/timeline", response_model=TimelineResponse)
async def get_case_timeline(
    case_id: str,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    evidence_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generate unified, multi-source chronological forensic timeline for a case.
    Correlates manual forensic events, evidence uploads, custody audits, and metadata timestamps.
    """
    db = get_database()
    case_repo = CaseRepository(db)

    case = await case_repo.get_by_id(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CASE_NOT_FOUND")

    require_case_access(current_user, case)

    timeline_events, total = await TimelineService.build_case_timeline(
        db=db,
        case_id=str(case["_id"]),
        start_time=start_time,
        end_time=end_time,
        event_type=event_type,
        severity=severity,
        source_type=source_type,
        evidence_id=evidence_id,
        search=search,
        order=order,
        limit=limit,
        skip=skip
    )

    return {
        "case_id": str(case["_id"]),
        "total_events": total,
        "returned_events": len(timeline_events),
        "start_filter": start_time,
        "end_filter": end_time,
        "events": timeline_events
    }

@router.get("/cases/{case_id}/timeline/stats", response_model=TimelineStats)
async def get_timeline_stats(case_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieve statistical summary and breakdown of a case timeline."""
    db = get_database()
    case_repo = CaseRepository(db)

    case = await case_repo.get_by_id(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CASE_NOT_FOUND")

    require_case_access(current_user, case)

    return await TimelineService.get_timeline_stats(db, case_id=str(case["_id"]))

@router.get("/events/{event_id}", response_model=ForensicEventResponse)
async def get_forensic_event(
    event_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve single forensic event by ID and record view audit."""
    db = get_database()
    event_repo = EventRepository(db)
    audit_repo = AuditRepository(db)

    event = await event_repo.get_by_id(event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EVENT_NOT_FOUND")

    if event.get("case_id") and not can_view_all_cases(current_user):
        case_repo = CaseRepository(db)
        case = await case_repo.get_by_id(event["case_id"])
        if case:
            require_case_access(current_user, case)

    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "FastAPI-Client")
    await audit_repo.create_log(
        user_id=str(current_user["_id"]),
        action="FORENSIC_EVENT_VIEWED",
        ip_address=client_ip,
        user_agent=user_agent,
        case_id=event.get("case_id"),
        details=f"Viewed forensic event '{event['title']}' ({event_id})"
    )

    return event

@router.put("/events/{event_id}", response_model=ForensicEventResponse)
async def update_forensic_event(
    event_id: str,
    payload: ForensicEventUpdate,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update an authorized manual forensic event.
    System-generated events cannot be edited.
    """
    if current_user.get("role") == UserRole.READONLY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="UNAUTHORIZED: Read-only accounts cannot modify forensic events"
        )

    db = get_database()
    event_repo = EventRepository(db)
    audit_repo = AuditRepository(db)

    existing = await event_repo.get_by_id(event_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EVENT_NOT_FOUND")

    if existing.get("case_id") and not is_admin(current_user):
        case_repo = CaseRepository(db)
        case = await case_repo.get_by_id(existing["case_id"])
        if case:
            require_case_access(current_user, case)

    # Protection: Cannot edit system-generated custody/audit events
    if existing.get("is_system_generated"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="IMMUTABLE_EVENT: System-generated forensic events cannot be altered"
        )

    # Permission check: Admin or event creator
    if current_user.get("role") != UserRole.ADMIN and existing.get("created_by") != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="UNAUTHORIZED: Only event author or administrator can edit this forensic event"
        )

    updated = await event_repo.update(event_id, payload.model_dump(exclude_unset=True))

    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "FastAPI-Client")
    await audit_repo.create_log(
        user_id=str(current_user["_id"]),
        action="FORENSIC_EVENT_UPDATED",
        ip_address=client_ip,
        user_agent=user_agent,
        case_id=existing.get("case_id"),
        details=f"Updated forensic event '{existing['title']}' ({event_id})"
    )

    return updated
