from bson import ObjectId
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from pymongo import ReturnDocument
from app.repositories.base import BaseRepository

class CaseRepository(BaseRepository):
    @property
    def collection(self):
        return self.db["cases"]

    async def generate_case_number(self) -> str:
        """Atomically generate unique human-readable case number: DF-YYYY-XXXXXX"""
        year = datetime.now(timezone.utc).year
        while True:
            counter = await self.db["counters"].find_one_and_update(
                {"_id": f"case_number_{year}"},
                {"$inc": {"seq": 1}},
                upsert=True,
                return_document=ReturnDocument.AFTER
            )
            seq = counter.get("seq", 1)
            case_num = f"DF-{year}-{seq:06d}"
            existing = await self.collection.find_one({"case_number": case_num})
            if not existing:
                return case_num

    async def create(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        case_data["case_number"] = await self.generate_case_number()
        case_data["created_at"] = now
        case_data["updated_at"] = now
        case_data["closed_at"] = None
        if "notes" not in case_data:
            case_data["notes"] = []
        if "tags" not in case_data:
            case_data["tags"] = []

        result = await self.collection.insert_one(case_data)
        case_data["_id"] = str(result.inserted_id)
        return self.serialize_doc(case_data)

    async def _hydrate_user_names(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        if not doc:
            return doc
        # Hydrate created_by_name
        if doc.get("created_by"):
            try:
                creator = await self.db["users"].find_one({"_id": ObjectId(doc["created_by"]) if isinstance(doc["created_by"], str) else doc["created_by"]})
                if creator:
                    doc["created_by_name"] = creator.get("name")
            except Exception:
                pass
        # Hydrate assigned_investigator_name
        if doc.get("assigned_investigator"):
            try:
                assignee = await self.db["users"].find_one({"_id": ObjectId(doc["assigned_investigator"]) if isinstance(doc["assigned_investigator"], str) else doc["assigned_investigator"]})
                if assignee:
                    doc["assigned_investigator_name"] = assignee.get("name")
            except Exception:
                pass
        return doc

    async def get_by_id(self, case_id: str) -> Optional[Dict[str, Any]]:
        doc = None
        try:
            doc = await self.collection.find_one({"_id": ObjectId(case_id)})
        except Exception:
            pass
        if not doc:
            # Fallback check by case_number
            doc = await self.collection.find_one({"case_number": case_id})
        if not doc:
            return None
        serialized = self.serialize_doc(doc)
        return await self._hydrate_user_names(serialized)

    async def list_cases(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        case_type: Optional[str] = None,
        assigned_investigator: Optional[str] = None,
        include_archived: bool = False,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        query: Dict[str, Any] = {}

        if status:
            query["status"] = status
        elif not include_archived:
            query["status"] = {"$ne": "ARCHIVED"}

        if priority:
            query["priority"] = priority

        if case_type:
            query["case_type"] = case_type

        if assigned_investigator:
            query["assigned_investigator"] = assigned_investigator

        # Scope query to user if user_id is provided (non-admin)
        and_clauses: List[Dict[str, Any]] = []

        if user_id:
            uids = [user_id]
            if ObjectId.is_valid(user_id):
                uids.append(ObjectId(user_id))
            and_clauses.append({
                "$or": [
                    {"created_by": {"$in": uids}},
                    {"assigned_investigator": {"$in": uids}}
                ]
            })

        if search and search.strip():
            regex = {"$regex": search.strip(), "$options": "i"}
            and_clauses.append({
                "$or": [
                    {"case_number": regex},
                    {"title": regex},
                    {"description": regex},
                    {"tags": regex}
                ]
            })

        if and_clauses:
            if len(and_clauses) == 1:
                query.update(and_clauses[0])
            else:
                query["$and"] = and_clauses

        total = await self.collection.count_documents(query)
        cursor = self.collection.find(query).sort("created_at", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)

        hydrated = []
        for doc in docs:
            serialized = self.serialize_doc(doc)
            hydrated.append(await self._hydrate_user_names(serialized))

        return hydrated, total

    async def update(self, case_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        update_data["updated_at"] = datetime.now(timezone.utc)
        try:
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(case_id)},
                {"$set": update_data},
                return_document=ReturnDocument.AFTER
            )
            if not result:
                return None
            serialized = self.serialize_doc(result)
            return await self._hydrate_user_names(serialized)
        except Exception:
            return None

    async def update_status(self, case_id: str, status: str) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        update_fields: Dict[str, Any] = {
            "status": status,
            "updated_at": now
        }
        if status in ("CLOSED", "ARCHIVED"):
            update_fields["closed_at"] = now
        else:
            update_fields["closed_at"] = None

        try:
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(case_id)},
                {"$set": update_fields},
                return_document=ReturnDocument.AFTER
            )
            if not result:
                return None
            serialized = self.serialize_doc(result)
            return await self._hydrate_user_names(serialized)
        except Exception:
            return None

    async def add_note(self, case_id: str, note: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        try:
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(case_id)},
                {
                    "$push": {"notes": note},
                    "$set": {"updated_at": now}
                },
                return_document=ReturnDocument.AFTER
            )
            if not result:
                return None
            serialized = self.serialize_doc(result)
            return await self._hydrate_user_names(serialized)
        except Exception:
            return None

    async def archive(self, case_id: str) -> bool:
        """Soft-delete for chain of custody compliance"""
        now = datetime.now(timezone.utc)
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(case_id)},
                {"$set": {"status": "ARCHIVED", "closed_at": now, "updated_at": now}}
            )
            return result.modified_count > 0
        except Exception:
            return False

    async def get_stats(self, user_id: Optional[str] = None) -> Dict[str, int]:
        pipeline = []
        user_filter: Optional[Dict[str, Any]] = None

        if user_id:
            uids = [user_id]
            if ObjectId.is_valid(user_id):
                uids.append(ObjectId(user_id))
            user_filter = {
                "$or": [
                    {"created_by": {"$in": uids}},
                    {"assigned_investigator": {"$in": uids}}
                ]
            }
            pipeline.append({"$match": user_filter})

        pipeline.append({
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }
        })

        status_counts: Dict[str, int] = {}
        async for item in self.collection.aggregate(pipeline):
            status_counts[item["_id"]] = item["count"]

        # Critical active cases
        critical_query: Dict[str, Any] = {
            "priority": "CRITICAL",
            "status": {"$nin": ["CLOSED", "ARCHIVED"]}
        }
        if user_filter:
            critical_query = {"$and": [critical_query, user_filter]}

        critical_count = await self.collection.count_documents(critical_query)

        total = sum(status_counts.values())
        archived = status_counts.get("ARCHIVED", 0)
        open_c = status_counts.get("OPEN", 0)
        in_prog = status_counts.get("IN_PROGRESS", 0)
        closed_c = status_counts.get("CLOSED", 0)

        return {
            "total_cases": total - archived,
            "active_cases": open_c + in_prog,
            "open_cases": open_c,
            "critical_cases": critical_count,
            "closed_cases": closed_c,
            "archived_cases": archived
        }
