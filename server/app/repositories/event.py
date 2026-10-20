from bson import ObjectId
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from app.repositories.base import BaseRepository

class EventRepository(BaseRepository):
    @property
    def collection(self):
        return self.db["forensic_events"]

    async def create(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        event_data["created_at"] = now
        if "tags" not in event_data:
            event_data["tags"] = []
        if "metadata" not in event_data:
            event_data["metadata"] = {}

        result = await self.collection.insert_one(event_data)
        event_data["_id"] = str(result.inserted_id)
        event_data["event_id"] = str(result.inserted_id)
        serialized = self.serialize_doc(event_data)
        return await self._hydrate_evidence(serialized)

    async def _hydrate_evidence(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        if not doc:
            return doc
        ev_id = doc.get("evidence_id")
        if ev_id:
            try:
                ev_doc = await self.db["evidence"].find_one({"_id": ObjectId(ev_id) if ObjectId.is_valid(ev_id) else ev_id})
                if ev_doc:
                    doc["evidence_filename"] = ev_doc.get("original_filename")
            except Exception:
                pass
        return doc

    async def get_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        try:
            doc = await self.collection.find_one({"_id": ObjectId(event_id)})
            if not doc:
                return None
            serialized = self.serialize_doc(doc)
            serialized["event_id"] = serialized["_id"]
            return await self._hydrate_evidence(serialized)
        except Exception:
            return None

    async def update(self, event_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            clean_update = {k: v for k, v in update_data.items() if v is not None}
            if not clean_update:
                return await self.get_by_id(event_id)

            clean_update["updated_at"] = datetime.now(timezone.utc)
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(event_id)},
                {"$set": clean_update},
                return_document=True
            )
            if not result:
                return None
            serialized = self.serialize_doc(result)
            serialized["event_id"] = serialized["_id"]
            return await self._hydrate_evidence(serialized)
        except Exception:
            return None

    async def list_by_case(
        self,
        case_id: str,
        query_filters: Optional[Dict[str, Any]] = None,
        sort_field: str = "event_time",
        sort_order: int = 1,
        skip: int = 0,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        query = {"case_id": case_id}
        if query_filters:
            query.update(query_filters)

        cursor = self.collection.find(query).sort(sort_field, sort_order).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)

        hydrated = []
        for doc in docs:
            s = self.serialize_doc(doc)
            s["event_id"] = s["_id"]
            hydrated.append(await self._hydrate_evidence(s))
        return hydrated

    async def count_by_case(self, case_id: str, query_filters: Optional[Dict[str, Any]] = None) -> int:
        query = {"case_id": case_id}
        if query_filters:
            query.update(query_filters)
        return await self.collection.count_documents(query)
