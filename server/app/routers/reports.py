import os
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import FileResponse
from typing import Dict, Any, Optional
from bson import ObjectId

from app.core.database import get_database
from app.core.config import settings
from app.routers.auth import get_current_user
from app.core.rbac import is_admin, require_case_access, get_accessible_case_ids, can_view_all_cases
from app.models.user import UserRole
from app.models.report import ForensicReportResponse, ReportListResponse, ReportGenerateRequest
from app.repositories.case import CaseRepository
from app.repositories.user import UserRepository
from app.services.report_service import ForensicReportService

router = APIRouter(tags=["reports"])

@router.post("/cases/{case_id}/reports", response_model=ForensicReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_case_report(
    case_id: str,
    payload: ReportGenerateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generate an official, court-admissible forensic PDF report.
    Compiles verified case exhibits, SHA-256 baseline and integrity verification statuses,
    cryptographic chain-of-custody ledger, forensic timeline events, topological graph,
    deterministic risk scoring, AI threat reasoning, and actionable countermeasures.
    """
    if current_user.get("role") == UserRole.READONLY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="UNAUTHORIZED: Read-only accounts cannot generate forensic reports"
        )

    db = get_database()
    case_repo = CaseRepository(db)
    case = await case_repo.get_by_id(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CASE_NOT_FOUND")

    require_case_access(current_user, case, for_write=True)

    try:
        return await ForensicReportService.generate_case_report(
            db=db,
            case_id=str(case["_id"]),
            user=current_user,
            title=payload.title,
            classification=payload.classification
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"REPORT_GENERATION_FAILED: {str(e)}"
        )

@router.get("/cases/{case_id}/reports", response_model=ReportListResponse)
async def list_case_reports(
    case_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """List all cryptographically sealed forensic report versions generated for a case."""
    db = get_database()
    case_repo = CaseRepository(db)
    case = await case_repo.get_by_id(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CASE_NOT_FOUND")

    require_case_access(current_user, case)

    cursor = db["forensic_reports"].find({"case_id": str(case["_id"])}).sort("version", -1)
    docs = await cursor.to_list(length=100)

    reports = []
    for d in docs:
        rep_id = str(d["_id"])
        reports.append(ForensicReportResponse(
            report_id=rep_id,
            case_id=str(d["case_id"]),
            case_number=d.get("case_number", "CASE"),
            title=d.get("title", "Forensic Report"),
            version=d.get("version", 1),
            classification=d.get("classification", "CONFIDENTIAL"),
            file_size=d.get("file_size", 0),
            sha256_hash=d.get("sha256_hash", ""),
            generated_by=str(d.get("generated_by", "")),
            generated_by_name=d.get("generated_by_name", "Operator"),
            generated_at=d.get("generated_at"),
            download_url=f"/api/reports/{rep_id}/download"
        ))

    return ReportListResponse(
        case_id=str(case["_id"]),
        total_reports=len(reports),
        reports=reports
    )

@router.get("/reports")
async def list_all_reports(current_user: Dict[str, Any] = Depends(get_current_user)):
    """List all cryptographically sealed forensic reports across all accessible cases."""
    db = get_database()
    query = {}
    if not can_view_all_cases(current_user):
        allowed_case_ids = await get_accessible_case_ids(db, current_user)
        query = {"case_id": {"$in": allowed_case_ids}}

    cursor = db["forensic_reports"].find(query).sort("generated_at", -1)
    docs = await cursor.to_list(length=200)
    reports = []
    for d in docs:
        rep_id = str(d["_id"])
        reports.append({
            "report_id": rep_id,
            "case_id": str(d["case_id"]),
            "case_number": d.get("case_number", "CASE"),
            "title": d.get("title", "Forensic Report"),
            "version": d.get("version", 1),
            "classification": d.get("classification", "CONFIDENTIAL"),
            "file_size": d.get("file_size", 0),
            "sha256_hash": d.get("sha256_hash", ""),
            "generated_by": str(d.get("generated_by", "")),
            "generated_by_name": d.get("generated_by_name", "Operator"),
            "generated_at": d.get("generated_at"),
            "download_url": f"/api/reports/{rep_id}/download"
        })
    return {"total": len(reports), "reports": reports}

@router.get("/reports/{report_id}", response_model=ForensicReportResponse)
async def get_report_metadata(
    report_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieve metadata and cryptographic hash seal for a specific report."""
    db = get_database()
    oid = ObjectId(report_id) if ObjectId.is_valid(report_id) else None
    doc = await db["forensic_reports"].find_one({"_id": oid if oid else report_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="REPORT_NOT_FOUND")

    if not can_view_all_cases(current_user):
        case_repo = CaseRepository(db)
        case = await case_repo.get_by_id(doc["case_id"])
        if not case:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated case not found")
        require_case_access(current_user, case)

    rep_id = str(doc["_id"])
    return ForensicReportResponse(
        report_id=rep_id,
        case_id=str(doc["case_id"]),
        case_number=doc.get("case_number", "CASE"),
        title=doc.get("title", "Forensic Report"),
        version=doc.get("version", 1),
        classification=doc.get("classification", "CONFIDENTIAL"),
        file_size=doc.get("file_size", 0),
        sha256_hash=doc.get("sha256_hash", ""),
        generated_by=str(doc.get("generated_by", "")),
        generated_by_name=doc.get("generated_by_name", "Operator"),
        generated_at=doc.get("generated_at"),
        download_url=f"/api/reports/{rep_id}/download"
    )

@router.get("/reports/{report_id}/download")
async def download_forensic_report(
    report_id: str,
    token: Optional[str] = Query(None),
    request: Request = None
):
    """
    Safely stream and download the physical court-admissible PDF file.
    Validates authentication via Authorization header or query token parameter.
    """
    auth_token = token
    if not auth_token and request and "authorization" in request.headers:
        auth_header = request.headers["authorization"]
        if auth_header.startswith("Bearer "):
            auth_token = auth_header[7:]

    if not auth_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="AUTHENTICATION_REQUIRED")

    from app.core.security import decode_token
    payload = decode_token(auth_token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_TOKEN")

    db = get_database()
    oid = ObjectId(report_id) if ObjectId.is_valid(report_id) else None
    doc = await db["forensic_reports"].find_one({"_id": oid if oid else report_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="REPORT_NOT_FOUND")

    user_role = payload.get("role")
    sub = payload.get("sub")
    user_repo = UserRepository(db)
    user_doc = await user_repo.get_by_email(sub) if sub else None
    if not user_doc and sub and ObjectId.is_valid(sub):
        user_doc = await user_repo.get_by_id(sub)
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if user_role != UserRole.ADMIN.value and user_role != "admin":
        case_repo = CaseRepository(db)
        case = await case_repo.get_by_id(doc["case_id"])
        if not case:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated case not found")
        require_case_access(user_doc, case)

    # Resolve relative or cross-platform path
    case_id_str = str(doc["case_id"])
    reports_dir = os.path.join(settings.EVIDENCE_STORAGE_DIR, "reports", case_id_str)
    os.makedirs(reports_dir, exist_ok=True)
    clean_filename = doc.get("filename") or f"Forensic_Report_{doc.get('case_number', 'CASE')}_v{doc.get('version', 1)}.pdf"
    fallback_path = os.path.join(reports_dir, clean_filename)

    file_path = doc.get("file_path")
    actual_path = None
    if file_path and os.path.exists(file_path):
        actual_path = file_path
    elif os.path.exists(fallback_path):
        actual_path = fallback_path
    else:
        # Dynamically regenerate the PDF file!
        try:
            actual_path = await ForensicReportService.render_pdf_file(
                db=db,
                case_id=case_id_str,
                user=user_doc,
                title=doc.get("title"),
                classification=doc.get("classification"),
                version=doc.get("version", 1),
                target_path=fallback_path
            )
            await db["forensic_reports"].update_one(
                {"_id": doc["_id"]},
                {"$set": {"file_path": actual_path}}
            )
        except Exception as e:
            print(f"[REPORT_REGEN_ERR] {e}")

    if not actual_path or not os.path.exists(actual_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="REPORT_FILE_NOT_FOUND_ON_DISK")

    # Audit report download
    try:
        from app.repositories.audit import AuditRepository
        audit_repo = AuditRepository(db)
        await audit_repo.create_log(
            user_id=str(user_doc.get("_id", "0000")),
            action="REPORT_DOWNLOADED",
            ip_address=request.client.host if request and request.client else "127.0.0.1",
            user_agent=request.headers.get("user-agent", "Unknown") if request else "Unknown",
            case_id=case_id_str,
            details=f"Downloaded forensic examination report {clean_filename} (Report ID: {report_id})"
        )
    except Exception as e:
        print(f"[REPORT_AUDIT_LOG_ERR] {e}")

    return FileResponse(
        path=actual_path,
        media_type="application/pdf",
        filename=clean_filename
    )
