import asyncio
from datetime import datetime, timezone
from app.core.database import get_database
from app.core.security import get_password_hash, verify_password

async def ensure_default_users():
    """
    Ensures default forensic investigators and admin credentials always exist 
    and have valid BCrypt hashes for seamless login.
    """
    try:
        db = get_database()
        # Verify MongoDB responsiveness before bootstrapping
        try:
            await asyncio.wait_for(db.command("ping"), timeout=3.0)
        except Exception as e:
            print(f"[BOOTSTRAP] MongoDB connection not immediately responsive ({e}). Deferred user seeding until first database request.")
            return

        users_col = db["users"]
        settings_col = db["settings"]
        devices_col = db["devices"]

        # 1. Ensure Global Settings
        existing_settings = await settings_col.find_one({"key": "global_config"})
        if not existing_settings:
            await settings_col.insert_one({
                "key": "global_config",
                "simulation_mode": True,
                "gemini_api_key": "",
                "updated_at": datetime.now(timezone.utc)
            })
            print("[BOOTSTRAP] Initialized global_config with simulation_mode=True.")

        # Default users list configured with physical hardware IDs
        default_accounts = [
            {
                "email": "admin@forensics.gov",
                "name": "System Administrator",
                "role": "admin",
                "password": "password123",
                "rfid": "105B965C",
                "fingerprint_id": 6,
                "is_active": True
            },
            {
                "email": "chief@forensics.gov",
                "name": "Chief Investigator",
                "role": "chief_investigator",
                "password": "password123",
                "rfid": "105B965C",
                "fingerprint_id": 15,
                "is_active": True
            },
            {
                "email": "investigator@forensics.gov",
                "name": "Forensic Analyst",
                "role": "investigator",
                "password": "password123",
                "rfid": "C0A3CF54",
                "fingerprint_id": 2,
                "is_active": True
            },
            {
                "email": "viewer@forensics.gov",
                "name": "Court Auditor (Read-Only)",
                "role": "readonly",
                "password": "password123",
                "rfid": "C3D4E5F6",
                "fingerprint_id": 20,
                "is_active": True
            }
        ]

        # Purge deprecated portal_manager account if present
        await users_col.delete_many({"email": "manager@forensics.gov"})

        for acc in default_accounts:
            existing = await users_col.find_one({"email": acc["email"]})
            if not existing:
                doc = {
                    "email": acc["email"],
                    "name": acc["name"],
                    "role": acc["role"],
                    "hashed_password": get_password_hash(acc["password"]),
                    "rfid": acc["rfid"],
                    "fingerprint_id": acc["fingerprint_id"],
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc)
                }
                await users_col.insert_one(doc)
                print(f"[BOOTSTRAP] Created default user: {acc['email']}")
            else:
                # Synchronize password hash and update RFID/Fingerprint credentials
                update_fields = {
                    "rfid": acc["rfid"],
                    "fingerprint_id": acc["fingerprint_id"],
                    "is_active": True
                }
                h = existing.get("hashed_password", "")
                if not verify_password("password123", h) and not verify_password("admin123", h):
                    update_fields["hashed_password"] = get_password_hash("password123")

                await users_col.update_one(
                    {"_id": existing["_id"]},
                    {"$set": update_fields}
                )
                print(f"[BOOTSTRAP] Synchronized RFID ({acc['rfid']}) & Fingerprint ({acc['fingerprint_id']}) for: {acc['email']}")

        # 2. Ensure ESP32 Ingestion Nodes
        devices_to_register = [
            {
                "device_id": "ESP32_01",
                "name": "Forensic Ingestion Node 01",
                "mac_address": "DA:51:53:00:95:7C",
                "ip_address": "192.168.4.1",
                "firmware_version": "v1.0.4-forensic",
                "status": "online"
            },
            {
                "device_id": "ESP32_WIFI",
                "name": "Forensic Wireless Node (ESP32_WIFI)",
                "mac_address": "DA:51:53:00:95:7C",
                "ip_address": "192.168.4.1",
                "firmware_version": "v1.0.4-forensic",
                "status": "online"
            }
        ]
        for dev in devices_to_register:
            dev_existing = await devices_col.find_one({"device_id": dev["device_id"]})
            if not dev_existing:
                await devices_col.insert_one({
                    **dev,
                    "last_seen": datetime.now(timezone.utc),
                    "registered_at": datetime.now(timezone.utc)
                })
                print(f"[BOOTSTRAP] Registered hardware device: {dev['device_id']}")
            else:
                await devices_col.update_one(
                    {"device_id": dev["device_id"]},
                    {"$set": {
                        "mac_address": dev["mac_address"],
                        "ip_address": dev["ip_address"],
                        "status": "online",
                        "last_seen": datetime.now(timezone.utc)
                    }}
                )

        print("[BOOTSTRAP] Database verification & user initialization complete.")
        # Ensure default demonstration cases exist
        await ensure_demo_cases()
    except Exception as e:
        print(f"[BOOTSTRAP_ERR] Error initializing default users: {e}")

async def ensure_demo_cases():
    """
    Ensures demonstration cases, including the tampered evidence inquiry with
    preserved immutable backup, are present in the investigator portal across all deployments.
    """
    try:
        from app.core.config import settings
        import os, hashlib
        from bson import ObjectId

        db = get_database()
        cases_col = db["cases"]
        evidence_col = db["evidence"]
        metadata_col = db["evidence_metadata"]
        backups_col = db["evidence_backups"]
        custody_col = db["chain_of_custody"]

        chief = await db["users"].find_one({"email": "chief@forensics.gov"})
        if not chief:
            chief = await db["users"].find_one({"email": "admin@forensics.gov"})
        if not chief:
            return

        chief_id = str(chief["_id"])
        chief_name = chief.get("name", "Chief Investigator")

        # 1. Purge legacy removed case if present
        await cases_col.delete_many({"case_number": "DF-2026-000102"})

        # 2. Check if Demo Tampered Case exists
        existing_tampered = await cases_col.find_one({
            "$or": [
                {"title": {"$regex": "Operation Phoenix Vault", "$options": "i"}},
                {"case_number": "DF-2026-000002"}
            ]
        })

        genuine_bytes = (
            b"Transaction_ID,Timestamp,Sender,Beneficiary,Routing_SWIFT,Amount_USD,Authorization,Status\n"
            b"PHX-2026-001,2026-10-29T00:30:00Z,Federal Reserve NY,Apex Escrow Custody,APEXUS33,5250000.00,AUTH_GENUINE_EXEC,SETTLED\n"
            b"PHX-2026-002,2026-10-29T00:45:00Z,Federal Reserve NY,Standard Chartered London,SCBLGB2L,1800000.00,AUTH_GENUINE_EXEC,SETTLED\n"
        )
        tampered_bytes = (
            b"Transaction_ID,Timestamp,Sender,Beneficiary,Routing_SWIFT,Amount_USD,Authorization,Status\n"
            b"PHX-2026-001,2026-10-29T00:30:00Z,Federal Reserve NY,Rogue Cayman Shell Corp,CYMBKY99,9999999.00,AUTH_HACKED_BY_INSIDER,CONFIRMED_FRAUD\n"
            b"PHX-2026-002,2026-10-29T00:45:00Z,Federal Reserve NY,Standard Chartered London,SCBLGB2L,1800000.00,AUTH_GENUINE_EXEC,SETTLED\n"
        )
        genuine_hash = hashlib.sha256(genuine_bytes).hexdigest().lower()
        tampered_hash = hashlib.sha256(tampered_bytes).hexdigest().lower()
        now = datetime.now(timezone.utc)

        if not existing_tampered:
            case_id = str(ObjectId())
            case_doc = {
                "_id": ObjectId(case_id),
                "case_number": "DF-2026-000002",
                "title": "Operation Phoenix Vault — Unauthorized Treasury Tampering Inquiry",
                "description": "High-security forensic inquiry into unauthorized treasury ledger byte tampering. Active disk file contains mutated beneficiary records; authentic original evidence is preserved in immutable backup storage.",
                "status": "OPEN",
                "priority": "CRITICAL",
                "case_type": "FINANCIAL_FRAUD",
                "tags": ["TREASURY", "TAMPER_INVESTIGATION", "FINANCIAL_FRAUD", "LIVE_DEMO"],
                "created_by": ObjectId(chief_id),
                "created_by_name": chief_name,
                "assigned_investigator": ObjectId(chief_id),
                "assigned_investigator_name": chief_name,
                "created_at": now - timedelta(days=2),
                "updated_at": now,
                "notes": [
                    {
                        "content": "Cryptographic discrepancy detected on treasury ledger exhibit during periodic vault audit.",
                        "author": chief_name,
                        "created_at": now - timedelta(hours=8)
                    }
                ]
            }
            await cases_col.insert_one(case_doc)
            print(f"[BOOTSTRAP] Seeded Demo Tampered Case: DF-2026-000002 ({case_id})")
        else:
            case_id = str(existing_tampered["_id"])

        # Check evidence exhibit
        evidence_doc = await evidence_col.find_one({
            "case_id": case_id,
            "original_filename": "phoenix_treasury_ledger_oct2026.csv"
        })

        working_dir = os.path.abspath(os.path.join(settings.EVIDENCE_STORAGE_DIR, case_id))
        backup_dir = os.path.abspath(os.path.join(settings.BACKUP_STORAGE_DIR, case_id, "BACKUP-EVDPhoenix-V1"))
        os.makedirs(working_dir, exist_ok=True)
        os.makedirs(backup_dir, exist_ok=True)

        backup_path = os.path.join(backup_dir, "phoenix_treasury_ledger_oct2026.csv")
        with open(backup_path, "wb") as f:
            f.write(genuine_bytes)

        if not evidence_doc:
            evidence_id = str(ObjectId())
            sub_dir = os.path.join(working_dir, evidence_id)
            os.makedirs(sub_dir, exist_ok=True)
            working_path = os.path.join(sub_dir, "phoenix_treasury_ledger_oct2026.csv")

            with open(working_path, "wb") as f:
                f.write(tampered_bytes)

            evidence_doc = {
                "_id": ObjectId(evidence_id),
                "case_id": case_id,
                "original_filename": "phoenix_treasury_ledger_oct2026.csv",
                "stored_filename": f"{evidence_id}_phoenix_treasury_ledger_oct2026.csv",
                "file_size": len(tampered_bytes),
                "mime_type": "text/csv",
                "file_extension": "csv",
                "storage_path": working_path,
                "sha256_hash": genuine_hash,
                "original_sha256_hash": genuine_hash,
                "calculated_hash": tampered_hash,
                "integrity_status": "TAMPERED",
                "source_device": "VAULT_TERMINAL_01",
                "collector": chief_name,
                "created_at": now - timedelta(days=2),
                "last_verified_at": now - timedelta(hours=1),
                "has_original_backup": True,
                "tamper_details": {
                    "confirmed_at": now - timedelta(hours=1),
                    "confirmed_by": chief_id,
                    "confirmed_by_name": chief_name,
                    "reason": "Host disk mutation detected during cryptographic SHA-256 verification. Beneficiary altered to Rogue Cayman Shell Corp.",
                    "attacker_attribution": "Suspect Malory (Rogue System Admin)",
                    "attributed_actor": "Suspect Malory (Rogue System Admin)",
                    "tamper_method": "DIRECT_STORAGE_WRITE",
                    "investigation_notes": "Cryptographic mismatch verified. Working copy preserved in tampered state for court prosecution. Preserved original backup unlocked."
                }
            }
            await evidence_col.insert_one(evidence_doc)

            meta_doc = {
                "evidence_id": evidence_id,
                "case_id": case_id,
                "original_filename": "phoenix_treasury_ledger_oct2026.csv",
                "file_size": len(genuine_bytes),
                "mime_type": "text/csv",
                "file_extension": "csv",
                "source_device": "VAULT_TERMINAL_01",
                "source_type": "DATABASE_EXPORT",
                "collector": chief_name,
                "description": "Original Treasury Wire Transfer Ledger. Captured at initial evidence acquisition baseline.",
                "tags": ["TREASURY", "FINANCIAL_RECORD", "EVIDENCE_TAMPERED", "FRAUD"],
                "metadata_status": "EXTRACTED",
                "created_at": now - timedelta(days=2)
            }
            await metadata_col.insert_one(meta_doc)

            backup_doc = {
                "backup_id": "BACKUP-EVDPhoenix-V1",
                "evidence_id": evidence_id,
                "case_id": case_id,
                "version": 1,
                "original_filename": "phoenix_treasury_ledger_oct2026.csv",
                "storage_reference": "BACKUP-EVDPhoenix-V1",
                "storage_path": backup_path,
                "original_sha256": genuine_hash,
                "backup_sha256": genuine_hash,
                "file_size": len(genuine_bytes),
                "created_by": chief_id,
                "created_by_name": chief_name,
                "status": "PROTECTED",
                "created_at": now - timedelta(days=2)
            }
            await backups_col.insert_one(backup_doc)

            await custody_col.insert_one({
                "evidence_id": evidence_id,
                "case_id": case_id,
                "action": "TAMPER_CONFIRMED",
                "actor_id": chief_id,
                "actor_name": chief_name,
                "timestamp": now - timedelta(hours=1),
                "details": "Unauthorized tampering CONFIRMED on 'phoenix_treasury_ledger_oct2026.csv'. Attribution: Suspect Malory (Rogue System Admin).",
                "ip_address": "127.0.0.1",
                "event_hash": hashlib.sha256(f"{evidence_id}:{case_id}:TAMPER_CONFIRMED:{now}".encode()).hexdigest()
            })
            print(f"[BOOTSTRAP] Initialized Tampered Evidence Exhibit & Preserved Backup for {evidence_id}")
        else:
            evidence_id = str(evidence_doc["_id"])
            sub_dir = os.path.join(working_dir, evidence_id)
            os.makedirs(sub_dir, exist_ok=True)
            working_path = os.path.join(sub_dir, "phoenix_treasury_ledger_oct2026.csv")
            if not os.path.exists(working_path):
                with open(working_path, "wb") as f:
                    f.write(tampered_bytes)

            await evidence_col.update_one(
                {"_id": evidence_doc["_id"]},
                {"$set": {"storage_path": working_path, "integrity_status": "TAMPERED", "has_original_backup": True}}
            )
            await backups_col.update_one(
                {"evidence_id": evidence_id},
                {"$set": {"storage_path": backup_path, "status": "PROTECTED"}},
                upsert=True
            )

    except Exception as e:
        print(f"[BOOTSTRAP_ERR] Error ensuring demo cases: {e}")
