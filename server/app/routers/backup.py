"""
Backup Router
=============
RBAC-enforced endpoints for accessing and verifying preserved original evidence backups.

Access Control:
- ADMIN: Full backup management (view, verify, download)
- INVESTIGATOR: View backup metadata + verify integrity for permitted cases
- READONLY: DENIED — no backup access
"""

import os
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import FileResponse
from typing import Dict, Any, List

from app.core.database import get_database
from app.routers.auth import get_current_user
from app.core.rbac import is_admin, require_case_access
from app.models.user import UserRole
from app.models.backup import BackupResponse, BackupListResponse, BackupIntegrityResponse
from app.models.evidence import CustodyAction
from app.repositories.backup import BackupRepository
from app.repositories.case import CaseRepository
from app.repositories.evidence import EvidenceRepository
from app.repositories.audit import AuditRepository
from app.services.backup_service import EvidenceBackupService
from app.services.custody_service import ChainOfCustodyService

router = APIRouter(tags=["backup"])


def _require_backup_view(current_user: Dict[str, Any]) -> None:
    """Enforce: ADMIN or INVESTIGATOR only. READONLY is denied."""
    role = current_user.get("role")
    if role not in (UserRole.ADMIN, UserRole.INVESTIGATOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="BACKUP_ACCESS_DENIED: Backup information is restricted to authorized investigators."
        )


def _require_admin(current_user: Dict[str, Any]) -> None:
    """Enforce: ADMIN only."""
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ADMIN_ONLY: Only administrators can perform this backup operation."
        )


# ==============================================================================
# GET BACKUP INFO FOR EVIDENCE
# ==============================================================================

@router.get("/evidence/{evidence_id}/backup", response_model=BackupResponse)
async def get_evidence_backup(
    evidence_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retrieve preserved original backup metadata for an evidence item.
    Physical storage path is NEVER returned — only the logical storage reference.

    Access: ADMIN, INVESTIGATOR
    """
    _require_backup_view(current_user)

    db = get_database()
    evidence_repo = EvidenceRepository(db)

    # Verify evidence exists
    evidence = await evidence_repo.get_by_id(evidence_id)
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EVIDENCE_NOT_FOUND")

    # Access check on case
    if not is_admin(current_user):
        case_repo = CaseRepository(db)
        case = await case_repo.get_by_id(evidence["case_id"])
        if not case:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated case not found")
        require_case_access(current_user, case)

    client_ip = request.client.host if request.client else "127.0.0.1"
    backup = await EvidenceBackupService.get_backup_for_evidence(
        db=db,
        evidence_id=evidence_id,
        actor_id=str(current_user["_id"]),
        actor_name=current_user.get("name", "Investigator"),
        ip_address=client_ip
    )

    if not backup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BACKUP_NOT_FOUND: No preserved original backup exists for this evidence."
        )

    return backup


# ==============================================================================
# VERIFY BACKUP INTEGRITY
# ==============================================================================

@router.post("/evidence/{evidence_id}/backup/verify", response_model=BackupIntegrityResponse)
async def verify_backup_integrity(
    evidence_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Recalculate the backup file's own SHA-256 and compare against its stored hash.
    This verifies the BACKUP ITSELF has not been corrupted or tampered.

    If backup hash differs: BACKUP_INTEGRITY_FAILURE (CRITICAL security alert generated).

    Access: ADMIN, INVESTIGATOR
    """
    _require_backup_view(current_user)

    if current_user.get("role") == UserRole.READONLY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="UNAUTHORIZED: Read-only accounts cannot trigger verification."
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

    client_ip = request.client.host if request.client else "127.0.0.1"

    result = await EvidenceBackupService.verify_backup_integrity(
        db=db,
        evidence_id=evidence_id,
        actor_id=str(current_user["_id"]),
        actor_name=current_user.get("name", "Investigator"),
        ip_address=client_ip
    )

    return result


# ==============================================================================
# LIST BACKUPS FOR A CASE
# ==============================================================================

@router.get("/cases/{case_id}/backups", response_model=BackupListResponse)
async def list_case_backups(
    case_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List all preserved original backup records for a case.
    Physical paths are never included in the response.

    Access: ADMIN, INVESTIGATOR
    """
    _require_backup_view(current_user)

    db = get_database()

    # Verify case exists
    from bson import ObjectId
    case_doc = await db["cases"].find_one({
        "_id": ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
    })
    if not case_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CASE_NOT_FOUND")

    require_case_access(current_user, case_doc)

    backup_repo = BackupRepository(db)
    records = await backup_repo.list_by_case(str(case_doc["_id"]))

    backups = []
    for r in records:
        try:
            backups.append(BackupResponse(
                backup_id=r["backup_id"],
                evidence_id=r["evidence_id"],
                case_id=r["case_id"],
                version=r["version"],
                original_filename=r["original_filename"],
                storage_reference=r["storage_reference"],
                original_sha256=r["original_sha256"],
                backup_sha256=r["backup_sha256"],
                file_size=r["file_size"],
                created_at=r["created_at"],
                created_by=r["created_by"],
                created_by_name=r["created_by_name"],
                status=r["status"]
            ))
        except Exception:
            continue

    return BackupListResponse(
        case_id=case_id,
        total_backups=len(backups),
        backups=backups
    )


# ==============================================================================
# DOWNLOAD PRESERVED ORIGINAL (ADMIN ONLY)
# ==============================================================================

@router.get("/evidence/{evidence_id}/backup/download")
async def download_backup(
    evidence_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Download the preserved original evidence file.

    ADMIN ONLY — every download is fully audited with:
    - User, Login ID, Timestamp, IP, Device/Session, Evidence, Backup ID

    The physical path is resolved internally and never exposed.
    """
    # Access control: ADMIN or authorized investigator assigned to the case.
    # STRICT CONFIDENTIALITY: PORTAL_MANAGER and READONLY are strictly forbidden!
    role = str(current_user.get("role", "")).lower()
    if role in ("portal_manager", "portalmanager", "readonly", "court_auditor", "auditor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="BACKUP_ACCESS_DENIED: You are not authorized to download preserved evidence backups."
        )

    db = get_database()
    evidence_repo = EvidenceRepository(db)
    audit_repo = AuditRepository(db)
    backup_repo = BackupRepository(db)
    case_repo = CaseRepository(db)

    evidence = await evidence_repo.get_by_id(evidence_id)
    if not evidence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EVIDENCE_NOT_FOUND")

    if not is_admin(current_user):
        case = await case_repo.get_by_id(evidence["case_id"])
        if not case:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated case not found")
        require_case_access(current_user, case)

    # Get backup record (includes physical path)
    record = await backup_repo.get_by_evidence_id(evidence_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BACKUP_NOT_FOUND: No verified original backup exists for this evidence artifact."
        )

    storage_path = record.get("storage_path", "")
    if not storage_path or not os.path.exists(storage_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BACKUP_FILE_MISSING: Physical backup file not found on storage vault."
        )

    # Verify backup integrity before serving - prevent serving corrupted backup
    import hashlib
    hasher = hashlib.sha256()
    with open(storage_path, "rb") as bf:
        while chunk := bf.read(64 * 1024):
            hasher.update(chunk)
    actual_backup_hash = hasher.hexdigest().lower()
    expected_backup_hash = (record.get("backup_sha256") or record.get("original_sha256", "")).lower()
    if expected_backup_hash and actual_backup_hash != expected_backup_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="BACKUP_CORRUPTED: Preserved original backup integrity check failed. The backup file is corrupted."
        )

    client_ip = request.client.host if request.client else "127.0.0.1"
    backup_id = record["backup_id"]
    user_agent = request.headers.get("user-agent", "UNKNOWN")

    # Record in Chain of Custody (BACKUP_DOWNLOADED)
    await ChainOfCustodyService.record_event(
        db=db,
        evidence_id=evidence_id,
        case_id=evidence["case_id"],
        action=CustodyAction.BACKUP_DOWNLOADED.value,
        actor_id=str(current_user["_id"]),
        actor_name=current_user.get("name", "Administrator"),
        details=(
            f"Preserved original downloaded by ADMIN. "
            f"Backup ID: {backup_id}. "
            f"IP: {client_ip}. "
            f"User: {current_user.get('name')}."
        ),
        ip_address=client_ip
    )

    # Record in audit_logs with full forensic context
    await audit_repo.create_log(
        user_id=current_user["_id"],
        action="backup_download",
        ip_address=client_ip,
        user_agent=user_agent,
        details=(
            f"[BACKUP DOWNLOAD] Evidence: {evidence_id}. "
            f"Backup ID: {backup_id}. "
            f"User: {current_user.get('name')} ({current_user.get('email')}). "
            f"IP: {client_ip}. "
            f"Device/User-Agent: {user_agent[:120]}."
        )
    )

    return FileResponse(
        path=storage_path,
        filename=f"PRESERVED_ORIGINAL_{record['original_filename']}",
        media_type=evidence.get("mime_type", "application/octet-stream")
    )
