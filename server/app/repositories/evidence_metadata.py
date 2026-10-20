from bson import ObjectId
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from app.repositories.base import BaseRepository

class EvidenceMetadataRepository(BaseRepository):
    @property
    def collection(self):
        return self.db["evidence_metadata"]

    async def create(self, metadata_data: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        if "created_at" not in metadata_data or not metadata_data["created_at"]:
            metadata_data["created_at"] = now
        if "modified_at" not in metadata_data or not metadata_data["modified_at"]:
            metadata_data["modified_at"] = now
        
        result = await self.collection.insert_one(metadata_data)
        metadata_data["_id"] = str(result.inserted_id)
        if "evidence_id" not in metadata_data or not metadata_data["evidence_id"]:
            metadata_data["evidence_id"] = metadata_data["_id"]
            await self.collection.update_one({"_id": result.inserted_id}, {"$set": {"evidence_id": metadata_data["_id"]}})
        return self.serialize_doc(metadata_data)

    async def get_by_id(self, metadata_id: str) -> Optional[Dict[str, Any]]:
        try:
            doc = await self.collection.find_one({"_id": ObjectId(metadata_id)})
            return self.serialize_doc(doc)
        except Exception:
            return None

    async def list_by_case(self, case_id: str) -> List[Dict[str, Any]]:
        cursor = self.collection.find({"case_id": case_id}).sort("created_at", -1)
        docs = await cursor.to_list(length=1000)
        return self.serialize_docs(docs)
