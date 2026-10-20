import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from bson import ObjectId

from app.repositories.base import BaseRepository
from app.repositories.audit import AuditRepository
from app.models.diary import DiaryEntryCreate, DiaryEntryAmend, DiaryAmendment

GENESIS_HASH = "0" * 64
LEGAL_DISCLAIMER = (
    "BNSS SECTION 192 STATUTORY NOTICE: This digital investigation diary record is informed by the "
    "provisions of Section 192 of the Bharatiya Nagarik Suraksha Sanhita, 2023 (recording day-to-day "
    "proceedings, times, visited locations, and circumstances discovered). Digital maintenance of diary "
    "entries in CRYPTEVID provides cryptographic tamper-evidence and versioned amendment auditability. "
    "Official evidentiary presentation in court remains subject to state police manuals, CrPC/BNSS procedural "
    "codes, and Bharatiya Sakshya Adhiniyam, 2023 evidentiary rules."
)

class DiaryRepository(BaseRepository):
    """
    Repository for Digital Investigation Diary entries under BNSS Section 192 principles.
    Enforces cryptographic SHA-256 hash chaining, immutable versioning via amendment ledgers,
    and audit log mirroring.
    """

    def __init__(self, db):
        super().__init__(db)
        self.col = db["investigation_diary"]
        self.audit_repo = AuditRepository(db)

    @staticmethod
    def compute_canonical_hash(
        case_id: str,
        entry_number: int,
        investigation_date: str,
        time_info_received: Optional[str],
        start_time: str,
        closing_time: str,
        places_visited: List[str],
        activities_performed: str,
        findings: str,
        related_evidence_ids: List[str],
        created_by: str,
        created_at_iso: str,
        previous_hash: str,
        timeline_events: Optional[List[Any]] = None
    ) -> str:
        """
        Calculate deterministic SHA-256 digest over canonical entry attributes.
        """
        norm_places = ",".join(sorted([p.strip() for p in places_visited if p.strip()]))
        norm_ev_ids = ",".join(sorted([str(eid).strip() for eid in related_evidence_ids if str(eid).strip()]))
        canonical_str = (
            f"{case_id}|{entry_number}|{investigation_date}|{time_info_received or ''}|"
            f"{start_time.strip()}|{closing_time.strip()}|{norm_places}|"
            f"{activities_performed.strip()}|{findings.strip()}|{norm_ev_ids}|"
            f"{created_by}|{created_at_iso}|{previous_hash}"
        )
        if timeline_events:
            norm_tl_items = []
            for ev in timeline_events:
                if isinstance(ev, dict):
                    t = ev.get("time", "").strip()
                    loc = ev.get("location", "").strip()
                    act = ev.get("activity", "").strip()
                elif hasattr(ev, "time"):
                    t = getattr(ev, "time", "").strip()
                    loc = getattr(ev, "location", "").strip()
                    act = getattr(ev, "activity", "").strip()
                else:
                    t, loc, act = "", "", ""
                norm_tl_items.append(f"{t}@{loc}:{act}")
            canonical_str += f"|{';'.join(norm_tl_items)}"
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest().lower()

    @staticmethod
    def compute_amendment_hash(
        amendment_id: str,
        entry_id: str,
        amended_by: str,
        timestamp_iso: str,
        reason: str,
        parent_hash: str
    ) -> str:
        canonical_str = f"{amendment_id}|{entry_id}|{amended_by}|{timestamp_iso}|{reason.strip()}|{parent_hash}"
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest().lower()

    async def create_entry(
        self,
        case_id: str,
        user: Dict[str, Any],
        payload: DiaryEntryCreate
    ) -> Dict[str, Any]:
        """
        Create a new, finalized daily investigation diary entry.
        Automatically sequences entry_number per case and chains SHA-256 hash.
        """
        user_id = str(user.get("_id", "0000"))
        user_name = user.get("name") or user.get("email") or "Investigator"
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        # Find case info for case_number
        case = await self.db["cases"].find_one({
            "_id": ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
        })
        case_num = case.get("case_number", case_id) if case else case_id

        # Determine next entry number for this case
        last_entry = await self.col.find_one(
            {"case_id": case_id},
            sort=[("entry_number", -1)]
        )
        entry_number = (last_entry.get("entry_number", 0) + 1) if last_entry else 1
        previous_hash = last_entry.get("entry_hash", GENESIS_HASH) if last_entry else GENESIS_HASH

        entry_code = f"DE-{case_num}-{entry_number:03d}"

        # Clean places and evidence lists
        clean_places = [p.strip() for p in payload.places_visited if p and p.strip()]
        clean_ev_ids = [str(e).strip() for e in payload.related_evidence_ids if str(e).strip()]

        # Clean timeline events
        clean_timeline = []
        if payload.timeline_events:
            for ev in payload.timeline_events:
                clean_timeline.append(ev.model_dump() if hasattr(ev, "model_dump") else dict(ev))

        # Compute cryptographic hash seal
        entry_hash = self.compute_canonical_hash(
            case_id=case_id,
            entry_number=entry_number,
            investigation_date=payload.investigation_date,
            time_info_received=payload.time_info_received,
            start_time=payload.start_time,
            closing_time=payload.closing_time,
            places_visited=clean_places,
            activities_performed=payload.activities_performed,
            findings=payload.findings,
            related_evidence_ids=clean_ev_ids,
            created_by=user_id,
            created_at_iso=now_iso,
            previous_hash=previous_hash,
            timeline_events=clean_timeline
        )

        doc = {
            "case_id": case_id,
            "case_number": case_num,
            "entry_number": entry_number,
            "entry_code": entry_code,
            "investigation_date": payload.investigation_date,
            "time_info_received": payload.time_info_received,
            "start_time": payload.start_time,
            "closing_time": payload.closing_time,
            "places_visited": clean_places,
            "activities_performed": payload.activities_performed,
            "findings": payload.findings,
            "related_evidence_ids": clean_ev_ids,
            "witness_references": payload.witness_references,
            "next_steps": payload.next_steps,
            "timeline_events": clean_timeline,
            "raw_input": payload.raw_input,
            "detected_language": payload.detected_language,
            "created_by": user_id,
            "created_by_name": user_name,
            "created_at": now,
            "created_at_iso": now_iso,
            "updated_at": now,
            "entry_hash": entry_hash,
            "previous_hash": previous_hash,
            "amendments": [],
            "is_amended": False
        }

        res = await self.col.insert_one(doc)
        doc["_id"] = str(res.inserted_id)

        # Mirror entry to immutable audit log
        await self.audit_repo.create_log(
            user_id=user_id,
            action="DIARY_ENTRY_CREATED",
            ip_address="127.0.0.1",
            user_agent="CRYPTEVID-DiaryEngine/BNSS-192",
            case_id=case_id,
            details=(
                f"Recorded BNSS 192 Investigation Diary Entry #{entry_number} ({entry_code}) "
                f"for Case {case_num}. Date: {payload.investigation_date}. "
                f"Places: {len(clean_places)}. Hash: {entry_hash[:16]}..."
            )
        )

        return self.serialize_doc(doc)

    async def list_entries(
        self,
        case_id: str,
        user: Dict[str, Any],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        sort_order: int = 1  # 1 for chronological, -1 for reverse chronological
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List diary entries chronologically with date filtering, text search, and pagination.
        Handles redaction of confidential witness references for non-authorized viewers.
        """
        query: Dict[str, Any] = {"case_id": case_id}

        # Date range filtering
        if start_date and end_date:
            query["investigation_date"] = {"$gte": start_date, "$lte": end_date}
        elif start_date:
            query["investigation_date"] = {"$gte": start_date}
        elif end_date:
            query["investigation_date"] = {"$lte": end_date}

        # Text search across activities, places, findings, and remarks
        if search and search.strip():
            s = search.strip()
            query["$or"] = [
                {"activities_performed": {"$regex": s, "$options": "i"}},
                {"findings": {"$regex": s, "$options": "i"}},
                {"places_visited": {"$elemMatch": {"$regex": s, "$options": "i"}}},
                {"next_steps": {"$regex": s, "$options": "i"}},
                {"entry_code": {"$regex": s, "$options": "i"}}
            ]

        total = await self.col.count_documents(query)
        cursor = self.col.find(query).sort("entry_number", sort_order).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)

        # RBAC Check: Court Auditors / Read-only users have witness info marked confidential/redacted
        from app.core.rbac import is_admin
        is_chief_admin = is_admin(user)
        user_role = str(user.get("role", "")).lower()
        can_view_witness = is_chief_admin or (user_role == "investigator")

        serialized_list = []
        for d in docs:
            ser = self.serialize_doc(d)
            if not can_view_witness:
                # Redact confidential witness reference
                if ser.get("witness_references"):
                    ser["witness_references"] = "[RESTRICTED - CONFIDENTIAL WITNESS DATA UNDER BNSS SEC. 192(3)]"
                    ser["is_witness_redacted"] = True
                else:
                    ser["is_witness_redacted"] = False
            else:
                ser["is_witness_redacted"] = False

            serialized_list.append(ser)

        return serialized_list, total

    async def get_entry_by_id(self, entry_id: str, case_id: str, user: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        oid = ObjectId(entry_id) if ObjectId.is_valid(entry_id) else None
        query = {"case_id": case_id, "$or": [{"_id": oid}, {"_id": entry_id}]} if oid else {"case_id": case_id, "_id": entry_id}
        doc = await self.col.find_one(query)
        if not doc:
            return None

        ser = self.serialize_doc(doc)
        from app.core.rbac import is_admin
        can_view_witness = is_admin(user) or (str(user.get("role", "")).lower() == "investigator")
        if not can_view_witness and ser.get("witness_references"):
            ser["witness_references"] = "[RESTRICTED - CONFIDENTIAL WITNESS DATA UNDER BNSS SEC. 192(3)]"
            ser["is_witness_redacted"] = True
        else:
            ser["is_witness_redacted"] = False

        return ser

    async def amend_entry(
        self,
        entry_id: str,
        case_id: str,
        user: Dict[str, Any],
        payload: DiaryEntryAmend
    ) -> Dict[str, Any]:
        """
        Amend an existing finalized diary entry.
        Creates a tamper-evident amendment record without overwriting original baseline hash or history.
        """
        oid = ObjectId(entry_id) if ObjectId.is_valid(entry_id) else None
        query = {"case_id": case_id, "$or": [{"_id": oid}, {"_id": entry_id}]} if oid else {"case_id": case_id, "_id": entry_id}
        existing = await self.col.find_one(query)
        if not existing:
            raise ValueError("DIARY_ENTRY_NOT_FOUND")

        user_id = str(user.get("_id", "0000"))
        user_name = user.get("name") or user.get("email") or "Investigator"
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        amendment_id = str(ObjectId())

        # Determine changed fields and capture previous/new states
        updatable_fields = [
            "investigation_date",
            "time_info_received",
            "start_time",
            "closing_time",
            "places_visited",
            "activities_performed",
            "findings",
            "related_evidence_ids",
            "witness_references",
            "next_steps",
            "timeline_events",
            "raw_input",
            "detected_language"
        ]

        previous_state: Dict[str, Any] = {}
        new_state: Dict[str, Any] = {}
        set_updates: Dict[str, Any] = {"updated_at": now, "is_amended": True}

        payload_dict = payload.model_dump(exclude_unset=True)
        if "timeline_events" in payload_dict and payload_dict["timeline_events"] is not None:
            payload_dict["timeline_events"] = [
                ev.model_dump() if hasattr(ev, "model_dump") else dict(ev)
                for ev in payload_dict["timeline_events"]
            ]
        for field in updatable_fields:
            if field in payload_dict and payload_dict[field] is not None:
                old_val = existing.get(field)
                new_val = payload_dict[field]
                if old_val != new_val:
                    previous_state[field] = old_val
                    new_state[field] = new_val
                    set_updates[field] = new_val

        if not new_state:
            raise ValueError("NO_CHANGES_DETECTED: No fields were modified in this amendment request.")

        # Compute cryptographic amendment seal
        parent_hash = existing.get("entry_hash", GENESIS_HASH)
        amendment_hash = self.compute_amendment_hash(
            amendment_id=amendment_id,
            entry_id=str(existing["_id"]),
            amended_by=user_id,
            timestamp_iso=now_iso,
            reason=payload.reason,
            parent_hash=parent_hash
        )

        amendment_record = {
            "amendment_id": amendment_id,
            "amended_by": user_id,
            "amended_by_name": user_name,
            "timestamp": now,
            "reason": payload.reason,
            "previous_state": previous_state,
            "new_state": new_state,
            "amendment_hash": amendment_hash
        }

        # Update database with new state and append to amendment history array
        await self.col.update_one(
            {"_id": existing["_id"]},
            {
                "$set": set_updates,
                "$push": {"amendments": amendment_record}
            }
        )

        # Audit log entry
        case_num = existing.get("case_number", case_id)
        entry_code = existing.get("entry_code", f"DE-{existing.get('entry_number')}")
        await self.audit_repo.create_log(
            user_id=user_id,
            action="DIARY_ENTRY_AMENDED",
            ip_address="127.0.0.1",
            user_agent="CRYPTEVID-DiaryEngine/BNSS-192",
            case_id=case_id,
            details=(
                f"Amended BNSS 192 Investigation Diary Entry #{existing.get('entry_number')} ({entry_code}) "
                f"for Case {case_num}. Reason: '{payload.reason}'. "
                f"Changed fields: {list(new_state.keys())}. Amendment Hash: {amendment_hash[:16]}..."
            )
        )

        # Return refreshed document
        updated_doc = await self.col.find_one({"_id": existing["_id"]})
        return self.serialize_doc(updated_doc)

    async def verify_entry_integrity(self, entry_id: str, case_id: str) -> Dict[str, Any]:
        """
        Cryptographically verify that the baseline SHA-256 hash matches the canonical attributes.
        """
        oid = ObjectId(entry_id) if ObjectId.is_valid(entry_id) else None
        query = {"case_id": case_id, "$or": [{"_id": oid}, {"_id": entry_id}]} if oid else {"case_id": case_id, "_id": entry_id}
        doc = await self.col.find_one(query)
        if not doc:
            raise ValueError("DIARY_ENTRY_NOT_FOUND")

        created_at = doc.get("created_at")
        created_at_iso = doc.get("created_at_iso")
        if not created_at_iso and isinstance(created_at, datetime):
            created_at_iso = created_at.isoformat()

        recalc = self.compute_canonical_hash(
            case_id=doc["case_id"],
            entry_number=doc["entry_number"],
            investigation_date=doc["investigation_date"],
            time_info_received=doc.get("time_info_received"),
            start_time=doc["start_time"],
            closing_time=doc["closing_time"],
            places_visited=doc.get("places_visited", []),
            activities_performed=doc["activities_performed"],
            findings=doc["findings"],
            related_evidence_ids=doc.get("related_evidence_ids", []),
            created_by=doc["created_by"],
            created_at_iso=created_at_iso or "",
            previous_hash=doc.get("previous_hash", GENESIS_HASH),
            timeline_events=doc.get("timeline_events")
        )

        stored = doc.get("entry_hash", "")
        is_valid = (stored.lower() == recalc.lower())

        # Check hash chaining with previous entry
        prev_matches = True
        if doc.get("entry_number", 1) > 1:
            prev_entry = await self.col.find_one(
                {"case_id": case_id, "entry_number": doc["entry_number"] - 1}
            )
            if prev_entry:
                prev_matches = (prev_entry.get("entry_hash") == doc.get("previous_hash"))
        else:
            prev_matches = (doc.get("previous_hash") == GENESIS_HASH)

        status_text = "VERIFIED_INTEGRITY_SECURE" if (is_valid and prev_matches) else "INTEGRITY_MISMATCH_SUSPECTED"

        return {
            "entry_id": str(doc["_id"]),
            "entry_number": doc.get("entry_number", 1),
            "stored_hash": stored,
            "recalculated_hash": recalc,
            "is_valid": is_valid,
            "previous_hash_matches": prev_matches,
            "status": status_text,
            "verified_at": datetime.now(timezone.utc)
        }
