from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class TimelineEvent(BaseModel):
    time: str = Field(..., description="Timestamp or time window of milestone, e.g. '09:30', '11:15', '14:00'")
    location: str = Field(..., description="Place, room, or node associated with this specific event")
    activity: str = Field(..., description="Chronological investigative activity performed at this milestone")

class DiaryAmendment(BaseModel):
    amendment_id: str
    amended_by: str  # User ID
    amended_by_name: str
    timestamp: datetime
    reason: str = Field(..., min_length=5, max_length=1000, description="Mandatory official reason for amending this diary entry")
    previous_state: Dict[str, Any]
    new_state: Dict[str, Any]
    amendment_hash: str

class DiaryEntryCreate(BaseModel):
    investigation_date: str = Field(..., description="Date of investigation proceedings in YYYY-MM-DD format")
    time_info_received: Optional[str] = Field(None, max_length=50, description="Time at which information was received, if applicable (e.g. 09:30 or 2026-10-19 09:30)")
    start_time: str = Field(..., max_length=50, description="Time at which investigation commenced (e.g. 10:00)")
    closing_time: str = Field(..., max_length=50, description="Time at which investigation closed for the day (e.g. 18:30)")
    places_visited: List[str] = Field(default_factory=list, description="List of place(s) visited by the investigator")
    activities_performed: str = Field(..., min_length=5, max_length=15000, description="Day-by-day record of investigation proceedings and activities performed")
    findings: str = Field(..., min_length=5, max_length=15000, description="Statement of circumstances and findings ascertained through investigation")
    related_evidence_ids: List[str] = Field(default_factory=list, description="IDs of related evidence exhibits collected or analyzed")
    witness_references: Optional[str] = Field(None, max_length=5000, description="Confidential witness-related references, subject to authorized access")
    next_steps: Optional[str] = Field(None, max_length=5000, description="Next steps, pending actions, and procedural remarks")
    timeline_events: List[TimelineEvent] = Field(default_factory=list, description="Ordered chronological milestone sequence extracted from proceedings")
    raw_input: Optional[str] = Field(None, max_length=20000, description="Optional original unorganized text, voice transcript, or Tanglish notes")
    detected_language: Optional[str] = Field(None, max_length=100, description="Detected input language or format (e.g. Tanglish, Informal English, etc.)")

class DiaryEntryAmend(BaseModel):
    reason: str = Field(..., min_length=5, max_length=1000, description="Mandatory official justification for amending this finalized record")
    investigation_date: Optional[str] = None
    time_info_received: Optional[str] = None
    start_time: Optional[str] = None
    closing_time: Optional[str] = None
    places_visited: Optional[List[str]] = None
    activities_performed: Optional[str] = None
    findings: Optional[str] = None
    related_evidence_ids: Optional[List[str]] = None
    witness_references: Optional[str] = None
    next_steps: Optional[str] = None
    timeline_events: Optional[List[TimelineEvent]] = None
    raw_input: Optional[str] = None
    detected_language: Optional[str] = None

class DiaryEntryResponse(BaseModel):
    id: str = Field(..., alias="_id")
    case_id: str
    entry_number: int
    entry_code: str  # e.g. "DE-CASE01-001"
    investigation_date: str
    time_info_received: Optional[str] = None
    start_time: str
    closing_time: str
    places_visited: List[str] = Field(default_factory=list)
    activities_performed: str
    findings: str
    related_evidence_ids: List[str] = Field(default_factory=list)
    witness_references: Optional[str] = None
    is_witness_redacted: bool = False
    next_steps: Optional[str] = None
    timeline_events: List[TimelineEvent] = Field(default_factory=list)
    raw_input: Optional[str] = None
    detected_language: Optional[str] = None
    created_by: str
    created_by_name: str
    created_at: datetime
    updated_at: datetime
    entry_hash: str
    previous_hash: str
    amendments: List[DiaryAmendment] = Field(default_factory=list)
    is_amended: bool = False

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class DiaryListResponse(BaseModel):
    entries: List[DiaryEntryResponse]
    total: int
    case_id: str
    legal_disclaimer: str

class DiaryVerificationResult(BaseModel):
    entry_id: str
    entry_number: int
    stored_hash: str
    recalculated_hash: str
    is_valid: bool
    previous_hash_matches: bool
    status: str
    verified_at: datetime

class DiaryParseRequest(BaseModel):
    raw_text: str = Field(..., min_length=3, max_length=20000, description="Raw unorganized notes or Tanglish text to be processed and ordered by AI")
    investigation_date: Optional[str] = Field(None, description="Optional target investigation date (YYYY-MM-DD)")

class DiaryParseResponse(BaseModel):
    detected_language: str
    investigation_date: str
    time_info_received: Optional[str] = None
    start_time: str
    closing_time: str
    places_visited: List[str]
    activities_performed: str
    findings: str
    timeline_events: List[TimelineEvent]
    witness_references: Optional[str] = None
    next_steps: Optional[str] = None
    ai_provider: str
    raw_text: str
