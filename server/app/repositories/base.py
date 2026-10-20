from bson import ObjectId
from typing import Any, Dict, List

class BaseRepository:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
        """Convert MongoDB document ObjectId into string id for API response compatibility."""
        if not doc:
            return doc
        serialized = doc.copy()
        if "_id" in serialized:
            serialized["_id"] = str(serialized["_id"])
        # Recursively serialize nested objects or lists if needed
        for key, value in serialized.items():
            if isinstance(value, ObjectId):
                serialized[key] = str(value)
            elif isinstance(value, list):
                serialized[key] = [
                    str(item) if isinstance(item, ObjectId) else item for item in value
                ]
        return serialized

    @staticmethod
    def serialize_docs(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [BaseRepository.serialize_doc(doc) for doc in docs if doc]
