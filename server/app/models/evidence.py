from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

class IntegrityStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    TAMPERED = "TAMPERED"
    INTEGRITY_MISMATCH = "INTEGRITY_MISMATCH"
    UNDER_INVESTIGATION = "UNDER_INVESTIGATION"

class CustodyAction(str, Enum):
    EVIDENCE_COLLECTED = "EVIDENCE_COLLECTED"
    EVIDENCE_UPLOADED = "EVIDENCE_UPLOADED"
    EVIDENCE_VIEWED = "EVIDENCE_VIEWED"
    EVIDENCE_DOWNLOADED = "EVIDENCE_DOWNLOADED"
    EVIDENCE_VERIFIED = "EVIDENCE_VERIFIED"
    EVIDENCE_INTEGRITY_FAILURE = "EVIDENCE_INTEGRITY_FAILURE"
    EVIDENCE_METADATA_UPDATED = "EVIDENCE_METADATA_UPDATED"
    EVIDENCE_ANALYZED = "EVIDENCE_ANALYZED"
    # Backup & Tamper Detection actions
    ORIGINAL_BACKUP_CREATED = "ORIGINAL_BACKUP_CREATED"
    BACKUP_INTEGRITY_VERIFIED = "BACKUP_INTEGRITY_VERIFIED"
    BACKUP_INTEGRITY_FAILURE = "BACKUP_INTEGRITY_FAILURE"
    TAMPER_DETECTED_VS_ORIGINAL = "TAMPER_DETECTED_VS_ORIGINAL"
    BACKUP_DOWNLOADED = "BACKUP_DOWNLOADED"
    BACKUP_ACCESSED = "BACKUP_ACCESSED"
    # Versioning & Intelligence actions
    AUTHORIZED_MODIFICATION = "AUTHORIZED_MODIFICATION"
    TAMPER_CONFIRMED = "TAMPER_CONFIRMED"
    INTEGRITY_DISCREPANCY_FLAGGED = "INTEGRITY_DISCREPANCY_FLAGGED"
    VERSION_PRESERVED = "VERSION_PRESERVED"

class EvidenceResponse(BaseModel):
    id: str = Field(..., alias="_id")
    case_id: str
    case_number: Optional[str] = None
    case_title: Optional[str] = None
    original_filename: str
    file_size: int
    mime_type: str
    file_extension: str
    source_device: str
    source_type: str
    collector_id: str
    collector_name: str
    collection_timestamp: datetime
    created_at: datetime
    sha256_hash: str
    original_sha256_hash: Optional[str] = None
    version: Optional[int] = 1
    version_history: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    tamper_details: Optional[Dict[str, Any]] = None
    has_original_backup: Optional[bool] = False
    integrity_status: IntegrityStatus
    last_verified_at: Optional[datetime] = None
    last_calculated_hash: Optional[str] = None
    metadata_id: Optional[str] = None
    description: Optional[str] = ""
    tags: List[str] = Field(default_factory=list)
    metadata_status: Optional[str] = None
    extracted_attributes: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class AuthorizedModifyRequest(BaseModel):
    reason: str
    notes: Optional[str] = ""

class ConfirmTamperRequest(BaseModel):
    reason: Optional[str] = "Forensic inspection confirmed unauthorized byte mutation"
    attributed_actor: Optional[str] = None
    attacker_attribution: Optional[str] = None
    investigation_notes: Optional[str] = ""
    tamper_method: Optional[str] = None

class EvidenceVerifyResponse(BaseModel):
    evidence_id: str
    original_filename: str
    stored_hash: str
    calculated_hash: str
    integrity: IntegrityStatus
    verified_at: datetime
    message: str
    has_original_backup: Optional[bool] = False
    original_sha256_hash: Optional[str] = None

class EvidenceStats(BaseModel):
    total_evidence: int
    verified_evidence: int
    tampered_evidence: int
    pending_evidence: int
    integrity_rate: float

class CustodyEventResponse(BaseModel):
    id: str = Field(..., alias="_id")
    event_id: str
    evidence_id: str
    case_id: str
    action: CustodyAction
    actor_id: str
    actor_name: str
    timestamp: datetime
    ip_address: str
    device_id: str
    previous_hash: str
    event_hash: str
    details: str
    is_chain_valid: Optional[bool] = True

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
