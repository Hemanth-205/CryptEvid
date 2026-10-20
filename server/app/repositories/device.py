from bson import ObjectId
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from app.repositories.base import BaseRepository

class DeviceRepository(BaseRepository):
    @property
    def collection(self):
        return self.db["devices"]

    async def get_by_device_id(self, device_id: str) -> Optional[Dict[str, Any]]:
        doc = await self.collection.find_one({"device_id": device_id})
        return self.serialize_doc(doc)

    async def register_device(self, device_id: str, mac_address: str, firmware_version: str) -> Dict[str, Any]:
        existing = await self.get_by_device_id(device_id)
        if existing:
            update_data = {
                "mac_address": mac_address,
                "firmware_version": firmware_version,
                "status": "online",
                "last_seen": datetime.now(timezone.utc)
            }
            await self.collection.update_one({"device_id": device_id}, {"$set": update_data})
            existing.update(update_data)
            return existing

        new_device = {
            "device_id": device_id,
            "mac_address": mac_address,
            "firmware_version": firmware_version,
            "status": "online",
            "last_seen": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc)
        }
        result = await self.collection.insert_one(new_device)
        new_device["_id"] = str(result.inserted_id)
        return new_device

    async def update_status(self, device_id: str, status: str) -> bool:
        result = await self.collection.update_one(
            {"device_id": device_id},
            {"$set": {"status": status, "last_seen": datetime.now(timezone.utc)}}
        )
        return result.modified_count > 0

    async def list_devices(self) -> List[Dict[str, Any]]:
        cursor = self.collection.find()
        docs = await cursor.to_list(length=1000)
        return self.serialize_docs(docs)

    async def delete(self, device_id: str) -> bool:
        result = await self.collection.delete_one({"device_id": device_id})
        return result.deleted_count > 0
