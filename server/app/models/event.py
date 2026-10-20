from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

class EventType(str, Enum):
    LOGIN = "LOGIN"
    FILE_CREATED = "FILE_CREATED"
    FILE_MODIFIED = "FILE_MODIFIED"
    FILE_DELETED = "FILE_DELETED"
    FILE_ACCESSED = "FILE_ACCESSED"
    EMAIL_RECEIVED = "EMAIL_RECEIVED"
    EMAIL_SENT = "EMAIL_SENT"
    PROCESS_EXECUTED = "PROCESS_EXECUTED"
    USB_CONNECTED = "USB_CONNECTED"
    NETWORK_CONNECTION = "NETWORK_CONNECTION"
    MALWARE_DETECTED = "MALWARE_DETECTED"
    EVIDENCE_COLLECTED = "EVIDENCE_COLLECTED"
    EVIDENCE_UPLOADED = "EVIDENCE_UPLOADED"
    EVIDENCE_VERIFIED = "EVIDENCE_VERIFIED"
    EVIDENCE_TAMPERED = "EVIDENCE_TAMPERED"
    CASE_EVENT = "CASE_EVENT"
    INVESTIGATOR_NOTE = "INVESTIGATOR_NOTE"
    OTHER = "OTHER"

class EventSourceType(str, Enum):
    EVIDENCE_METADATA = "EVIDENCE_METADATA"
    AUDIT_LOG = "AUDIT_LOG"
    MANUAL_ENTRY = "MANUAL_ENTRY"
    SYSTEM = "SYSTEM"
    DEVICE = "DEVICE"
    AI_ANALYSIS = "AI_ANALYSIS"

class TimePrecision(str, Enum):
    EXACT = "EXACT"
    APPROXIMATE = "APPROXIMATE"
    UNKNOWN = "UNKNOWN"

class EventConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"

class EventSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ForensicEventCreate(BaseModel):
    event_type: EventType
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = ""
    event_time: Optional[datetime] = None
    event_time_end: Optional[datetime] = None
    time_precision: TimePrecision = TimePrecision.EXACT
    time_start: Optional[datetime] = None
    time_end: Optional[datetime] = None
    evidence_id: Optional[str] = None
    source: Optional[str] = "Investigator Observation"
    source_type: EventSourceType = EventSourceType.MANUAL_ENTRY
    source_reference: Optional[str] = None
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    device_id: Optional[str] = "INVESTIGATOR_WORKSTATION"
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    confidence: EventConfidence = EventConfidence.MEDIUM
    severity: EventSeverity = EventSeverity.INFO
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ForensicEventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[EventType] = None
    event_time: Optional[datetime] = None
    event_time_end: Optional[datetime] = None
    time_precision: Optional[TimePrecision] = None
    time_start: Optional[datetime] = None
    time_end: Optional[datetime] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    confidence: Optional[EventConfidence] = None
    severity: Optional[EventSeverity] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class ForensicEventResponse(BaseModel):
    id: str = Field(..., alias="_id")
    event_id: str
    case_id: str
    evidence_id: Optional[str] = None
    evidence_filename: Optional[str] = None
    event_type: str
    event_time: Optional[datetime] = None
    event_time_end: Optional[datetime] = None
    time_precision: str
    time_start: Optional[datetime] = None
    time_end: Optional[datetime] = None
    title: str
    description: str
    source: str
    source_type: str
    source_reference: Optional[str] = None
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    device_id: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    confidence: str
    severity: str
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_system_generated: bool = False
    created_at: datetime
    created_by: Optional[str] = None

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class TimelineResponse(BaseModel):
    case_id: str
    total_events: int
    returned_events: int
    start_filter: Optional[datetime] = None
    end_filter: Optional[datetime] = None
    events: List[ForensicEventResponse]

class TimelineStats(BaseModel):
    total_events: int
    critical_events: int
    high_events: int
    medium_events: int
    low_events: int
    info_events: int
    system_events: int
    manual_events: int
    first_event_time: Optional[datetime] = None
    last_event_time: Optional[datetime] = None
    event_types: Dict[str, int] = Field(default_factory=dict)
