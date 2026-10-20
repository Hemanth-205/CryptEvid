from typing import Dict, Any, Optional, List
from bson import ObjectId
from fastapi import HTTPException, status
from app.models.user import UserRole

def is_admin(user: Dict[str, Any]) -> bool:
    """Check if the user is a Chief Investigator (Admin)."""
    role = user.get("role")
    if isinstance(role, UserRole):
        role = role.value
    return str(role).lower() == "admin"

def is_court_auditor(user: Dict[str, Any]) -> bool:
    """Check if the user is a Court Auditor (ReadOnly)."""
    role = user.get("role")
    if isinstance(role, UserRole):
        role = role.value
    return str(role).lower() in ("readonly", "court_auditor", "auditor")

def can_view_all_cases(user: Dict[str, Any]) -> bool:
    """
    Chief Investigator (Admin) and Court Auditor (ReadOnly) can view all cases across the system.
    No case assignment is needed for the Court Auditor.
    """
    return is_admin(user) or is_court_auditor(user)

def can_user_access_case(user: Dict[str, Any], case: Dict[str, Any], for_write: bool = False) -> bool:
    """
    RBAC Case Access Policy:
    - Chief Investigator (Admin): Full view and manage access to all cases.
    - Court Auditor (ReadOnly): Can VIEW all cases across the platform without assignment; CANNOT modify.
    - Regular Investigator: Restricted ONLY to cases they created or are assigned to.
    """
    if is_admin(user):
        return True

    if is_court_auditor(user):
        return not for_write

    user_id = str(user.get("_id", ""))
    creator_id = str(case.get("created_by", ""))
    assigned_id = str(case.get("assigned_investigator", ""))

    return (user_id == creator_id) or (user_id == assigned_id)

def require_case_access(user: Dict[str, Any], case: Dict[str, Any], for_write: bool = False) -> None:
    """Raise HTTP 403 Forbidden if user is not authorized to access this case."""
    if not can_user_access_case(user, case, for_write=for_write):
        if is_court_auditor(user) and for_write:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="UNAUTHORIZED: Court Auditor account has read-only access and cannot modify case files or exhibits."
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="UNAUTHORIZED_CASE_ACCESS: You do not have permission to view or access this case file. Only Chief Investigator (Admin) and Court Auditor can view all cases."
        )

def get_user_case_ownership_filter(user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate MongoDB query filter for cases accessible to the given user.
    Returns empty dict {} for admin and court auditor (all cases accessible).
    """
    if can_view_all_cases(user):
        return {}

    user_id_str = str(user.get("_id", ""))
    uids = [user_id_str]
    if ObjectId.is_valid(user_id_str):
        uids.append(ObjectId(user_id_str))

    return {
        "$or": [
            {"created_by": {"$in": uids}},
            {"assigned_investigator": {"$in": uids}}
        ]
    }

async def get_accessible_case_ids(db, user: Dict[str, Any]) -> Optional[List[str]]:
    """
    Return a list of string case IDs accessible to the user, or None if admin or court auditor (unrestricted viewing).
    """
    if can_view_all_cases(user):
        return None

    query = get_user_case_ownership_filter(user)
    cursor = db["cases"].find(query, {"_id": 1})
    docs = await cursor.to_list(length=10000)
    return [str(d["_id"]) for d in docs]
