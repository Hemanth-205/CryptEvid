from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import BaseModel, EmailStr

from app.core.database import get_database
from app.core.security import get_password_hash
from app.routers.auth import get_current_user
from app.core.rbac import is_admin, is_portal_manager, can_manage_users
from app.models.user import UserRole
from app.repositories.user import UserRepository
from app.repositories.case import CaseRepository
from app.repositories.audit import AuditRepository

router = APIRouter(tags=["portal_manager"])

def require_portal_manager_or_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Enforce authorization: Chief Investigator (Admin) or Portal Manager only."""
    if not can_manage_users(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="PORTAL_MANAGEMENT_DENIED: Access restricted to Portal Manager and Chief Investigator administrators."
        )
    return current_user

# ==============================================================================
# SCHEMAS
# ==============================================================================

class PortalUserCreate(BaseModel):
    name: Optional[str] = None
    full_name: Optional[str] = None
    email: EmailStr
    role: UserRole = UserRole.INVESTIGATOR
    password: str
    is_active: bool = True

class PortalUserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

class UserStatusUpdate(BaseModel):
    is_active: bool

class CaseAssignmentRequest(BaseModel):
    investigator_id: Optional[str] = None

# ==============================================================================
# 1. PORTAL MANAGER DASHBOARD OVERVIEW (Zero evidence data)
# ==============================================================================

@router.get("/portal-manager/overview")
async def get_portal_manager_overview(current_user: Dict[str, Any] = Depends(require_portal_manager_or_admin)):
    """
    Provide aggregate operational telemetry for Portal Manager dashboard:
    - User metrics (total, active, inactive)
    - Case oversight metrics (total, assigned, unassigned, status distribution)
    - Total assigned officers
    CONFIDENTIALITY GUARANTEE: Does not access or expose evidence files or bytes.
    """
    db = get_database()
    users_col = db["users"]
    cases_col = db["cases"]

    # 1. User stats
    total_users = await users_col.count_documents({})
    active_users = await users_col.count_documents({"is_active": True})
    inactive_users = await users_col.count_documents({"is_active": False})

    # 2. Case stats
    total_cases = await cases_col.count_documents({})
    assigned_cases = await cases_col.count_documents({
        "assigned_investigator": {"$exists": True, "$ne": None, "$nin": ["", None]}
    })
    unassigned_cases = total_cases - assigned_cases

    # 3. Unique assigned officers count
    assigned_officer_ids = await cases_col.distinct(
        "assigned_investigator",
        {"assigned_investigator": {"$exists": True, "$ne": None, "$nin": ["", None]}}
    )
    total_assigned_officers = len(assigned_officer_ids)

    # 4. Cases by status breakdown
    open_cases = await cases_col.count_documents({"status": "OPEN"})
    in_progress_cases = await cases_col.count_documents({"status": "IN_PROGRESS"})
    closed_cases = await cases_col.count_documents({"status": "CLOSED"})
    on_hold_cases = await cases_col.count_documents({"status": "ON_HOLD"})

    assignment_rate = round((assigned_cases / total_cases * 100.0), 1) if total_cases > 0 else 0.0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "total_cases": total_cases,
        "total_assigned_officers": total_assigned_officers,
        "assignment_overview": {
            "assigned_cases": assigned_cases,
            "unassigned_cases": unassigned_cases,
            "assignment_rate": assignment_rate,
            "open_cases": open_cases,
            "in_progress_cases": in_progress_cases,
            "closed_cases": closed_cases,
            "on_hold_cases": on_hold_cases
        }
    }

# ==============================================================================
# 2. USER MANAGEMENT DIRECTORY (Protected & Credential-Stripped)
# ==============================================================================

@router.get("/portal-manager/users")
@router.get("/users")
async def list_portal_users(
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(require_portal_manager_or_admin)
):
    """
    Searchable, filterable user directory for Portal Manager & Admin.
    CONFIDENTIALITY & SECURITY RULE:
    Passwords, hashes, authentication tokens, fingerprint templates, and RFID secrets
    are NEVER returned in this directory!
    """
    db = get_database()
    query: Dict[str, Any] = {}

    if role and role.strip() and role != "ALL":
        query["role"] = role.strip().lower()

    if is_active is not None:
        query["is_active"] = is_active

    if search and search.strip():
        term = search.strip()
        query["$or"] = [
            {"name": {"$regex": term, "$options": "i"}},
            {"email": {"$regex": term, "$options": "i"}}
        ]

    total = await db["users"].count_documents(query)
    cursor = db["users"].find(query).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)

    # Compute assigned cases count per user
    user_ids = [str(d["_id"]) for d in docs]
    case_counts: Dict[str, int] = {}
    if user_ids:
        agg = await db["cases"].aggregate([
            {"$match": {"assigned_investigator": {"$in": user_ids}}},
            {"$group": {"_id": "$assigned_investigator", "count": {"$sum": 1}}}
        ]).to_list(length=1000)
        for row in agg:
            case_counts[str(row["_id"])] = row["count"]

    safe_users = []
    for d in docs:
        uid = str(d["_id"])
        safe_users.append({
            "_id": uid,
            "name": d.get("name", "Unknown"),
            "email": d.get("email", ""),
            "role": d.get("role", "investigator"),
            "is_active": d.get("is_active", True),
            "created_at": d.get("created_at"),
            "assigned_cases_count": case_counts.get(uid, 0)
        })

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "users": safe_users
    }

@router.post("/portal-manager/users", status_code=status.HTTP_201_CREATED)
@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_portal_user(
    payload: PortalUserCreate,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_portal_manager_or_admin)
):
    """
    Create a new portal user account.
    ANTI-PRIVILEGE ESCALATION RULES:
    - Portal Manager can ONLY create INVESTIGATOR or READONLY accounts.
    - Portal Manager CANNOT create ADMIN or PORTAL_MANAGER accounts.
    - Passwords are validated and hashed with BCrypt.
    - Action is immutably audited.
    """
    actor_is_admin = is_admin(current_user)

    # Privilege escalation guard
    if not actor_is_admin:
        requested_role = payload.role.value if isinstance(payload.role, UserRole) else str(payload.role)
        if requested_role in ("admin", "portal_manager"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="PRIVILEGE_ESCALATION_BLOCKED: Portal Manager cannot provision Administrator or Portal Manager accounts. Only Chief Investigators (Admin) can assign elevated roles."
            )

    if len(payload.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters in length."
        )

    db = get_database()
    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)

    # Check for existing email
    clean_email = payload.email.strip().lower()
    existing = await user_repo.get_by_email(clean_email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An account with email '{clean_email}' already exists."
        )

    now = datetime.now(timezone.utc)
    user_name = (payload.name or payload.full_name or clean_email.split('@')[0]).strip()
    new_user_doc = {
        "email": clean_email,
        "name": user_name,
        "role": payload.role.value if isinstance(payload.role, UserRole) else str(payload.role),
        "hashed_password": get_password_hash(payload.password),
        "is_active": payload.is_active,
        "created_at": now
    }

    created = await user_repo.create(new_user_doc)
    client_ip = request.client.host if request.client else "127.0.0.1"

    # Audit log
    await audit_repo.create_log(
        user_id=str(current_user["_id"]),
        action="USER_MANAGEMENT_CREATE",
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent", "Unknown"),
        details=f"User account '{created['email']}' ({created['name']}) created with role '{created['role']}' by {current_user.get('name')} ({current_user.get('role')})."
    )

    return {
        "_id": str(created["_id"]),
        "name": created["name"],
        "email": created["email"],
        "role": created["role"],
        "is_active": created["is_active"],
        "created_at": created["created_at"]
    }

@router.patch("/portal-manager/users/{user_id}")
@router.patch("/users/{user_id}")
async def update_portal_user(
    user_id: str,
    payload: PortalUserUpdate,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_portal_manager_or_admin)
):
    """
    Update permitted details for an existing user account.
    ANTI-PRIVILEGE ESCALATION RULES:
    - Users cannot modify their own role.
    - Portal Manager cannot modify Chief Investigator (Admin) accounts.
    - Portal Manager cannot elevate any user to Admin or Portal Manager.
    - Action is immutably audited.
    """
    db = get_database()
    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)

    target_user = await user_repo.get_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found")

    actor_is_admin = is_admin(current_user)
    is_self = str(current_user["_id"]) == user_id

    # Rule: Prevent self-privilege escalation
    if is_self and payload.role is not None:
        new_role_val = payload.role.value if isinstance(payload.role, UserRole) else str(payload.role)
        if new_role_val != target_user.get("role"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="PRIVILEGE_ESCALATION_BLOCKED: You cannot modify your own administrative role."
            )

    # Rule: Portal Manager cannot modify Admin account
    target_role = str(target_user.get("role", "")).lower()
    if not actor_is_admin and target_role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="PRIVILEGE_VIOLATION: Portal Manager is not authorized to edit Chief Investigator (Admin) accounts."
        )

    # Rule: Portal Manager cannot grant Admin or Portal Manager
    if not actor_is_admin and payload.role is not None:
        new_role_val = payload.role.value if isinstance(payload.role, UserRole) else str(payload.role)
        if new_role_val in ("admin", "portal_manager") and new_role_val != target_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="PRIVILEGE_ESCALATION_BLOCKED: Portal Manager cannot assign Administrator or Portal Manager privileges."
            )

    update_fields: Dict[str, Any] = {}
    if payload.name is not None and payload.name.strip():
        update_fields["name"] = payload.name.strip()
    if payload.email is not None and payload.email.strip():
        clean_email = payload.email.strip().lower()
        if clean_email != target_user.get("email"):
            existing = await user_repo.get_by_email(clean_email)
            if existing:
                raise HTTPException(status_code=400, detail="Email is already in use by another user.")
            update_fields["email"] = clean_email
    if payload.role is not None:
        update_fields["role"] = payload.role.value if isinstance(payload.role, UserRole) else str(payload.role)
    if payload.is_active is not None:
        if is_self and not payload.is_active:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own active session account.")
        update_fields["is_active"] = payload.is_active

    if update_fields:
        await user_repo.update(user_id, update_fields)

    client_ip = request.client.host if request.client else "127.0.0.1"
    await audit_repo.create_log(
        user_id=str(current_user["_id"]),
        action="USER_MANAGEMENT_UPDATE",
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent", "Unknown"),
        details=f"User account '{target_user.get('email')}' updated: {list(update_fields.keys())} by {current_user.get('name')}."
    )

    updated_doc = await user_repo.get_by_id(user_id)
    return {
        "_id": str(updated_doc["_id"]),
        "name": updated_doc.get("name"),
        "email": updated_doc.get("email"),
        "role": updated_doc.get("role"),
        "is_active": updated_doc.get("is_active", True),
        "created_at": updated_doc.get("created_at")
    }

@router.patch("/portal-manager/users/{user_id}/status")
@router.patch("/users/{user_id}/status")
async def toggle_portal_user_status(
    user_id: str,
    payload: UserStatusUpdate,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_portal_manager_or_admin)
):
    """
    Activate or deactivate a user account with strict safeguards:
    - Users cannot deactivate their own active account.
    - Portal Manager cannot deactivate Administrator accounts.
    """
    if str(current_user["_id"]) == user_id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own active session account."
        )

    db = get_database()
    user_repo = UserRepository(db)
    audit_repo = AuditRepository(db)

    target_user = await user_repo.get_by_id(user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found")

    actor_is_admin = is_admin(current_user)
    if not actor_is_admin and str(target_user.get("role", "")).lower() == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="PRIVILEGE_VIOLATION: Portal Manager cannot alter status of Chief Investigator (Admin) accounts."
        )

    await user_repo.update(user_id, {"is_active": payload.is_active})
    client_ip = request.client.host if request.client else "127.0.0.1"

    status_str = "ACTIVATED" if payload.is_active else "DEACTIVATED"
    await audit_repo.create_log(
        user_id=str(current_user["_id"]),
        action="USER_STATUS_CHANGE",
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent", "Unknown"),
        details=f"User '{target_user.get('email')}' was {status_str} by {current_user.get('name')} ({current_user.get('role')})."
    )

    return {
        "success": True,
        "user_id": user_id,
        "is_active": payload.is_active,
        "message": f"User account successfully {status_str.lower()}."
    }

# ==============================================================================
# 3. CASE OVERSIGHT & OFFICER ASSIGNMENT (Strictly zero evidence contents)
# ==============================================================================

@router.get("/portal-manager/cases")
async def list_portal_manager_cases(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    assignment_status: Optional[str] = Query(None),  # ASSIGNED | UNASSIGNED
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(require_portal_manager_or_admin)
):
    """
    Searchable, filterable case list for Portal Manager oversight.
    CONFIDENTIALITY GUARANTEE:
    - Provides case ID, title, status, priority, timestamps, assigned officer info.
    - STRICTLY EXCLUDES all evidence files, evidence descriptions, vault paths, digests, and previews.
    """
    db = get_database()
    cases_col = db["cases"]
    users_col = db["users"]

    query: Dict[str, Any] = {}

    if status and status.strip() and status != "ALL":
        query["status"] = status.strip().upper()

    if priority and priority.strip() and priority != "ALL":
        query["priority"] = priority.strip().upper()

    if assignment_status == "ASSIGNED":
        query["assigned_investigator"] = {"$exists": True, "$ne": None, "$nin": ["", None]}
    elif assignment_status == "UNASSIGNED":
        query["$or"] = [
            {"assigned_investigator": {"$exists": False}},
            {"assigned_investigator": None},
            {"assigned_investigator": ""}
        ]

    if search and search.strip():
        term = search.strip()
        search_or = [
            {"case_number": {"$regex": term, "$options": "i"}},
            {"title": {"$regex": term, "$options": "i"}}
        ]
        # Match officer name in search
        matching_officers = await users_col.find(
            {"name": {"$regex": term, "$options": "i"}},
            {"_id": 1}
        ).to_list(length=100)
        matching_officer_ids = [str(o["_id"]) for o in matching_officers]
        if matching_officer_ids:
            search_or.append({"assigned_investigator": {"$in": matching_officer_ids}})

        if "$or" in query:
            query = {"$and": [query, {"$or": search_or}]}
        else:
            query["$or"] = search_or

    total = await cases_col.count_documents(query)
    cursor = cases_col.find(query).sort("created_at", -1).skip(skip).limit(limit)
    raw_cases = await cursor.to_list(length=limit)

    # Hydrate assigned officer details
    assignee_ids = list({str(c.get("assigned_investigator")) for c in raw_cases if c.get("assigned_investigator")})
    officer_map: Dict[str, Dict[str, Any]] = {}
    if assignee_ids:
        oids = [ObjectId(x) for x in assignee_ids if ObjectId.is_valid(x)]
        officers = await users_col.find(
            {"$or": [{"_id": {"$in": oids}}, {"_id": {"$in": assignee_ids}}]},
            {"name": 1, "email": 1, "role": 1}
        ).to_list(length=500)
        for o in officers:
            officer_map[str(o["_id"])] = {
                "name": o.get("name", "Investigator"),
                "email": o.get("email", ""),
                "role": o.get("role", "investigator")
            }

    oversight_cases = []
    for c in raw_cases:
        cid = str(c["_id"])
        assigned_id = str(c.get("assigned_investigator", "")) if c.get("assigned_investigator") else None
        officer = officer_map.get(assigned_id) if assigned_id else None

        oversight_cases.append({
            "_id": cid,
            "case_id": cid,
            "case_number": c.get("case_number", "CASE"),
            "title": c.get("title", "Forensic Investigation"),
            "description": c.get("description", ""),
            "case_type": c.get("case_type", "OTHER"),
            "priority": c.get("priority", "MEDIUM"),
            "status": c.get("status", "OPEN"),
            "created_at": c.get("created_at"),
            "updated_at": c.get("updated_at"),
            "assigned_officer_id": assigned_id,
            "assigned_officer_name": officer["name"] if officer else "Unassigned",
            "assigned_investigator_name": officer["name"] if officer else "Unassigned",
            "assigned_officer_email": officer["email"] if officer else None,
            "assignment_status": "ASSIGNED" if assigned_id else "UNASSIGNED"
        })

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "cases": oversight_cases
    }

@router.post("/portal-manager/cases/{case_id}/assign")
async def assign_case_officer(
    case_id: str,
    payload: CaseAssignmentRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_portal_manager_or_admin)
):
    """
    Assign or unassign an officer to a forensic case.
    Enforces that the assigned officer is active and is not a Court Auditor.
    """
    db = get_database()
    cases_col = db["cases"]
    users_col = db["users"]
    audit_repo = AuditRepository(db)

    oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else None
    case_doc = await cases_col.find_one({"_id": oid if oid else case_id})
    if not case_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    new_officer_name = "Unassigned"
    new_assignee_id = None

    if payload.investigator_id and payload.investigator_id.strip():
        inv_id = payload.investigator_id.strip()
        inv_oid = ObjectId(inv_id) if ObjectId.is_valid(inv_id) else None
        officer_doc = await users_col.find_one({"_id": inv_oid if inv_oid else inv_id})
        if not officer_doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target officer not found")
        if not officer_doc.get("is_active", True):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot assign cases to an inactive officer account.")
        if str(officer_doc.get("role", "")).lower() in ("readonly", "court_auditor", "auditor"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Court Auditors cannot be assigned to cases.")

        new_assignee_id = str(officer_doc["_id"])
        new_officer_name = officer_doc.get("name", "Investigator")

    now = datetime.now(timezone.utc)
    await cases_col.update_one(
        {"_id": case_doc["_id"]},
        {"$set": {"assigned_investigator": new_assignee_id, "updated_at": now}}
    )

    client_ip = request.client.host if request.client else "127.0.0.1"
    await audit_repo.create_log(
        user_id=str(current_user["_id"]),
        action="CASE_OFFICER_ASSIGNMENT",
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent", "Unknown"),
        case_id=str(case_doc["_id"]),
        details=f"Case '{case_doc.get('case_number')}' assigned to officer '{new_officer_name}' ({new_assignee_id}) by {current_user.get('name')} ({current_user.get('role')})."
    )

    return {
        "success": True,
        "case_id": str(case_doc["_id"]),
        "case_number": case_doc.get("case_number"),
        "assigned_investigator": new_assignee_id,
        "assigned_officer_name": new_officer_name,
        "message": f"Case assigned to {new_officer_name}."
    }
