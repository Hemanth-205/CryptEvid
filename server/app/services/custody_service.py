import hashlib
import json
from datetime import datetime, timezone
from bson import ObjectId
from typing import Dict, Any, List, Optional
from app.repositories.base import BaseRepository

GENESIS_HASH = "0" * 64

class ChainOfCustodyService:
    """
    Forensic Chain of Custody service with local cryptographic hash-chaining.
    Provides immutable-style audit logging where each custody event cryptographically
    seals the previous event's hash, preventing retroactive tampering of evidence history.
    """

    @staticmethod
    def _compute_event_hash(
        evidence_id: str,
        case_id: str,
        action: str,
        actor_id: str,
        timestamp_str: str,
        previous_hash: str,
        details: str
    ) -> str:
        canonical_str = f"{evidence_id}|{case_id}|{action}|{actor_id}|{timestamp_str}|{previous_hash}|{details}"
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest().lower()

    @classmethod
    async def record_event(
        cls,
        db,
        evidence_id: str,
        case_id: str,
        action: str,
        actor_id: str,
        actor_name: str,
        details: str = "",
        ip_address: str = "127.0.0.1",
        device_id: str = "WEB_APP"
    ) -> Dict[str, Any]:
        custody_col = db["chain_of_custody"]
        audit_col = db["audit_logs"]

        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        # Find the last event for this evidence item to chain hashes
        last_event = await custody_col.find_one(
            {"evidence_id": evidence_id},
            sort=[("timestamp", -1)]
        )

        previous_hash = last_event.get("event_hash", GENESIS_HASH) if last_event else GENESIS_HASH

        # Calculate current event hash
        event_hash = cls._compute_event_hash(
            evidence_id=evidence_id,
            case_id=case_id,
            action=action,
            actor_id=actor_id,
            timestamp_str=now_iso,
            previous_hash=previous_hash,
            details=details
        )

        event_doc = {
            "evidence_id": evidence_id,
            "case_id": case_id,
            "action": action,
            "actor_id": actor_id,
            "actor_name": actor_name,
            "timestamp": now,
            "timestamp_iso": now_iso,
            "ip_address": ip_address,
            "device_id": device_id,
            "previous_hash": previous_hash,
            "event_hash": event_hash,
            "details": details
        }

        result = await custody_col.insert_one(event_doc)
        event_doc["_id"] = str(result.inserted_id)
        event_doc["event_id"] = str(result.inserted_id)

        # Mirror into unified audit_logs
        try:
            await audit_col.insert_one({
                "user_id": ObjectId(actor_id) if actor_id and ObjectId.is_valid(actor_id) else None,
                "action": action,
                "ip_address": ip_address,
                "user_agent": f"CUSTODY_SERVICE_{device_id}",
                "device_id": device_id,
                "case_id": ObjectId(case_id) if case_id and ObjectId.is_valid(case_id) else None,
                "evidence_id": ObjectId(evidence_id) if evidence_id and ObjectId.is_valid(evidence_id) else None,
                "details": f"[Chain of Custody] {action}: {details} (Hash: {event_hash[:12]}...)",
                "timestamp": now
            })
        except Exception as e:
            print(f"Warning: Failed to mirror custody event into audit_logs: {e}")

        return BaseRepository.serialize_doc(event_doc)

    @classmethod
    async def get_custody_history(cls, db, evidence_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve chronological custody records and verify the cryptographic integrity
        of the custody hash chain.
        """
        custody_col = db["chain_of_custody"]
        cursor = custody_col.find({"evidence_id": evidence_id}).sort("timestamp", 1)
        docs = await cursor.to_list(length=2000)

        history: List[Dict[str, Any]] = []
        expected_prev = GENESIS_HASH

        for doc in docs:
            serialized = BaseRepository.serialize_doc(doc)
            serialized["event_id"] = serialized["_id"]

            prev_hash = serialized.get("previous_hash", GENESIS_HASH)
            event_hash = serialized.get("event_hash", "")
            ts_str = serialized.get("timestamp_iso") or (
                doc["timestamp"].isoformat() if isinstance(doc.get("timestamp"), datetime) else ""
            )

            # Check previous hash continuity
            chain_valid = (prev_hash == expected_prev)

            # Check current event hash calculation
            recalculated = cls._compute_event_hash(
                evidence_id=str(serialized.get("evidence_id")),
                case_id=str(serialized.get("case_id")),
                action=str(serialized.get("action")),
                actor_id=str(serialized.get("actor_id")),
                timestamp_str=ts_str,
                previous_hash=prev_hash,
                details=str(serialized.get("details", ""))
            )

            if recalculated != event_hash:
                chain_valid = False

            serialized["is_chain_valid"] = chain_valid
            expected_prev = event_hash
            history.append(serialized)

        return history
