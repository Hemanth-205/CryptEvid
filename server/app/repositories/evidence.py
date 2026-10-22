from bson import ObjectId
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from app.repositories.base import BaseRepository

class EvidenceRepository(BaseRepository):
    @property
    def collection(self):
        return self.db["evidence"]

    async def create(self, evidence_data: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        evidence_data["created_at"] = now
        evidence_data["last_verified_at"] = None
        evidence_data["last_calculated_hash"] = None
        if "tags" not in evidence_data:
            evidence_data["tags"] = []

        result = await self.collection.insert_one(evidence_data)
        evidence_data["_id"] = str(result.inserted_id)
        return self.serialize_doc(evidence_data)

    async def _hydrate_case_details(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        if not doc:
            return doc
        case_id = doc.get("case_id")
        if case_id:
            try:
                case_doc = await self.db["cases"].find_one({"_id": ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id})
                if case_doc:
                    doc["case_number"] = case_doc.get("case_number")
                    doc["case_title"] = case_doc.get("title")
            except Exception:
                pass

        doc.setdefault("original_sha256_hash", doc.get("sha256_hash"))
        doc.setdefault("version", 1)
        doc.setdefault("version_history", [])

        # Check for preserved original backup
        try:
            ev_id = str(doc.get("_id", ""))
            backup_doc = await self.db["evidence_backups"].find_one({"evidence_id": ev_id})
            doc["has_original_backup"] = bool(backup_doc)
            if backup_doc:
                doc["original_sha256_hash"] = backup_doc.get("original_sha256") or doc.get("original_sha256_hash")
                doc["original_backup_created_at"] = backup_doc.get("created_at")
        except Exception:
            doc["has_original_backup"] = False

        return doc

    async def get_by_id(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        try:
            doc = await self.collection.find_one({"_id": ObjectId(evidence_id)})
            if not doc:
                return None
            serialized = self.serialize_doc(doc)
            return await self._hydrate_case_details(serialized)
        except Exception:
            return None

    async def list_by_case(self, case_id: str) -> List[Dict[str, Any]]:
        cursor = self.collection.find({"case_id": case_id}).sort("created_at", -1)
        docs = await cursor.to_list(length=1000)
        hydrated = []
        for doc in docs:
            s = self.serialize_doc(doc)
            hydrated.append(await self._hydrate_case_details(s))
        return hydrated

    async def list_all(
        self,
        search: Optional[str] = None,
        integrity_status: Optional[str] = None,
        case_id: Optional[str] = None,
        allowed_case_ids: Optional[List[str]] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        query: Dict[str, Any] = {}

        if allowed_case_ids is not None:
            if case_id:
                if case_id not in allowed_case_ids:
                    return [], 0
                query["case_id"] = case_id
            else:
                query["case_id"] = {"$in": allowed_case_ids}
        elif case_id:
            query["case_id"] = case_id

        if integrity_status:
            query["integrity_status"] = integrity_status

        if search and search.strip():
            regex = {"$regex": search.strip(), "$options": "i"}
            query["$or"] = [
                {"original_filename": regex},
                {"sha256_hash": regex},
                {"tags": regex},
                {"description": regex}
            ]

        total = await self.collection.count_documents(query)
        cursor = self.collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)

        hydrated = []
        for doc in docs:
            s = self.serialize_doc(doc)
            hydrated.append(await self._hydrate_case_details(s))

        return hydrated, total

    async def update_integrity(
        self,
        evidence_id: str,
        integrity_status: str,
        calculated_hash: str,
        verified_at: datetime
    ) -> Optional[Dict[str, Any]]:
        """
        Update verification status and last calculated hash.
        CRITICAL FORENSIC RULE: Never overwrite original baseline sha256_hash!
        """
        try:
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(evidence_id)},
                {
                    "$set": {
                        "integrity_status": integrity_status,
                        "last_calculated_hash": calculated_hash,
                        "last_verified_at": verified_at
                    }
                },
                return_document=True
            )
            if not result:
                return None
            s = self.serialize_doc(result)
            return await self._hydrate_case_details(s)
        except Exception:
            return None

    async def record_authorized_modification(
        self,
        evidence_id: str,
        new_hash: str,
        new_file_size: int,
        version_entry: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Record an authorized modification as a new version without marking as tampered."""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(evidence_id)})
            if not doc:
                return None
            current_ver = doc.get("version", 1)
            new_ver = current_ver + 1
            now = datetime.now(timezone.utc)

            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(evidence_id)},
                {
                    "$set": {
                        "sha256_hash": new_hash,
                        "last_calculated_hash": new_hash,
                        "file_size": new_file_size,
                        "version": new_ver,
                        "integrity_status": "VERIFIED",
                        "last_verified_at": now
                    },
                    "$push": {
                        "version_history": version_entry
                    }
                },
                return_document=True
            )
            if not result:
                return None
            s = self.serialize_doc(result)
            return await self._hydrate_case_details(s)
        except Exception:
            return None

    async def confirm_tampering(
        self,
        evidence_id: str,
        tamper_details: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Confirm evidence tampering following forensic inquiry."""
        try:
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(evidence_id)},
                {
                    "$set": {
                        "integrity_status": "TAMPERED",
                        "tamper_details": tamper_details,
                        "last_verified_at": datetime.now(timezone.utc)
                    }
                },
                return_document=True
            )
            if not result:
                return None
            s = self.serialize_doc(result)
            return await self._hydrate_case_details(s)
        except Exception:
            return None

    async def get_stats(self, allowed_case_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        base_query: Dict[str, Any] = {}
        if allowed_case_ids is not None:
            base_query["case_id"] = {"$in": allowed_case_ids}

        def make_query(extra: Dict[str, Any]) -> Dict[str, Any]:
            q = dict(base_query)
            q.update(extra)
            return q

        total = await self.collection.count_documents(base_query)
        verified = await self.collection.count_documents(make_query({"integrity_status": "VERIFIED"}))
        tampered = await self.collection.count_documents(make_query({"integrity_status": "TAMPERED"}))
        pending = await self.collection.count_documents(make_query({"integrity_status": "PENDING"}))

        rate = round((verified / total * 100.0), 1) if total > 0 else 100.0

        return {
            "total_evidence": total,
            "verified_evidence": verified,
            "tampered_evidence": tampered,
            "pending_evidence": pending,
            "integrity_rate": rate
        }
