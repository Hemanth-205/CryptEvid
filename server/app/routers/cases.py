from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, UploadFile, File, Form
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from bson import ObjectId
from app.core.database import get_database
from app.routers.auth import get_current_user
from app.models.user import UserRole
from app.models.case import (
    CaseCreate,
    CaseUpdate,
    CaseStatusUpdate,
    CaseStatus,
    AddCaseNotePayload,
    CaseResponse,
    CaseStats
)
from app.models.evidence_metadata import SourceType
from app.repositories.case import CaseRepository
from app.repositories.audit import AuditRepository
from app.repositories.evidence_metadata import EvidenceMetadataRepository
from app.services.metadata_service import MetadataExtractionService
from app.core.rbac import is_admin, require_case_access, can_user_access_case, can_view_all_cases

router = APIRouter(prefix="/cases", tags=["cases"])

def verify_case_modify_permission(current_user: Dict[str, Any], case: Dict[str, Any]):
    """Enforce role-based access for updating cases."""
    if is_admin(current_user):
        return
    if current_user.get("role") == UserRole.READONLY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="UNAUTHORIZED_CASE_ACCESS: Viewers have read-only access"
        )
    require_case_access(current_user, case, for_write=True)

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_case(payload: CaseCreate, request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Create a new forensic case."""
    if current_user.get("role") == UserRole.READONLY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="UNAUTHORIZED_CASE_ACCESS: Read-only accounts cannot create cases"
        )

    db = get_database()
    case_repo = CaseRepository(db)
    audit_repo = AuditRepository(db)

    now = datetime.now(timezone.utc)
    notes = []
    if payload.initial_note and payload.initial_note.strip():
        notes.append({
            "id": str(ObjectId()),
            "author_id": str(current_user["_id"]),
            "author_name": current_user.get("name", "Investigator"),
            "content": payload.initial_note.strip(),
            "timestamp": now
        })

    # If assigned_investigator is not specified, assign to the creator by default
    assigned = payload.assigned_investigator
    if not assigned and current_user.get("role") != UserRole.ADMIN:
        assigned = str(current_user["_id"])

    # Disallow assigning cases to Court Auditors
    if assigned:
        assignee = await db["users"].find_one({"_id": ObjectId(assigned) if ObjectId.is_valid(assigned) else assigned})
        if assignee and str(assignee.get("role")).lower() in ("readonly", "court_auditor", "auditor"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ASSIGNMENT_NOT_ALLOWED: Cases cannot be assigned to Court Auditors. Court Auditors are external observers with platform-wide read-only viewing permissions."
            )

    case_doc = {
        "title": payload.title.strip(),
        "description": payload.description.strip() if payload.description else "",
        "case_type": payload.case_type.value,
        "priority": payload.priority.value,
        "status": CaseStatus.OPEN.value,
        "created_by": str(current_user["_id"]),
        "assigned_investigator": assigned,
        "tags": [t.strip().upper() for t in payload.tags if t.strip()],
        "notes": notes
    }

    created_case = await case_repo.create(case_doc)

    # Log to audit trail
    await audit_repo.create_log(
        user_id=str(current_user["_id"]),
        action="CASE_CREATED",
        ip_address=request.client.host if request.client else "127.0.0.1",
        user_agent=request.headers.get("user-agent", "unknown"),
        case_id=created_case["_id"],
        details=f"Case {created_case['case_number']} ('{created_case['title']}') created with priority {created_case['priority']}."
    )

    return created_case

@router.get("/stats", response_model=CaseStats)
async def get_case_stats(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get aggregate forensic case statistics scoped to the user (Chief Investigator & Court Auditor see all)."""
    db = get_database()
    case_repo = CaseRepository(db)
    user_id = None if can_view_all_cases(current_user) else str(current_user["_id"])
    return await case_repo.get_stats(user_id=user_id)

@router.get("")
async def list_cases(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    case_type: Optional[str] = Query(None),
    assigned_investigator: Optional[str] = Query(None),
    include_archived: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List and search forensic cases with role-based scoping:
    - Chief Investigator (Admin) & Court Auditor (ReadOnly): View all cases.
    - Other users: View ONLY their own cases (created by or assigned to them).
    """
    db = get_database()
    case_repo = CaseRepository(db)
    user_id = None if can_view_all_cases(current_user) else str(current_user["_id"])
    cases, total = await case_repo.list_cases(
        search=search,
        status=status,
        priority=priority,
        case_type=case_type,
        assigned_investigator=assigned_investigator,
        include_archived=include_archived,
        user_id=user_id,
        skip=skip,
        limit=limit
    )
    return {
        "cases": cases,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.get("/{case_id}")
async def get_case(case_id: str, request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieve detailed forensic case record with RBAC enforcement."""
    db = get_database()
    case_repo = CaseRepository(db)
    audit_repo = AuditRepository(db)

    case = await case_repo.get_by_id(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CASE_NOT_FOUND: Forensic case does not exist"
        )

    # Enforce case access permission
    require_case_access(current_user, case)

    # Log viewing to audit trail
    await audit_repo.create_log(
        user_id=str(current_user["_id"]),
        action="CASE_VIEWED",
        ip_address=request.client.host if request.client else "127.0.0.1",
        user_agent=request.headers.get("user-agent", "unknown"),
        case_id=case["_id"],
        details=f"Case {case['case_number']} accessed by investigator {current_user.get('name')}."
    )

    return case

@router.put("/{case_id}")
async def update_case(
    case_id: str,
    payload: CaseUpdate,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Update case metadata and assignment."""
    db = get_database()
    case_repo = CaseRepository(db)
    audit_repo = AuditRepository(db)

    existing = await case_repo.get_by_id(case_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CASE_NOT_FOUND: Forensic case does not exist"
        )

    verify_case_modify_permission(current_user, existing)

    update_dict: Dict[str, Any] = {}
    if payload.title is not None:
        update_dict["title"] = payload.title.strip()
    if payload.description is not None:
        update_dict["description"] = payload.description.strip()
    if payload.case_type is not None:
        update_dict["case_type"] = payload.case_type.value
    if payload.priority is not None:
        update_dict["priority"] = payload.priority.value
    if payload.tags is not None:
        update_dict["tags"] = [t.strip().upper() for t in payload.tags if t.strip()]

    assigned_changed = False
    if payload.assigned_investigator is not None and payload.assigned_investigator != existing.get("assigned_investigator"):
        # Only Admins can reassign cases
        if current_user.get("role") != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="UNAUTHORIZED_CASE_ACCESS: Only administrators can reassign cases"
            )
        if payload.assigned_investigator:
            assignee = await db["users"].find_one({"_id": ObjectId(payload.assigned_investigator) if ObjectId.is_valid(payload.assigned_investigator) else payload.assigned_investigator})
            if assignee and str(assignee.get("role")).lower() in ("readonly", "court_auditor", "auditor"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ASSIGNMENT_NOT_ALLOWED: Cases cannot be assigned to Court Auditors. Court Auditors are external observers with platform-wide read-only viewing permissions."
                )
        update_dict["assigned_investigator"] = payload.assigned_investigator
        assigned_changed = True

    updated_case = await case_repo.update(case_id, update_dict)
    if not updated_case:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update case")

    # Audit logging
    if assigned_changed:
        await audit_repo.create_log(
            user_id=str(current_user["_id"]),
            action="CASE_ASSIGNED",
            ip_address=request.client.host if request.client else "127.0.0.1",
            user_agent=request.headers.get("user-agent", "unknown"),
            case_id=case_id,
            details=f"Case {existing['case_number']} reassigned to investigator {payload.assigned_investigator}."
        )

    await audit_repo.create_log(
        user_id=str(current_user["_id"]),
        action="CASE_UPDATED",
        ip_address=request.client.host if request.client else "127.0.0.1",
        user_agent=request.headers.get("user-agent", "unknown"),
        case_id=case_id,
        details=f"Case {existing['case_number']} updated by {current_user.get('name')}."
    )

    return updated_case

@router.patch("/{case_id}/status")
async def update_case_status(
    case_id: str,
    payload: CaseStatusUpdate,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Change the status of a forensic case."""
    db = get_database()
    case_repo = CaseRepository(db)
    audit_repo = AuditRepository(db)

    existing = await case_repo.get_by_id(case_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CASE_NOT_FOUND: Forensic case does not exist"
        )

    verify_case_modify_permission(current_user, existing)

    old_status = existing.get("status")
    new_status = payload.status.value

    updated_case = await case_repo.update_status(case_id, new_status)
    if not updated_case:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update status")

    await audit_repo.create_log(
        user_id=str(current_user["_id"]),
        action="CASE_STATUS_CHANGED",
        ip_address=request.client.host if request.client else "127.0.0.1",
        user_agent=request.headers.get("user-agent", "unknown"),
        case_id=case_id,
        details=f"Status of Case {existing['case_number']} changed from {old_status} to {new_status}."
    )

    return updated_case

@router.post("/{case_id}/notes")
async def add_case_note(
    case_id: str,
    payload: AddCaseNotePayload,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Append an investigation note to a case."""
    if current_user.get("role") == UserRole.READONLY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="UNAUTHORIZED_CASE_ACCESS: Read-only accounts cannot append notes"
        )

    db = get_database()
    case_repo = CaseRepository(db)
    audit_repo = AuditRepository(db)

    existing = await case_repo.get_by_id(case_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CASE_NOT_FOUND: Forensic case does not exist"
        )

    require_case_access(current_user, existing)

    note = {
        "id": str(ObjectId()),
        "author_id": str(current_user["_id"]),
        "author_name": current_user.get("name", "Investigator"),
        "content": payload.content.strip(),
        "timestamp": datetime.now(timezone.utc)
    }

    updated = await case_repo.add_note(case_id, note)

    await audit_repo.create_log(
        user_id=str(current_user["_id"]),
        action="CASE_UPDATED",
        ip_address=request.client.host if request.client else "127.0.0.1",
        user_agent=request.headers.get("user-agent", "unknown"),
        case_id=case_id,
        details=f"Investigation note added to Case {existing['case_number']}."
    )

    return updated

@router.delete("/{case_id}")
async def archive_case(
    case_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Soft-delete / Archive a forensic case (Admins only, preserves chain-of-custody)."""
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="UNAUTHORIZED_CASE_ACCESS: Only administrators can archive forensic cases"
        )

    db = get_database()
    case_repo = CaseRepository(db)
    audit_repo = AuditRepository(db)

    existing = await case_repo.get_by_id(case_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CASE_NOT_FOUND: Forensic case does not exist"
        )

    success = await case_repo.archive(case_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to archive case")

    await audit_repo.create_log(
        user_id=str(current_user["_id"]),
        action="CASE_ARCHIVED",
        ip_address=request.client.host if request.client else "127.0.0.1",
        user_agent=request.headers.get("user-agent", "unknown"),
        case_id=case_id,
        details=f"Case {existing['case_number']} ('{existing['title']}') was archived by admin {current_user.get('name')}."
    )

    return {"success": True, "message": f"Case {existing['case_number']} archived successfully"}

@router.post("/{case_id}/extract-metadata")
async def extract_evidence_metadata(
    case_id: str,
    file: UploadFile = File(...),
    source_device: str = Form("WEB_APP"),
    source_type: str = Form("MANUAL_UPLOAD"),
    description: str = Form(""),
    tags: str = Form(""),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Extract forensic metadata from an uploaded evidence file and attach to case.
    Does NOT calculate SHA-256 yet (scheduled for Milestone 3).
    """
    db = get_database()
    case_repo = CaseRepository(db)
    metadata_repo = EvidenceMetadataRepository(db)

    case = await case_repo.get_by_id(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CASE_NOT_FOUND: Forensic case does not exist"
        )

    require_case_access(current_user, case)

    file_bytes = await file.read()
    file_size = len(file_bytes)
    original_filename = file.filename or "unknown_file"
    file_extension = original_filename.split(".")[-1].lower() if "." in original_filename else ""

    # Call MetadataExtractionService
    status_str, attributes, latitude, longitude, error_msg = MetadataExtractionService.extract(
        original_filename, file_bytes
    )

    tag_list = [t.strip().upper() for t in tags.split(",") if t.strip()]

    # Construct metadata record
    metadata_doc = {
        "case_id": case["_id"],
        "original_filename": original_filename,
        "file_size": file_size,
        "mime_type": file.content_type or "application/octet-stream",
        "file_extension": file_extension,
        "source_device": source_device,
        "source_type": source_type,
        "collector": current_user.get("name", "Investigator"),
        "collection_timestamp": datetime.now(timezone.utc),
        "description": description,
        "tags": tag_list,
        "latitude": latitude,
        "longitude": longitude,
        "metadata_status": status_str,
        "extracted_attributes": attributes,
        "error_message": error_msg
    }

    saved_metadata = await metadata_repo.create(metadata_doc)
    return saved_metadata

@router.get("/{case_id}/evidence-metadata")
async def list_case_evidence_metadata(case_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """List all extracted metadata records associated with a case."""
    db = get_database()
    case_repo = CaseRepository(db)
    metadata_repo = EvidenceMetadataRepository(db)

    case = await case_repo.get_by_id(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CASE_NOT_FOUND: Forensic case does not exist"
        )

    require_case_access(current_user, case)

    records = await metadata_repo.list_by_case(case["_id"])
    return records

@router.post("/seed-demo", status_code=status.HTTP_201_CREATED)
async def seed_demo_case_endpoint(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Seed or ensure the baseline demo case with evidence, custody ledger, timeline, and report exists."""
    from seed_demo_case import seed_demo
    await seed_demo()
    return {"message": "Demo case successfully seeded or verified."}
