from bson import ObjectId
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from app.repositories.base import BaseRepository

class AuditRepository(BaseRepository):
    @property
    def collection(self):
        return self.db["audit_logs"]

    async def create_log(
        self,
        user_id: Optional[str],
        action: str,
        ip_address: str,
        user_agent: str,
        device_id: str = "WEB_APP",
        case_id: Optional[str] = None,
        evidence_id: Optional[str] = None,
        details: str = ""
    ) -> Dict[str, Any]:
        parsed_user_id = None
        if user_id:
            try:
                parsed_user_id = ObjectId(user_id) if isinstance(user_id, str) else user_id
            except Exception:
                parsed_user_id = user_id

        parsed_case_id = None
        if case_id:
            try:
                parsed_case_id = ObjectId(case_id) if isinstance(case_id, str) else case_id
            except Exception:
                parsed_case_id = case_id

        parsed_evidence_id = None
        if evidence_id:
            try:
                parsed_evidence_id = ObjectId(evidence_id) if isinstance(evidence_id, str) else evidence_id
            except Exception:
                parsed_evidence_id = evidence_id

        log_entry = {
            "user_id": parsed_user_id,
            "action": action,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "device_id": device_id,
            "case_id": parsed_case_id,
            "evidence_id": parsed_evidence_id,
            "details": details,
            "timestamp": datetime.now(timezone.utc)
        }
        result = await self.collection.insert_one(log_entry)
        log_entry["_id"] = str(result.inserted_id)
        return self.serialize_doc(log_entry)

    async def list_logs(self, case_id: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
        query = {}
        if case_id:
            try:
                query["case_id"] = ObjectId(case_id)
            except Exception:
                pass
        
        cursor = self.collection.find(query).sort("timestamp", -1)
        docs = await cursor.to_list(length=limit)
        
        # Hydrate user details by joining with users
        hydrated_logs = []
        for doc in docs:
            serialized = self.serialize_doc(doc)
            if doc.get("user_id"):
                user_doc = await self.db["users"].find_one({"_id": doc["user_id"]})
                if user_doc:
                    serialized["user_name"] = user_doc.get("name")
                    serialized["user_email"] = user_doc.get("email")
            hydrated_logs.append(serialized)
            
        return hydrated_logs
