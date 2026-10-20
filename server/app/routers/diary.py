from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import Dict, Any, Optional, List
from bson import ObjectId

from app.core.database import get_database
from app.routers.auth import get_current_user
from app.core.rbac import require_case_access, is_admin, is_court_auditor
from app.models.diary import (
    DiaryEntryCreate,
    DiaryEntryAmend,
    DiaryEntryResponse,
    DiaryListResponse,
    DiaryVerificationResult,
    DiaryParseRequest,
    DiaryParseResponse
)
from app.repositories.diary import DiaryRepository, LEGAL_DISCLAIMER
from app.services.diary_ai_service import DiaryAIService

router = APIRouter(prefix="/cases/{case_id}/diary", tags=["investigation-diary"])

async def _get_authorized_case(case_id: str, current_user: Dict[str, Any], for_write: bool = False) -> Dict[str, Any]:
    db = get_database()
    oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else None
    case = await db["cases"].find_one({"_id": oid if oid else case_id})
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case with ID '{case_id}' was not found in the forensic registry."
        )
    require_case_access(current_user, case, for_write=for_write)
    return case

@router.post("", response_model=DiaryEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_diary_entry(
    case_id: str,
    payload: DiaryEntryCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new day-by-day Investigation Diary entry under BNSS Section 192.
    Records date, times, locations, activities, findings, related exhibits, and confidential references.
    Automatically sequences entry number and calculates cryptographically chained SHA-256 hash.
    Requires Admin or assigned Case Investigator privileges.
    """
    await _get_authorized_case(case_id, current_user, for_write=True)

    db = get_database()
    repo = DiaryRepository(db)

    entry = await repo.create_entry(
        case_id=case_id,
        user=current_user,
        payload=payload
    )
    return entry

@router.get("", response_model=DiaryListResponse)
async def list_diary_entries(
    case_id: str,
    start_date: Optional[str] = Query(None, description="Filter entries on or after this investigation date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter entries on or before this investigation date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Keyword search across activities, places, findings, or entry code"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_order: int = Query(1, description="1 for chronological (oldest to newest), -1 for newest first"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List case investigation diary entries chronologically with optional date filters and search.
    Enforces role-based confidentiality: Court Auditors and Read-Only users have witness references redacted.
    """
    await _get_authorized_case(case_id, current_user, for_write=False)

    db = get_database()
    repo = DiaryRepository(db)

    entries, total = await repo.list_entries(
        case_id=case_id,
        user=current_user,
        start_date=start_date,
        end_date=end_date,
        search=search,
        skip=skip,
        limit=limit,
        sort_order=sort_order
    )

    return DiaryListResponse(
        entries=entries,
        total=total,
        case_id=case_id,
        legal_disclaimer=LEGAL_DISCLAIMER
    )

@router.get("/{entry_id}", response_model=DiaryEntryResponse)
async def get_diary_entry(
    case_id: str,
    entry_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retrieve a specific investigation diary entry by ID.
    """
    await _get_authorized_case(case_id, current_user, for_write=False)

    db = get_database()
    repo = DiaryRepository(db)

    entry = await repo.get_entry_by_id(entry_id, case_id, current_user)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation diary entry '{entry_id}' not found for case '{case_id}'."
        )
    return entry

@router.post("/{entry_id}/amend", response_model=DiaryEntryResponse)
async def amend_diary_entry(
    case_id: str,
    entry_id: str,
    payload: DiaryEntryAmend,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Amend a finalized investigation diary entry.
    Under BNSS Section 192 principles, finalized records are never silently overwritten or deleted.
    A cryptographically sealed amendment record is permanently appended to the entry's amendment ledger.
    Requires an official justification/reason.
    """
    await _get_authorized_case(case_id, current_user, for_write=True)

    db = get_database()
    repo = DiaryRepository(db)

    try:
        updated = await repo.amend_entry(
            entry_id=entry_id,
            case_id=case_id,
            user=current_user,
            payload=payload
        )
        return updated
    except ValueError as e:
        err_msg = str(e)
        if "DIARY_ENTRY_NOT_FOUND" in err_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diary entry not found.")
        elif "NO_CHANGES_DETECTED" in err_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

@router.get("/{entry_id}/verify", response_model=DiaryVerificationResult)
async def verify_diary_entry(
    case_id: str,
    entry_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Verify the cryptographic SHA-256 seal and hash chain continuity of an investigation diary entry.
    """
    await _get_authorized_case(case_id, current_user, for_write=False)

    db = get_database()
    repo = DiaryRepository(db)

    try:
        result = await repo.verify_entry_integrity(entry_id, case_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.delete("/{entry_id}")
async def delete_diary_entry(
    case_id: str,
    entry_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Strict immutability enforcement:
    Investigation diary entries recorded under BNSS Section 192 principles cannot be deleted.
    """
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="BNSS_192_IMMUTABILITY_RESTRICTION: Investigation diary entries cannot be deleted. Use the amendment protocol with an official justification."
    )

@router.post("/ai-parse", response_model=DiaryParseResponse)
async def ai_parse_diary_narrative(
    case_id: str,
    payload: DiaryParseRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Intelligently parse raw investigative notes, informal field logs, voice memos,
    or Tanglish / multilingual text into structured, chronological BNSS 192 diary fields.
    Automatically identifies the language, sequences timeline milestones with timestamps and locations,
    and formats activities and findings in court-admissible forensic English.
    Requires Admin or assigned Case Investigator privileges.
    """
    await _get_authorized_case(case_id, current_user, for_write=True)
    db = get_database()
    ai_service = DiaryAIService()
    result = await ai_service.parse_and_organize(
        raw_text=payload.raw_text,
        investigation_date=payload.investigation_date,
        db=db
    )
    return result
