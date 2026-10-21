import logging
from typing import Optional, List, Dict, Any, Tuple
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

    @property
    def tickets_collection(self):
        return self.db["hardware_auth_tickets"]

    async def create_auth_ticket(
        self,
        uid: str,
        user_id: str,
        user_email: str,
        user_name: str,
        user_role: str,
        ttl_seconds: int = 300
    ) -> Dict[str, Any]:
        """
        Generate a cryptographically unique single-use challenge ticket
        binding the verified Stage 1 hardware scan to an investigator identity.
        """
        import uuid
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl_seconds)
        ticket_id = f"hw_ticket_{uuid.uuid4().hex}"

        doc = {
            "ticket_id": ticket_id,
            "uid": uid,
            "user_id": user_id,
            "user_email": user_email.lower(),
            "user_name": user_name,
            "user_role": user_role,
            "status": "VALID",
            "created_at": now,
            "expires_at": expires_at,
            "consumed_at": None
        }

        try:
            await self.tickets_collection.insert_one(doc)
            # Store in memory for instant lookup and fallback
            serialized = self.serialize_doc(doc)
            serialized["expires_in_seconds"] = int((expires_at - now).total_seconds())
            return serialized
        except Exception as e:
            logger.error(f"Failed to create hardware auth ticket: {e}")
            raise

    async def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a ticket by its unique ticket_id."""
        try:
            doc = await self.tickets_collection.find_one({"ticket_id": ticket_id})
            return self.serialize_doc(doc) if doc else None
        except Exception as e:
            logger.error(f"Failed to fetch ticket {ticket_id}: {e}")
            return None

    async def verify_ticket_only(
        self,
        ticket_id: Optional[str],
        email: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Verify that a hardware ticket exists, is VALID, is not expired, and matches the email,
        WITHOUT consuming it yet.
        """
        if not ticket_id or not ticket_id.strip():
            return False, "Hardware verification challenge ticket is required. Please complete Stage 1 Hardware Authentication first.", None

        clean_id = ticket_id.strip()
        clean_email = email.strip().lower()
        now = datetime.now(timezone.utc)

        try:
            doc = await self.tickets_collection.find_one({"ticket_id": clean_id})
            if not doc:
                return False, "Hardware verification ticket was not found or has already been consumed.", None

            if doc.get("status") != "VALID":
                return False, f"Hardware verification ticket has already been {doc.get('status', 'consumed').lower()}.", None

            expires_at = doc.get("expires_at")
            if expires_at:
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if now > expires_at:
                    await self.tickets_collection.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"status": "EXPIRED"}}
                    )
                    return False, "Hardware verification ticket has expired (validity is 5 minutes). Please re-authenticate on the ESP32 hardware.", None

            ticket_email = doc.get("user_email", "").strip().lower()
            if ticket_email != clean_email:
                return False, f"Hardware ticket was issued for investigator '{ticket_email}', but software login was attempted with '{clean_email}'.", None

            return True, "Ticket is valid.", self.serialize_doc(doc)
        except Exception as e:
            logger.error(f"Error checking ticket {clean_id}: {e}")
            return False, f"Database error during ticket check: {str(e)}", None

    async def consume_ticket(self, ticket_id: str) -> bool:
        """Atomically mark ticket as CONSUMED."""
        clean_id = ticket_id.strip()
        now = datetime.now(timezone.utc)
        try:
            res = await self.tickets_collection.update_one(
                {"ticket_id": clean_id, "status": "VALID"},
                {"$set": {"status": "CONSUMED", "consumed_at": now}}
            )
            return res.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to consume ticket {clean_id}: {e}")
            return False

    async def validate_and_consume_ticket(
        self,
        ticket_id: Optional[str],
        email: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Securely validate and atomically consume a hardware challenge ticket for Stage 2 software login.
        Validates:
        1. Ticket existence
        2. Status is 'VALID' (single-use enforcement)
        3. Non-expired TTL (< 5 minutes)
        4. User identity binding (ticket must match the investigator email logging in)
        """
        if not ticket_id or not ticket_id.strip():
            return False, "Hardware verification challenge ticket is required. Please complete Stage 1 Hardware Authentication first.", None

        clean_id = ticket_id.strip()
        clean_email = email.strip().lower()
        now = datetime.now(timezone.utc)

        try:
            doc = await self.tickets_collection.find_one({"ticket_id": clean_id})
            if not doc:
                return False, "Hardware verification ticket was not found or has been consumed.", None

            if doc.get("status") != "VALID":
                return False, f"Hardware verification ticket has already been {doc.get('status', 'consumed').lower()}.", None

            expires_at = doc.get("expires_at")
            if expires_at:
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if now > expires_at:
                    await self.tickets_collection.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"status": "EXPIRED"}}
                    )
                    return False, "Hardware verification ticket has expired (validity is 5 minutes). Please re-authenticate on the ESP32 hardware.", None

            ticket_email = doc.get("user_email", "").strip().lower()
            if ticket_email != clean_email:
                return False, f"Hardware ticket was issued for investigator '{ticket_email}', but software login was attempted with '{clean_email}'.", None

            # Atomically mark ticket consumed so it can NEVER be reused or replayed
            update_res = await self.tickets_collection.update_one(
                {"_id": doc["_id"], "status": "VALID"},
                {"$set": {
                    "status": "CONSUMED",
                    "consumed_at": now
                }}
            )

            if update_res.modified_count == 0:
                return False, "Hardware ticket was already consumed by a concurrent login attempt.", None

            doc["status"] = "CONSUMED"
            doc["consumed_at"] = now
            return True, "Hardware ticket successfully validated and consumed.", self.serialize_doc(doc)

        except Exception as e:
            logger.error(f"Error validating hardware ticket {clean_id}: {e}")
            return False, f"Database error during hardware ticket validation: {str(e)}", None

    async def get_latest_valid_ticket(self) -> Optional[Dict[str, Any]]:
        """Retrieve the latest unconsumed, unexpired hardware authentication ticket."""
        now = datetime.now(timezone.utc)
        try:
            doc = await self.tickets_collection.find_one(
                {"status": "VALID", "expires_at": {"$gt": now}},
                sort=[("created_at", -1)]
            )
            if doc:
                serialized = self.serialize_doc(doc)
                exp = doc["expires_at"]
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                serialized["expires_in_seconds"] = max(0, int((exp - now).total_seconds()))
                return serialized
            return None
        except Exception as e:
            logger.error(f"Failed to fetch latest valid ticket: {e}")
            return None

    async def invalidate_all_tickets_for_user(self, email: str):
        """Revoke all active tickets for a user upon logout."""
        now = datetime.now(timezone.utc)
        try:
            await self.tickets_collection.update_many(
                {"user_email": email.strip().lower(), "status": "VALID"},
                {"$set": {"status": "REVOKED", "revoked_at": now}}
            )
        except Exception as e:
            logger.error(f"Failed to revoke tickets for {email}: {e}")
