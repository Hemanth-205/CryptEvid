# pyrefly: ignore [missing-import]
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum
from datetime import datetime


class BackupStatus(str, Enum):
    PROTECTED = "PROTECTED"
    TAMPERED = "TAMPERED"
    MISSING = "MISSING"
    CORRUPT = "CORRUPT"


class BackupResponse(BaseModel):
    """
    Public-facing backup record.
    CRITICAL: storage_path (physical filesystem path) is NEVER included here.
    Only the logical storage_reference is exposed to authorized users.
    """
    backup_id: str
    evidence_id: str
    case_id: str
    version: int
    original_filename: str
    storage_reference: str          # Logical ID e.g. BACKUP-EVD001-V1
    original_sha256: str
    backup_sha256: str
    file_size: int
    created_at: datetime
    created_by: str
    created_by_name: str
    status: BackupStatus

    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat()}
    }


class BackupListResponse(BaseModel):
    evidence_id: Optional[str] = None
    case_id: Optional[str] = None
    total_backups: int
    backups: List[BackupResponse]


class BackupIntegrityResponse(BaseModel):
    """Result of verifying the backup itself (not the working copy)."""
    backup_id: str
    evidence_id: str
    case_id: str
    storage_reference: str
    original_sha256: str
    backup_sha256_stored: str
    backup_sha256_calculated: str
    backup_status: BackupStatus
    integrity_verified: bool
    message: str
    verified_at: datetime

    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat()}
    }


class EvidenceIntegrityResponse(BaseModel):
    """
    Combined working-copy vs original-backup comparison result.
    Returned by the verify endpoint when backup exists.
    """
    evidence_id: str
    original_filename: str
    original_sha256: str             # Immutable baseline from first upload
    current_sha256: str              # Freshly calculated from working copy
    stored_sha256: str               # The sha256_hash field on evidence record
    integrity_status: str            # VERIFIED | TAMPERED
    backup_id: Optional[str] = None
    backup_reference: Optional[str] = None
    backup_status: Optional[BackupStatus] = None
    message: str
    verified_at: datetime

    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat()}
    }
