from bson import ObjectId
from typing import Optional, List, Dict, Any
from app.repositories.base import BaseRepository

class UserRepository(BaseRepository):
    @property
    def collection(self):
        return self.db["users"]

    async def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            doc = await self.collection.find_one({"_id": ObjectId(user_id)})
            return self.serialize_doc(doc)
        except Exception:
            return None

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        clean = email.strip().lower()
        # 1. Direct match on email
        doc = await self.collection.find_one({"email": clean})
        if doc:
            return self.serialize_doc(doc)
            
        # 2. Match with @forensics.gov or @forensic.gov suffix if plain username entered
        if "@" not in clean:
            doc = await self.collection.find_one({"email": f"{clean}@forensics.gov"})
            if doc:
                return self.serialize_doc(doc)
                
            doc = await self.collection.find_one({"email": f"{clean}@forensic.gov"})
            if doc:
                return self.serialize_doc(doc)

            # Match prefix before @ in registered email
            doc = await self.collection.find_one({"email": {"$regex": f"^{clean}@", "$options": "i"}})
            if doc:
                return self.serialize_doc(doc)
                
            # 3. Match by name
            doc = await self.collection.find_one({"name": {"$regex": f"^{clean}$", "$options": "i"}})
            if doc:
                return self.serialize_doc(doc)

            doc = await self.collection.find_one({"name": {"$regex": clean, "$options": "i"}})
            if doc:
                return self.serialize_doc(doc)

        return None

    async def get_by_rfid(self, rfid: str) -> Optional[Dict[str, Any]]:
        clean = rfid.replace(" ", "").replace(":", "").replace("-", "").upper()
        # Flexible pattern matching with or without spaces/delimiters
        pattern = "^" + "".join([f"{clean[i:i+2]}[ :\\-]?" for i in range(0, len(clean), 2)]) + "$" if len(clean) >= 4 else clean
        doc = await self.collection.find_one({
            "$or": [
                {"rfid": rfid},
                {"rfid": clean},
                {"rfid": {"$regex": f"^{clean}$", "$options": "i"}},
                {"rfid": {"$regex": pattern, "$options": "i"}}
            ]
        })
        return self.serialize_doc(doc)

    async def get_by_fingerprint(self, fingerprint_id: Any) -> Optional[Dict[str, Any]]:
        try:
            fid = int(fingerprint_id)
        except (ValueError, TypeError):
            fid = fingerprint_id
        doc = await self.collection.find_one({
            "$or": [
                {"fingerprint_id": fid},
                {"fingerprint_id": str(fid)}
            ]
        })
        return self.serialize_doc(doc)

    async def create(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        user_data["email"] = user_data["email"].lower()
        result = await self.collection.insert_one(user_data)
        user_data["_id"] = str(result.inserted_id)
        return user_data

    async def update(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(user_id)}, 
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception:
            return False

    async def list_users(self) -> List[Dict[str, Any]]:
        cursor = self.collection.find()
        docs = await cursor.to_list(length=1000)
        return self.serialize_docs(docs)

    async def delete(self, user_id: str) -> bool:
        try:
            result = await self.collection.delete_one({"_id": ObjectId(user_id)})
            return result.deleted_count > 0
        except Exception:
            return False
