from bson import ObjectId
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from app.repositories.base import BaseRepository
from app.models.backup import BackupStatus


class BackupRepository(BaseRepository):
    """
    Repository for the `evidence_backups` MongoDB collection.
    Manages immutable preserved-original records.
    Physical storage paths are stored in the DB but NEVER returned via API responses.
    """

    @property
    def collection(self):
        return self.db["evidence_backups"]

    async def create(self, backup_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert a new backup record.
        The `storage_path` field in backup_data is stored but is stripped
        before any API serialization (handled in the service layer).
        """
        now = datetime.now(timezone.utc)
        backup_data["created_at"] = now
        backup_data["updated_at"] = now
        result = await self.collection.insert_one(backup_data)
        backup_data["_id"] = str(result.inserted_id)
        return self.serialize_doc(backup_data)

    async def get_by_evidence_id(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        """Get the latest (highest version) backup for a given evidence ID."""
        doc = await self.collection.find_one(
            {"evidence_id": evidence_id},
            sort=[("version", -1)]
        )
        return self.serialize_doc(doc) if doc else None

    async def get_by_backup_id(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Get a backup by its logical backup_id string (e.g. BACKUP-EVD001-V1)."""
        doc = await self.collection.find_one({"backup_id": backup_id})
        if not doc:
            # Also try by MongoDB _id
            if ObjectId.is_valid(backup_id):
                doc = await self.collection.find_one({"_id": ObjectId(backup_id)})
        return self.serialize_doc(doc) if doc else None

    async def list_by_case(self, case_id: str) -> List[Dict[str, Any]]:
        """List all backup records for a case, newest first."""
        cursor = self.collection.find({"case_id": case_id}).sort("created_at", -1)
        docs = await cursor.to_list(length=1000)
        return [self.serialize_doc(d) for d in docs]

    async def list_by_evidence(self, evidence_id: str) -> List[Dict[str, Any]]:
        """List all backup versions for a given evidence item."""
        cursor = self.collection.find({"evidence_id": evidence_id}).sort("version", -1)
        docs = await cursor.to_list(length=100)
        return [self.serialize_doc(d) for d in docs]

    async def update_status(
        self,
        backup_id: str,
        status: BackupStatus,
        calculated_sha256: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update backup integrity status after a re-verification."""
        update: Dict[str, Any] = {
            "status": status.value,
            "updated_at": datetime.now(timezone.utc)
        }
        if calculated_sha256 is not None:
            update["last_verified_sha256"] = calculated_sha256
            update["last_verified_at"] = datetime.now(timezone.utc)

        result = await self.collection.find_one_and_update(
            {"backup_id": backup_id},
            {"$set": update},
            return_document=True
        )
        return self.serialize_doc(result) if result else None

    async def count_by_evidence(self, evidence_id: str) -> int:
        return await self.collection.count_documents({"evidence_id": evidence_id})

    async def exists_for_evidence(self, evidence_id: str) -> bool:
        return await self.count_by_evidence(evidence_id) > 0
