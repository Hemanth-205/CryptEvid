from fastapi import APIRouter, Depends, Query, Request
from typing import List, Dict, Any, Optional
from app.core.database import get_database
from app.repositories.audit import AuditRepository
from app.routers.auth import get_current_user, require_role
from app.models.user import UserRole

router = APIRouter(tags=["audit"])

@router.get("/audit-logs")
async def get_audit_logs(
    case_id: Optional[str] = Query(None),
    limit: int = Query(200),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Fetch Chain of Custody logs. Investigators and Admins can view logs.
    """
    db = get_database()
    audit_repo = AuditRepository(db)
    logs = await audit_repo.list_logs(case_id=case_id, limit=limit)
    return logs
