from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ReportGenerateRequest(BaseModel):
    title: Optional[str] = None
    classification: Optional[str] = "CONFIDENTIAL // LAW ENFORCEMENT SENSITIVE"
    notes: Optional[str] = None

class ForensicReportResponse(BaseModel):
    report_id: str
    case_id: str
    case_number: str
    title: str
    version: int
    classification: str
    file_size: int
    sha256_hash: str
    generated_by: str
    generated_by_name: str
    generated_at: datetime
    download_url: str

class ReportListResponse(BaseModel):
    case_id: str
    total_reports: int
    reports: List[ForensicReportResponse]
