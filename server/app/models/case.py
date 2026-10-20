from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

class CaseStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"

class CasePriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class CaseType(str, Enum):
    PHISHING = "PHISHING"
    MALWARE = "MALWARE"
    INSIDER_THREAT = "INSIDER_THREAT"
    DATA_BREACH = "DATA_BREACH"
    FINANCIAL_FRAUD = "FINANCIAL_FRAUD"
    FRAUD = "FRAUD"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    OTHER = "OTHER"

class CaseNote(BaseModel):
    id: str
    author_id: str
    author_name: str
    content: str
    timestamp: datetime

class CaseCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field("", max_length=5000)
    case_type: CaseType = CaseType.OTHER
    priority: CasePriority = CasePriority.MEDIUM
    assigned_investigator: Optional[str] = None  # User ID
    tags: List[str] = Field(default_factory=list)
    initial_note: Optional[str] = None

class CaseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    case_type: Optional[CaseType] = None
    priority: Optional[CasePriority] = None
    assigned_investigator: Optional[str] = None
    tags: Optional[List[str]] = None

class CaseStatusUpdate(BaseModel):
    status: CaseStatus

class AddCaseNotePayload(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)

class CaseResponse(BaseModel):
    id: str = Field(..., alias="_id")
    case_number: str
    title: str
    description: str
    case_type: CaseType
    priority: CasePriority
    status: CaseStatus
    created_by: str
    created_by_name: Optional[str] = None
    assigned_investigator: Optional[str] = None
    assigned_investigator_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    notes: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class CaseStats(BaseModel):
    total_cases: int
    active_cases: int
    open_cases: int
    critical_cases: int
    closed_cases: int
    archived_cases: int
