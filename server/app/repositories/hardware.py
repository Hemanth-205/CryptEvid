import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from app.repositories.base import BaseRepository

logger = logging.getLogger("hardware.repository")

class HardwareRepository(BaseRepository):
    @property
    def events_collection(self):
        return self.db["hardware_events"]

    @property
    def state_collection(self):
        return self.db["hardware_bridge_state"]

    async def create_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a validated hardware serial event into hardware_events collection."""
        try:
            if "timestamp" not in event_data or not event_data["timestamp"]:
                event_data["timestamp"] = datetime.now(timezone.utc)
            
            result = await self.events_collection.insert_one(event_data)
            event_data["_id"] = str(result.inserted_id)

            # Update latest event in bridge state collection
            await self.state_collection.update_one(
                {"key": "bridge_status"},
                {"$set": {
                    "last_event": self.serialize_doc(event_data),
                    "last_event_at": datetime.now(timezone.utc)
                }},
                upsert=True
            )
            return self.serialize_doc(event_data)
        except Exception as e:
            logger.error(f"Failed to persist hardware event: {e}")
            raise

    async def list_events(self, limit: int = 50, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List recent hardware authentication events in descending chronological order."""
        try:
            query = {}
            if status_filter:
                query["status"] = status_filter.upper()
            cursor = self.events_collection.find(query).sort("timestamp", -1).limit(limit)
            docs = await cursor.to_list(length=limit)
            return self.serialize_docs(docs)
        except Exception as e:
            logger.error(f"Failed to list hardware events: {e}")
            return []

    async def get_latest_event(self) -> Optional[Dict[str, Any]]:
        """Get the single most recent hardware authentication event."""
        try:
            doc = await self.events_collection.find_one(sort=[("timestamp", -1)])
            return self.serialize_doc(doc) if doc else None
        except Exception as e:
            logger.error(f"Failed to fetch latest hardware event: {e}")
            return None

    async def update_bridge_heartbeat(
        self,
        port: str,
        status: str,
        baud_rate: int = 115200,
        device_id: str = "ESP32_USB",
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update the bridge heartbeat, active COM port, and diagnostic health status."""
        try:
            now = datetime.now(timezone.utc)
            update_data = {
                "key": "bridge_status",
                "port": port,
                "status": status,
                "baud_rate": baud_rate,
                "device_id": device_id,
                "error_message": error_message,
                "last_heartbeat": now
            }
            await self.state_collection.update_one(
                {"key": "bridge_status"},
                {"$set": update_data},
                upsert=True
            )
            return update_data
        except Exception as e:
            logger.error(f"Failed to update bridge heartbeat: {e}")
            return {}

    async def get_bridge_state(self) -> Optional[Dict[str, Any]]:
        """Retrieve stored bridge status from database."""
        try:
            doc = await self.state_collection.find_one({"key": "bridge_status"})
            return self.serialize_doc(doc) if doc else None
        except Exception as e:
            logger.error(f"Failed to retrieve bridge state: {e}")
            return None
