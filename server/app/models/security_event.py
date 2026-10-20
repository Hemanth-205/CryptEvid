from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from enum import Enum

class SecurityEventType(str, Enum):
    UNAUTHORIZED_ACCESS_ATTEMPT = "UNAUTHORIZED_ACCESS_ATTEMPT"
    AUTHENTICATED_BUT_UNAUTHORIZED = "AUTHENTICATED_BUT_UNAUTHORIZED"
    FAILED_LOGIN = "FAILED_LOGIN"
    REPEATED_LOGIN_FAILURE = "REPEATED_LOGIN_FAILURE"
    TAMPER_ATTEMPT = "TAMPER_ATTEMPT"
    TAMPER_DETECTED = "TAMPER_DETECTED"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"

class SecurityAlertStatus(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"

class SecurityAlertSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class SecurityEventResponse(BaseModel):
    id: str = Field(..., alias="_id")
    event_id: str
    event_type: SecurityEventType
    timestamp: datetime
    ip_address: str
    ip_source: str = "direct_socket"
    http_method: str
    endpoint: str
    request_type: str = "REST"
    user_id: Optional[str] = None
    login_id: Optional[str] = None
    user_role: Optional[str] = None
    user_agent: Optional[str] = None
    device_id: Optional[str] = None
    device_type: Optional[str] = None
    mac_address: Optional[str] = None
    case_id: Optional[str] = None
    case_number: Optional[str] = None
    evidence_id: Optional[str] = None
    evidence_name: Optional[str] = None
    action: str
    result: str = "BLOCKED"
    reason: str
    severity: SecurityAlertSeverity = SecurityAlertSeverity.MEDIUM
    metadata: Optional[Dict[str, Any]] = None

    model_config = {
        "populate_by_name": True,
        "json_encoders": {datetime: lambda dt: dt.isoformat()}
    }

class SecurityEventListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    events: List[SecurityEventResponse]

class SecurityAlertResponse(BaseModel):
    id: str = Field(..., alias="_id")
    alert_id: str
    alert_type: str
    severity: SecurityAlertSeverity
    timestamp: datetime
    ip_address: str
    user_id: Optional[str] = None
    login_id: Optional[str] = None
    user_role: Optional[str] = None
    device_id: Optional[str] = None
    case_id: Optional[str] = None
    case_number: Optional[str] = None
    evidence_id: Optional[str] = None
    action: str
    description: str
    status: SecurityAlertStatus = SecurityAlertStatus.OPEN
    related_event_ids: List[str] = Field(default_factory=list)
    resolution_notes: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "populate_by_name": True,
        "json_encoders": {datetime: lambda dt: dt.isoformat()}
    }

class SecurityAlertListResponse(BaseModel):
    total: int
    open_count: int
    alerts: List[SecurityAlertResponse]

class AlertStatusUpdatePayload(BaseModel):
    status: SecurityAlertStatus
    notes: Optional[str] = None

class SecurityMetricsResponse(BaseModel):
    open_alerts: int
    total_alerts: int
    unauthorized_attempts_24h: int
    failed_logins_24h: int
    suspicious_ips: List[str]
    critical_events_count: int
