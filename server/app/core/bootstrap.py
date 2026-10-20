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

        # Default users list
        default_accounts = [
            {
                "email": "admin@forensics.gov",
                "name": "Chief Investigator (Admin)",
                "role": "admin",
                "password": "password123",
                "rfid": "04A1B2C3",
                "fingerprint_id": 12,
                "is_active": True
            },
            {
                "email": "investigator@forensics.gov",
                "name": "Forensic Analyst",
                "role": "investigator",
                "password": "password123",
                "rfid": "B1C2D3E4",
                "fingerprint_id": 15,
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
                # Check if password verifies against either password123 or admin123
                h = existing.get("hashed_password", "")
                if not verify_password("password123", h) and not verify_password("admin123", h):
                    # Refresh hash to password123
                    new_hash = get_password_hash("password123")
                    await users_col.update_one(
                        {"_id": existing["_id"]},
                        {"$set": {"hashed_password": new_hash, "is_active": True}}
                    )
                    print(f"[BOOTSTRAP] Synchronized password hash for: {acc['email']}")

        # 2. Ensure Default ESP32 Ingestion Node
        existing_device = await devices_col.find_one({"device_id": "ESP32_01"})
        if not existing_device:
            await devices_col.insert_one({
                "device_id": "ESP32_01",
                "name": "Forensic Ingestion Node 01",
                "mac_address": "24:6F:28:AE:C3:0C",
                "firmware_version": "v1.0.4-forensic",
                "status": "online",
                "last_seen": datetime.now(timezone.utc),
                "registered_at": datetime.now(timezone.utc)
            })
            print("[BOOTSTRAP] Registered default hardware device: ESP32_01")

        print("[BOOTSTRAP] Database verification & user initialization complete.")
    except Exception as e:
        print(f"[BOOTSTRAP_ERR] Error initializing default users: {e}")
