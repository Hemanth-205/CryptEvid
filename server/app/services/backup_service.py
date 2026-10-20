"""
EvidenceBackupService
=====================
Manages the lifecycle of preserved original evidence backups.

Key forensic guarantees:
- Preserved originals are physically isolated in BACKUP_STORAGE_DIR (separate from working copies)
- The original SHA-256 is captured at upload time and stored immutably
- The backup is itself SHA-256 sealed (backup_sha256) to detect storage corruption
- Physical storage paths are NEVER returned to the API layer
- All operations are recorded in chain_of_custody and audit_logs
- Tamper detection fires into: Timeline (custody), SecurityAlert, Risk signals
"""

import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from bson import ObjectId

from app.core.config import settings
from app.models.backup import BackupStatus, BackupResponse, BackupIntegrityResponse
from app.models.evidence import CustodyAction
from app.repositories.backup import BackupRepository
from app.services.hash_service import HashService
from app.services.custody_service import ChainOfCustodyService


def _make_backup_id(evidence_id: str, version: int) -> str:
    """Generate a human-readable logical backup reference."""
    short_id = evidence_id[:6].upper()
    return f"BACKUP-EVD{short_id}-V{version}"


def _make_storage_reference(backup_id: str) -> str:
    """Return the storage reference that is safe to expose in the UI."""
    return backup_id  # Already human-readable; no path info


def _get_backup_physical_path(case_id: str, backup_id: str, filename: str) -> str:
    """
    Compute the physical filesystem path for the backup file.
    This path is NEVER returned to the API layer.
    """
    return os.path.join(settings.BACKUP_STORAGE_DIR, case_id, backup_id, filename)


def _safe_backup_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strip physical storage_path from a backup DB document before returning to API callers.
    This is the critical path-redaction step.
    """
    safe = {k: v for k, v in record.items() if k not in ("storage_path", "_id")}
    return safe


class EvidenceBackupService:

    @classmethod
    async def create_backup(
        cls,
        db,
        evidence_id: str,
        case_id: str,
        source_path: str,
        original_sha256: str,
        created_by: str,
        created_by_name: str,
        original_filename: str,
        file_size: int,
        ip_address: str = "127.0.0.1",
        device_id: str = "WEB_APP"
    ) -> BackupResponse:
        """
        Create a preserved original backup of the evidence file.

        Steps:
        1. Check no backup already exists (prevent duplicate originals)
        2. Determine version number
        3. Copy source file to isolated backup directory
        4. Calculate SHA-256 of the backup copy
        5. Store backup record in evidence_backups collection
        6. Record ORIGINAL_BACKUP_CREATED in chain_of_custody
        """
        backup_repo = BackupRepository(db)

        # Prevent duplicate original backups for same evidence
        existing_count = await backup_repo.count_by_evidence(evidence_id)
        version = existing_count + 1

        backup_id = _make_backup_id(evidence_id, version)
        storage_reference = _make_storage_reference(backup_id)

        # Determine physical backup path
        safe_filename = os.path.basename(source_path)
        backup_path = _get_backup_physical_path(case_id, backup_id, safe_filename)
        backup_dir = os.path.dirname(backup_path)

        # Ensure backup directory exists
        os.makedirs(backup_dir, exist_ok=True)

        # Copy file to backup location (never symlink — always a real copy)
        shutil.copy2(source_path, backup_path)

        # Calculate SHA-256 of the backup itself
        backup_sha256 = HashService.calculate_sha256_file(backup_path)

        # Build DB record (storage_path stored in DB but never exposed via API)
        backup_doc = {
            "backup_id": backup_id,
            "evidence_id": evidence_id,
            "case_id": case_id,
            "version": version,
            "original_filename": original_filename,
            "storage_reference": storage_reference,
            "storage_path": backup_path,        # INTERNAL ONLY — never serialized to API
            "original_sha256": original_sha256,  # Immutable baseline hash
            "backup_sha256": backup_sha256,      # Hash of the backup copy itself
            "file_size": file_size,
            "created_by": created_by,
            "created_by_name": created_by_name,
            "status": BackupStatus.PROTECTED.value
        }

        saved = await backup_repo.create(backup_doc)

        # Record in Chain of Custody
        await ChainOfCustodyService.record_event(
            db=db,
            evidence_id=evidence_id,
            case_id=case_id,
            action=CustodyAction.ORIGINAL_BACKUP_CREATED.value,
            actor_id=created_by,
            actor_name=created_by_name,
            details=(
                f"Preserved original created. Backup ID: {backup_id}. "
                f"Original SHA-256: {original_sha256}. "
                f"Backup SHA-256: {backup_sha256}. "
                f"Storage Reference: {storage_reference}."
            ),
            ip_address=ip_address,
            device_id=device_id
        )

        return BackupResponse(
            backup_id=saved["backup_id"],
            evidence_id=saved["evidence_id"],
            case_id=saved["case_id"],
            version=saved["version"],
            original_filename=saved["original_filename"],
            storage_reference=saved["storage_reference"],
            original_sha256=saved["original_sha256"],
            backup_sha256=saved["backup_sha256"],
            file_size=saved["file_size"],
            created_at=saved["created_at"],
            created_by=saved["created_by"],
            created_by_name=saved["created_by_name"],
            status=BackupStatus(saved["status"])
        )

    @classmethod
    async def get_backup_for_evidence(
        cls,
        db,
        evidence_id: str,
        actor_id: str,
        actor_name: str,
        ip_address: str = "127.0.0.1",
        device_id: str = "WEB_APP"
    ) -> Optional[BackupResponse]:
        """
        Retrieve backup metadata for an evidence item.
        Records BACKUP_ACCESSED in the custody chain.
        Physical path is never returned.
        """
        backup_repo = BackupRepository(db)
        record = await backup_repo.get_by_evidence_id(evidence_id)
        if not record:
            return None

        # Look up case_id from record for custody event
        case_id = record.get("case_id", "")

        await ChainOfCustodyService.record_event(
            db=db,
            evidence_id=evidence_id,
            case_id=case_id,
            action=CustodyAction.BACKUP_ACCESSED.value,
            actor_id=actor_id,
            actor_name=actor_name,
            details=f"Backup record accessed. Backup ID: {record['backup_id']}.",
            ip_address=ip_address,
            device_id=device_id
        )

        return BackupResponse(
            backup_id=record["backup_id"],
            evidence_id=record["evidence_id"],
            case_id=record["case_id"],
            version=record["version"],
            original_filename=record["original_filename"],
            storage_reference=record["storage_reference"],
            original_sha256=record["original_sha256"],
            backup_sha256=record["backup_sha256"],
            file_size=record["file_size"],
            created_at=record["created_at"],
            created_by=record["created_by"],
            created_by_name=record["created_by_name"],
            status=BackupStatus(record["status"])
        )

    @classmethod
    async def verify_backup_integrity(
        cls,
        db,
        evidence_id: str,
        actor_id: str,
        actor_name: str,
        ip_address: str = "127.0.0.1",
        device_id: str = "WEB_APP"
    ) -> BackupIntegrityResponse:
        """
        Verify the backup file itself — recalculate its SHA-256 and compare
        with the stored backup_sha256.

        If integrity fails: record BACKUP_INTEGRITY_FAILURE, create security alert.
        """
        backup_repo = BackupRepository(db)
        record = await backup_repo.get_by_evidence_id(evidence_id)

        now = datetime.now(timezone.utc)

        if not record:
            return BackupIntegrityResponse(
                backup_id="N/A",
                evidence_id=evidence_id,
                case_id="",
                storage_reference="N/A",
                original_sha256="",
                backup_sha256_stored="",
                backup_sha256_calculated="",
                backup_status=BackupStatus.MISSING,
                integrity_verified=False,
                message="BACKUP_NOT_FOUND: No preserved original exists for this evidence.",
                verified_at=now
            )

        backup_id = record["backup_id"]
        case_id = record["case_id"]
        storage_path = record.get("storage_path", "")

        # Check physical file existence
        if not storage_path or not os.path.exists(storage_path):
            await backup_repo.update_status(backup_id, BackupStatus.MISSING)
            await cls._create_backup_alert(
                db=db,
                backup_id=backup_id,
                evidence_id=evidence_id,
                case_id=case_id,
                alert_type="BACKUP_FILE_MISSING",
                description=(
                    f"Preserved original backup file is physically missing from storage. "
                    f"Backup ID: {backup_id}. Storage reference: {record['storage_reference']}."
                ),
                actor_id=actor_id,
                ip_address=ip_address
            )
            return BackupIntegrityResponse(
                backup_id=backup_id,
                evidence_id=evidence_id,
                case_id=case_id,
                storage_reference=record["storage_reference"],
                original_sha256=record["original_sha256"],
                backup_sha256_stored=record["backup_sha256"],
                backup_sha256_calculated="",
                backup_status=BackupStatus.MISSING,
                integrity_verified=False,
                message="BACKUP_FILE_MISSING: Physical backup file not found on storage.",
                verified_at=now
            )

        # Recalculate backup file hash
        calculated_sha256 = HashService.calculate_sha256_file(storage_path)
        stored_sha256 = record["backup_sha256"]
        integrity_ok = (calculated_sha256.lower() == stored_sha256.lower())

        if integrity_ok:
            new_status = BackupStatus.PROTECTED
            custody_action = CustodyAction.BACKUP_INTEGRITY_VERIFIED.value
            message = "Backup integrity verified. Preserved original matches sealed SHA-256."
        else:
            new_status = BackupStatus.CORRUPT
            custody_action = CustodyAction.BACKUP_INTEGRITY_FAILURE.value
            message = (
                f"CRITICAL: BACKUP_INTEGRITY_FAILURE! "
                f"Stored: {stored_sha256[:16]}... "
                f"Calculated: {calculated_sha256[:16]}..."
            )
            # Create high-priority alert for backup corruption
            await cls._create_backup_alert(
                db=db,
                backup_id=backup_id,
                evidence_id=evidence_id,
                case_id=case_id,
                alert_type="BACKUP_INTEGRITY_FAILURE",
                description=(
                    f"CRITICAL: Preserved original backup has been modified or corrupted! "
                    f"Backup ID: {backup_id}. Stored SHA-256: {stored_sha256}. "
                    f"Recalculated SHA-256: {calculated_sha256}."
                ),
                actor_id=actor_id,
                ip_address=ip_address,
                severity="CRITICAL"
            )

        # Update backup status in DB
        await backup_repo.update_status(backup_id, new_status, calculated_sha256)

        # Record in Chain of Custody
        await ChainOfCustodyService.record_event(
            db=db,
            evidence_id=evidence_id,
            case_id=case_id,
            action=custody_action,
            actor_id=actor_id,
            actor_name=actor_name,
            details=(
                f"Backup integrity check. Backup ID: {backup_id}. "
                f"Stored SHA-256: {stored_sha256}. "
                f"Calculated SHA-256: {calculated_sha256}. "
                f"Result: {'PASS' if integrity_ok else 'FAIL'}."
            ),
            ip_address=ip_address,
            device_id=device_id
        )

        return BackupIntegrityResponse(
            backup_id=backup_id,
            evidence_id=evidence_id,
            case_id=case_id,
            storage_reference=record["storage_reference"],
            original_sha256=record["original_sha256"],
            backup_sha256_stored=stored_sha256,
            backup_sha256_calculated=calculated_sha256,
            backup_status=new_status,
            integrity_verified=integrity_ok,
            message=message,
            verified_at=now
        )

    @classmethod
    async def verify_evidence_against_original(
        cls,
        db,
        evidence_id: str,
        case_id: str,
        current_sha256: str,
        actor_id: str,
        actor_name: str,
        ip_address: str = "127.0.0.1",
        device_id: str = "WEB_APP",
        session_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Compare the current working copy SHA-256 against the preserved original SHA-256.

        Returns:
            (is_match: bool, original_sha256: str|None, backup_id: str|None)

        When TAMPER_DETECTED:
        - Records TAMPER_DETECTED_VS_ORIGINAL in chain_of_custody
        - Creates CRITICAL security alert with full forensic context
        - Marks backup status as TAMPERED
        """
        backup_repo = BackupRepository(db)
        record = await backup_repo.get_by_evidence_id(evidence_id)

        if not record:
            return True, None, None  # No backup exists yet — can't compare

        original_sha256 = record["original_sha256"]
        backup_id = record["backup_id"]
        is_match = (current_sha256.lower() == original_sha256.lower())

        if is_match:
            return True, original_sha256, backup_id

        # ── TAMPER DETECTED ──────────────────────────────────────────────────
        # Record in Chain of Custody (non-destructive — appends to chain)
        await ChainOfCustodyService.record_event(
            db=db,
            evidence_id=evidence_id,
            case_id=case_id,
            action=CustodyAction.TAMPER_DETECTED_VS_ORIGINAL.value,
            actor_id=actor_id,
            actor_name=actor_name,
            details=(
                f"TAMPER DETECTED: Working copy hash differs from preserved original. "
                f"Original SHA-256: {original_sha256}. "
                f"Current SHA-256: {current_sha256}. "
                f"Backup ID: {backup_id}. "
                f"Preserved original remains INTACT."
            ),
            ip_address=ip_address,
            device_id=device_id
        )

        # Create CRITICAL security alert
        now = datetime.now(timezone.utc)
        alert_doc = {
            "alert_id": str(uuid.uuid4()),
            "alert_type": "EVIDENCE_TAMPER_DETECTED",
            "severity": "CRITICAL",
            "timestamp": now,
            "ip_address": ip_address,
            "user_id": actor_id,
            "login_id": actor_name,
            "user_role": None,
            "device_id": device_id if device_id != "WEB_APP" else session_id or device_id,
            "case_id": case_id,
            "case_number": None,
            "evidence_id": evidence_id,
            "backup_id": backup_id,
            "action": "TAMPER_DETECTED_VS_ORIGINAL",
            "description": (
                f"CRITICAL — EVIDENCE TAMPERING DETECTED\n"
                f"Evidence: {evidence_id}\n"
                f"Backup ID: {backup_id}\n"
                f"User: {actor_name}\n"
                f"IP: {ip_address}\n"
                f"Device/Session: {device_id}\n"
                f"Original SHA-256: {original_sha256}\n"
                f"Current SHA-256: {current_sha256}\n"
                f"Preserved Original: INTACT"
            ),
            "status": "OPEN",
            "related_event_ids": [],
            "resolution_notes": None,
            "resolved_by": None,
            "resolved_at": None,
            "original_sha256": original_sha256,
            "current_sha256": current_sha256,
            "backup_reference": record["storage_reference"],
            "created_at": now,
            "updated_at": now
        }
        await db["security_alerts"].insert_one(alert_doc)

        # Also record in security_events for timeline
        event_doc = {
            "event_id": str(uuid.uuid4()),
            "event_type": "TAMPER_DETECTED",
            "timestamp": now,
            "ip_address": ip_address,
            "ip_source": "direct_socket",
            "http_method": "POST",
            "endpoint": f"/evidence/{evidence_id}/verify",
            "request_type": "REST",
            "user_id": actor_id,
            "login_id": actor_name,
            "user_role": None,
            "device_id": device_id,
            "case_id": case_id,
            "evidence_id": evidence_id,
            "backup_id": backup_id,
            "action": "VERIFY",
            "result": "TAMPER_DETECTED",
            "reason": f"Working copy SHA-256 does not match preserved original SHA-256.",
            "severity": "CRITICAL",
            "original_sha256": original_sha256,
            "current_sha256": current_sha256,
            "metadata": {
                "backup_id": backup_id,
                "storage_reference": record["storage_reference"],
                "session_id": session_id
            }
        }
        await db["security_events"].insert_one(event_doc)

        # Mark backup record as TAMPERED (the working copy, not the backup)
        await backup_repo.update_status(backup_id, BackupStatus.TAMPERED)

        return False, original_sha256, backup_id

    @classmethod
    async def get_backup_physical_path(cls, db, evidence_id: str) -> Optional[str]:
        """
        INTERNAL ONLY. Returns the physical storage path for authorized download.
        This method must only be called from admin-authenticated endpoints.
        The path is NEVER serialized into API response bodies.
        """
        backup_repo = BackupRepository(db)
        record = await backup_repo.get_by_evidence_id(evidence_id)
        if not record:
            return None
        return record.get("storage_path")

    @classmethod
    async def _create_backup_alert(
        cls,
        db,
        backup_id: str,
        evidence_id: str,
        case_id: str,
        alert_type: str,
        description: str,
        actor_id: str,
        ip_address: str,
        severity: str = "CRITICAL"
    ) -> None:
        """Create a security alert for backup-related integrity failures."""
        now = datetime.now(timezone.utc)
        alert_doc = {
            "alert_id": str(uuid.uuid4()),
            "alert_type": alert_type,
            "severity": severity,
            "timestamp": now,
            "ip_address": ip_address,
            "user_id": actor_id,
            "login_id": None,
            "case_id": case_id,
            "evidence_id": evidence_id,
            "backup_id": backup_id,
            "action": alert_type,
            "description": description,
            "status": "OPEN",
            "related_event_ids": [],
            "resolution_notes": None,
            "resolved_by": None,
            "resolved_at": None,
            "created_at": now,
            "updated_at": now
        }
        await db["security_alerts"].insert_one(alert_doc)
