from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

class MetadataStatus(str, Enum):
    PENDING = "PENDING"
    EXTRACTED = "EXTRACTED"
    FAILED = "FAILED"

class SourceType(str, Enum):
    MANUAL_UPLOAD = "MANUAL_UPLOAD"
    IOT_TERMINAL = "IOT_TERMINAL"
    NETWORK_CAPTURE = "NETWORK_CAPTURE"
    MEMORY_ACQUISITION = "MEMORY_ACQUISITION"
    STORAGE_IMAGE = "STORAGE_IMAGE"
    OTHER = "OTHER"

class EvidenceMetadataBase(BaseModel):
    case_id: str
    original_filename: str
    file_size: int
    mime_type: str
    file_extension: str
    source_device: Optional[str] = "WEB_APP"
    source_type: SourceType = SourceType.MANUAL_UPLOAD
    collector: str
    collection_timestamp: datetime
    description: Optional[str] = ""
    tags: List[str] = Field(default_factory=list)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    accessed_at: Optional[datetime] = None
    metadata_status: MetadataStatus = MetadataStatus.PENDING
    extracted_attributes: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None

class EvidenceMetadataCreate(EvidenceMetadataBase):
    pass

class EvidenceMetadataResponse(EvidenceMetadataBase):
    id: str = Field(..., alias="_id")
    evidence_id: str

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
