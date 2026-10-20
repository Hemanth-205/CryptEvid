import os
import re
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from bson import ObjectId
from app.core.config import settings
from app.core.database import get_database
from app.routers.auth import get_current_user
from app.core.rbac import is_admin, require_case_access, get_accessible_case_ids, can_view_all_cases
from app.models.user import UserRole
from app.models.evidence import (
    IntegrityStatus,
    CustodyAction,
    EvidenceResponse,
    EvidenceVerifyResponse,
    EvidenceStats,
    CustodyEventResponse
)
from app.repositories.case import CaseRepository
from app.repositories.evidence import EvidenceRepository
from app.repositories.evidence_metadata import EvidenceMetadataRepository
from app.repositories.audit import AuditRepository
from app.services.hash_service import HashService
from app.services.custody_service import ChainOfCustodyService
from app.services.metadata_service import MetadataExtractionService
from app.services.backup_service import EvidenceBackupService

router = APIRouter(tags=["evidence"])

def sanitize_filename(filename: str) -> str:
    """Sanitize user-provided filename to prevent path traversal and unsafe characters."""
    clean = os.path.basename(filename)
    clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', clean)
    return clean or "evidence_file"

def verify_storage_path(file_path: str):
    """Ensure the resolved storage path remains strictly inside the configured evidence root."""
    base = os.path.abspath(settings.EVIDENCE_STORAGE_DIR)
    target = os.path.abspath(file_path)
    if not target.startswith(base):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SECURITY_VIOLATION: Path traversal detected"
        )

# ==============================================================================
# CASE-SCOPED EVIDENCE ENDPOINTS
# ==============================================================================

@router.post("/cases/{case_id}/evidence", status_code=status.HTTP_201_CREATED)
async def upload_case_evidence(
    case_id: str,
    request: Request,
    file: UploadFile = File(...),
    source_device: str = Form("WEB_APP"),
    source_type: str = Form("MANUAL_UPLOAD"),
    description: str = Form(""),
    tags: str = Form(""),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Ingest evidence file into a forensic case.
    Calculates streaming SHA-256 hash, extracts metadata, safely stores file on disk,
    and creates the initial cryptographic chain-of-custody event.
    """
    if current_user.get("role") == UserRole.READONLY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="UNAUTHORIZED: Read-only accounts cannot upload evidence"
        )

    db = get_database()
    case_repo = CaseRepository(db)
    evidence_repo = EvidenceRepository(db)
    metadata_repo = EvidenceMetadataRepository(db)

    case = await case_repo.get_by_id(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CASE_NOT_FOUND: Target forensic case does not exist"
        )

    require_case_access(current_user, case)

    # 1. Prepare safe directory structure
    evidence_object_id = str(ObjectId())
    raw_filename = file.filename or "unknown_artifact"
    safe_filename = sanitize_filename(raw_filename)

    evidence_dir = os.path.join(settings.EVIDENCE_STORAGE_DIR, str(case["_id"]), evidence_object_id)
    verify_storage_path(evidence_dir)
    os.makedirs(evidence_dir, exist_ok=True)

    target_file_path = os.path.join(evidence_dir, safe_filename)
    verify_storage_path(target_file_path)

    # 2. Stream file to disk and calculate SHA-256 simultaneously in 64KB chunks
    hasher = hashlib.sha256()
    total_bytes = 0
    all_file_bytes = bytearray()

    with open(target_file_path, "wb") as f:
        while True:
            chunk = await file.read(64 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
            f.write(chunk)
            total_bytes += len(chunk)
            if total_bytes <= 15 * 1024 * 1024:  # Collect up to 15MB for in-memory metadata inspection
                all_file_bytes.extend(chunk)

    sha256_hash = hasher.hexdigest().lower()
    file_ext = os.path.splitext(safe_filename)[1].lstrip(".").lower()

    # 3. Extract technical metadata via MetadataExtractionService
    meta_status, attributes, lat, lon, meta_err = MetadataExtractionService.extract(
        safe_filename, bytes(all_file_bytes)
    )

    tag_list = [t.strip().upper() for t in tags.split(",") if t.strip()]

    # 4. Create metadata record
    metadata_doc = {
        "evidence_id": evidence_object_id,
        "case_id": str(case["_id"]),
        "original_filename": raw_filename,
        "file_size": total_bytes,
        "mime_type": file.content_type or "application/octet-stream",
        "file_extension": file_ext,
        "source_device": source_device,
        "source_type": source_type,
        "collector": current_user.get("name", "Investigator"),
        "collection_timestamp": datetime.now(timezone.utc),
        "description": description.strip(),
        "tags": tag_list,
        "latitude": lat,
        "longitude": lon,
        "metadata_status": meta_status,
        "extracted_attributes": attributes,
        "error_message": meta_err
    }
    saved_metadata = await metadata_repo.create(metadata_doc)

    # 5. Create evidence record with immutable SHA-256 baseline
    evidence_doc = {
        "_id": ObjectId(evidence_object_id),
        "case_id": str(case["_id"]),
        "original_filename": raw_filename,
        "stored_filename": safe_filename,
        "file_size": total_bytes,
        "mime_type": file.content_type or "application/octet-stream",
        "file_extension": file_ext,
        "storage_path": target_file_path,
        "source_device": source_device,
        "source_type": source_type,
        "collector_id": str(current_user["_id"]),
        "collector_name": current_user.get("name", "Investigator"),
        "collection_timestamp": datetime.now(timezone.utc),
        "sha256_hash": sha256_hash,
        "integrity_status": IntegrityStatus.VERIFIED.value,
        "last_verified_at": datetime.now(timezone.utc),
        "last_calculated_hash": sha256_hash,
        "metadata_id": saved_metadata["_id"],
        "description": description.strip(),
        "tags": tag_list,
        "metadata_status": meta_status,
        "extracted_attributes": attributes
    }
    saved_evidence = await evidence_repo.create(evidence_doc)

    # 6. Record initial Chain of Custody event
    client_ip = request.client.host if request.client else "127.0.0.1"
    await ChainOfCustodyService.record_event(
        db=db,
        evidence_id=evidence_object_id,
        case_id=str(case["_id"]),
        action=CustodyAction.EVIDENCE_UPLOADED.value,
        actor_id=str(current_user["_id"]),
        actor_name=current_user.get("name", "Investigator"),
        details=f"Evidence artifact '{raw_filename}' ({total_bytes} bytes) ingested into Case {case['case_number']}. Baseline SHA-256: {sha256_hash}",
        ip_address=client_ip,
        device_id=source_device
    )

    # 7. Create preserved original backup (immutable copy)
    try:
        await EvidenceBackupService.create_backup(
            db=db,
            evidence_id=evidence_object_id,
            case_id=str(case["_id"]),
            source_path=target_file_path,
            original_sha256=sha256_hash,
            created_by=str(current_user["_id"]),
            created_by_name=current_user.get("name", "Investigator"),
            original_filename=raw_filename,
            file_size=total_bytes,
            ip_address=client_ip,
            device_id=source_device
        )
    except Exception as e:
        # Log backup failure but do not block evidence ingestion
        print(f"[BACKUP_WARNING] Failed to create preserved original for {evidence_object_id}: {e}")

    return saved_evidence

@router.get("/cases/{case_id}/evidence")
async def list_case_evidence(case_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """List all evidence records assigned to a case container."""
    db = get_database()
    case_repo = CaseRepository(db)
    evidence_repo = EvidenceRepository(db)

    case = await case_repo.get_by_id(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    require_case_access(current_user, case)

    items = await evidence_repo.list_by_case(str(case["_id"]))
    return items

# ==============================================================================
# GLOBAL EVIDENCE VAULT ENDPOINTS
# ==============================================================================

@router.get("/evidence/stats", response_model=EvidenceStats)
async def get_evidence_stats(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieve real-time global evidence integrity metrics for dashboard."""
    db = get_database()
    evidence_repo = EvidenceRepository(db)
    allowed_case_ids = None
    if not can_view_all_cases(current_user):
        allowed_case_ids = await get_accessible_case_ids(db, current_user)
    return await evidence_repo.get_stats(allowed_case_ids=allowed_case_ids)

@router.get("/evidence")
async def list_all_evidence(
    search: Optional[str] = Query(None),
    integrity_status: Optional[str] = Query(None),
    case_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """List, search, and filter evidence items across the entire repository."""
    db = get_database()
    evidence_repo = EvidenceRepository(db)

    allowed_case_ids = None
    if not can_view_all_cases(current_user):
        allowed_case_ids = await get_accessible_case_ids(db, current_user)
        if case_id:
            if case_id not in allowed_case_ids:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to requested case evidence")
            allowed_case_ids = [case_id]

    items, total = await evidence_repo.list_all(
        search=search,
        integrity_status=integrity_status,
        case_id=case_id,
        skip=skip,
        limit=limit,
        allowed_case_ids=allowed_case_ids
    )
    return {
        "evidence": items,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.get("/evidence/{evidence_id}")
async def get_evidence(evidence_id: str, request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieve detailed evidence information and record view custody event."""
    db = get_database()
    evidence_repo = EvidenceRepository(db)

    evidence = await evidence_repo.get_by_id(evidence_id)
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EVIDENCE_NOT_FOUND")

    if not can_view_all_cases(current_user):
        case_repo = CaseRepository(db)
        case = await case_repo.get_by_id(evidence["case_id"])
        if not case:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated case not found")
        require_case_access(current_user, case)

    # Record custody view event
    client_ip = request.client.host if request.client else "127.0.0.1"
    await ChainOfCustodyService.record_event(
        db=db,
        evidence_id=evidence_id,
        case_id=evidence["case_id"],
        action=CustodyAction.EVIDENCE_VIEWED.value,
        actor_id=str(current_user["_id"]),
        actor_name=current_user.get("name", "Investigator"),
        details=f"Evidence artifact viewed by investigator {current_user.get('name')}.",
        ip_address=client_ip
    )

    return evidence

@router.get("/evidence/{evidence_id}/download")
async def download_evidence(evidence_id: str, request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Securely download forensic evidence artifact and log chain-of-custody event."""
    db = get_database()
    evidence_repo = EvidenceRepository(db)

    evidence = await evidence_repo.get_by_id(evidence_id)
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EVIDENCE_NOT_FOUND")

    if not can_view_all_cases(current_user):
        case_repo = CaseRepository(db)
        case = await case_repo.get_by_id(evidence["case_id"])
        if not case:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated case not found")
        require_case_access(current_user, case)

    storage_path = evidence.get("storage_path")
    if not storage_path or not os.path.exists(storage_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Physical evidence file missing on disk")

    verify_storage_path(storage_path)

    # Record download event in Chain of Custody
    client_ip = request.client.host if request.client else "127.0.0.1"
    await ChainOfCustodyService.record_event(
        db=db,
        evidence_id=evidence_id,
        case_id=evidence["case_id"],
        action=CustodyAction.EVIDENCE_DOWNLOADED.value,
        actor_id=str(current_user["_id"]),
        actor_name=current_user.get("name", "Investigator"),
        details=f"Evidence file downloaded for offline examination by {current_user.get('name')}.",
        ip_address=client_ip
    )

    return FileResponse(
        path=storage_path,
        filename=evidence["original_filename"],
        media_type=evidence.get("mime_type", "application/octet-stream")
    )

@router.post("/evidence/{evidence_id}/verify", response_model=EvidenceVerifyResponse)
async def verify_evidence_integrity(
    evidence_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Recalculate evidence SHA-256 hash using streaming and compare against the baseline hash.
    If matching: VERIFIED.
    If mismatch: TAMPERED (triggers high-severity alert and preserves original hash).
    """
    if current_user.get("role") == UserRole.READONLY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="UNAUTHORIZED: Read-only accounts cannot trigger verification audits"
        )

    db = get_database()
    evidence_repo = EvidenceRepository(db)

    evidence = await evidence_repo.get_by_id(evidence_id)
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EVIDENCE_NOT_FOUND")

    if not is_admin(current_user):
        case_repo = CaseRepository(db)
        case = await case_repo.get_by_id(evidence["case_id"])
        if not case:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated case not found")
        require_case_access(current_user, case)

    storage_path = evidence.get("storage_path")
    if not storage_path or not os.path.exists(storage_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Physical evidence file missing from storage path"
        )

    verify_storage_path(storage_path)

    expected_hash = evidence.get("sha256_hash", "")
    is_match, calculated_hash = HashService.verify_sha256(storage_path, expected_hash)

    now = datetime.now(timezone.utc)
    client_ip = request.client.host if request.client else "127.0.0.1"

    if is_match:
        integrity_status = IntegrityStatus.VERIFIED
        message = "Cryptographic integrity verified. Evidence matches original baseline hash."
        custody_action = CustodyAction.EVIDENCE_VERIFIED.value
        details_msg = f"Integrity verification PASSED. Calculated SHA-256: {calculated_hash}"
    else:
        integrity_status = IntegrityStatus.TAMPERED
        message = f"CRITICAL SECURITY ALERT: Evidence has been TAMPERED with! Calculated hash ({calculated_hash}) does NOT match original baseline ({expected_hash})."
        custody_action = CustodyAction.EVIDENCE_INTEGRITY_FAILURE.value
        details_msg = f"TAMPER ALERT! Expected baseline: {expected_hash}, Recalculated hash: {calculated_hash}"

    # Update evidence integrity in database without overwriting original baseline hash
    await evidence_repo.update_integrity(
        evidence_id=evidence_id,
        integrity_status=integrity_status.value,
        calculated_hash=calculated_hash,
        verified_at=now
    )

    # Record custody event
    await ChainOfCustodyService.record_event(
        db=db,
        evidence_id=evidence_id,
        case_id=evidence["case_id"],
        action=custody_action,
        actor_id=str(current_user["_id"]),
        actor_name=current_user.get("name", "Investigator"),
        details=details_msg,
        ip_address=client_ip
    )

    # Backup-aware tamper detection: compare against preserved original
    backup_compared = False
    original_sha256_from_backup = None
    backup_id_result = None
    if not is_match:
        try:
            _, original_sha256_from_backup, backup_id_result = \
                await EvidenceBackupService.verify_evidence_against_original(
                    db=db,
                    evidence_id=evidence_id,
                    case_id=evidence["case_id"],
                    current_sha256=calculated_hash,
                    actor_id=str(current_user["_id"]),
                    actor_name=current_user.get("name", "Investigator"),
                    ip_address=client_ip,
                    device_id=evidence.get("source_device", "WEB_APP")
                )
            backup_compared = True
        except Exception as e:
            print(f"[BACKUP_TAMPER_CHECK_ERR] {e}")

    return EvidenceVerifyResponse(
        evidence_id=evidence_id,
        original_filename=evidence["original_filename"],
        stored_hash=expected_hash,
        calculated_hash=calculated_hash,
        integrity=integrity_status,
        verified_at=now,
        message=message
    )

@router.get("/evidence/{evidence_id}/custody")
async def get_evidence_custody_history(evidence_id: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Retrieve chronological Chain of Custody events for an evidence artifact
    with cryptographic hash chain validation.
    """
    db = get_database()
    evidence_repo = EvidenceRepository(db)

    evidence = await evidence_repo.get_by_id(evidence_id)
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EVIDENCE_NOT_FOUND")

    if not can_view_all_cases(current_user):
        case_repo = CaseRepository(db)
        case = await case_repo.get_by_id(evidence["case_id"])
        if not case:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated case not found")
        require_case_access(current_user, case)

    history = await ChainOfCustodyService.get_custody_history(db, evidence_id)
    return {
        "evidence_id": evidence_id,
        "original_filename": evidence.get("original_filename"),
        "sha256_hash": evidence.get("sha256_hash"),
        "total_events": len(history),
        "history": history
    }

@router.get("/custody")
async def get_all_custody_events(
    case_id: Optional[str] = Query(None),
    evidence_id: Optional[str] = Query(None),
    limit: int = Query(200, le=1000),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retrieve all Chain of Custody events across the platform with evidence & case details.
    """
    db = get_database()
    query: Dict[str, Any] = {}

    if not can_view_all_cases(current_user):
        allowed_case_ids = await get_accessible_case_ids(db, current_user)
        if case_id:
            if case_id not in allowed_case_ids:
                return {"total": 0, "events": []}
            query["case_id"] = case_id
        else:
            query["case_id"] = {"$in": allowed_case_ids}
    else:
        if case_id:
            query["case_id"] = case_id

    if evidence_id:
        query["evidence_id"] = evidence_id

    cursor = db["chain_of_custody"].find(query).sort("timestamp", -1).limit(limit)
    raw_events = await cursor.to_list(length=limit)

    ev_ids = list({d.get("evidence_id") for d in raw_events if d.get("evidence_id")})
    case_ids = list({d.get("case_id") for d in raw_events if d.get("case_id")})

    ev_map = {}
    if ev_ids:
        from bson import ObjectId
        ev_oids = [ObjectId(e) for e in ev_ids if ObjectId.is_valid(e)]
        ev_docs = await db["evidence"].find({"$or": [{"_id": {"$in": ev_oids}}, {"_id": {"$in": ev_ids}}]}).to_list(length=500)
        for ev in ev_docs:
            ev_map[str(ev["_id"])] = ev

    case_map = {}
    if case_ids:
        from bson import ObjectId
        c_oids = [ObjectId(c) for c in case_ids if ObjectId.is_valid(c)]
        case_docs = await db["cases"].find({"$or": [{"_id": {"$in": c_oids}}, {"_id": {"$in": case_ids}}]}).to_list(length=500)
        for c in case_docs:
            case_map[str(c["_id"])] = c

    results = []
    for d in raw_events:
        eid = str(d.get("evidence_id", ""))
        cid = str(d.get("case_id", ""))
        ev = ev_map.get(eid)
        case_doc = case_map.get(cid)
        results.append({
            "_id": str(d["_id"]),
            "evidence_id": eid,
            "case_id": cid,
            "case_number": case_doc.get("case_number", "CASE") if case_doc else "N/A",
            "evidence_name": ev.get("original_filename", "Evidence File") if ev else "Evidence File",
            "evidence_hash": ev.get("sha256_hash", "") if ev else "",
            "action": d.get("action", "CUSTODY_EVENT"),
            "actor_id": str(d.get("actor_id", "")),
            "actor_name": d.get("actor_name", "Investigator"),
            "details": d.get("details", ""),
            "timestamp": d.get("timestamp"),
            "event_hash": d.get("event_hash", ""),
            "previous_hash": d.get("previous_hash", ""),
            "ip_address": d.get("ip_address", "127.0.0.1"),
            "device_id": d.get("device_id", "WEB_APP")
        })

    return {
        "total": len(results),
        "events": results
    }
