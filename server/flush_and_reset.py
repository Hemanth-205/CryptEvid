import asyncio
import os
import shutil
from datetime import datetime
from app.core.database import connect_to_mongo, get_database, close_mongo_connection
from app.core.security import get_password_hash
from app.core.config import settings

async def flush_all_data():
    print("==================================================")
    print("FLUSHING ALL SYSTEM DATA AND INITIALIZING BASELINE")
    print("==================================================")

    # 1. Connect to MongoDB
    await connect_to_mongo()
    db = get_database()

    # 2. Collections to flush
    collections_to_clear = [
        "cases",
        "evidence",
        "evidence_metadata",
        "forensic_events",
        "chain_of_custody",
        "forensic_reports",
        "audit_logs",
        "counters",
        "devices",
        "settings",
        "users"
    ]

    for col_name in collections_to_clear:
        deleted_count = await db[col_name].delete_many({})
        print(f"[-] Cleared collection '{col_name}': {deleted_count.deleted_count} documents removed.")

    # 3. Seed Default Global Settings
    await db["settings"].insert_one({
        "key": "global_config",
        "simulation_mode": True,
        "gemini_api_key": "",
        "updated_at": datetime.utcnow()
    })
    print("[+] Seeded global settings (Simulation Mode: Active)")

    # 4. Seed Standard Users
    users_to_seed = [
        {
            "email": "admin@forensics.gov",
            "name": "Chief Investigator (Admin)",
            "role": "admin",
            "hashed_password": get_password_hash("password123"),
            "rfid": "04A1B2C3",
            "fingerprint_id": 12,
            "is_active": True,
            "created_at": datetime.utcnow()
        },
        {
            "email": "investigator@forensics.gov",
            "name": "Forensic Analyst",
            "role": "investigator",
            "hashed_password": get_password_hash("password123"),
            "rfid": "B1C2D3E4",
            "fingerprint_id": 15,
            "is_active": True,
            "created_at": datetime.utcnow()
        },
        {
            "email": "viewer@forensics.gov",
            "name": "Court Auditor (Read-Only)",
            "role": "readonly",
            "hashed_password": get_password_hash("password123"),
            "rfid": None,
            "fingerprint_id": None,
            "is_active": True,
            "created_at": datetime.utcnow()
        }
    ]

    for user in users_to_seed:
        res = await db["users"].insert_one(user)
        print(f"[+] Seeded User: {user['email']} | Role: {user['role'].upper()} | RFID: {user['rfid']} | FP_ID: {user['fingerprint_id']}")

    # 5. Seed IoT Ingestion Terminal Device
    await db["devices"].insert_one({
        "device_id": "ESP32_01",
        "name": "Forensic Ingestion Terminal 1",
        "status": "online",
        "mac_address": "24:6F:28:AE:C3:0C",
        "firmware_version": "v1.0.4-forensic",
        "last_seen": datetime.utcnow(),
        "registered_at": datetime.utcnow(),
        "created_at": datetime.utcnow()
    })
    print("[+] Seeded IoT Terminal: ESP32_01 (MAC: 24:6F:28:AE:C3:0C)")

    # 6. Initialize Case Sequence Counter
    current_year = datetime.utcnow().year
    await db["counters"].insert_one({
        "_id": f"case_seq_{current_year}",
        "seq": 0
    })
    print(f"[+] Initialized case sequence counter for year {current_year}")

    # 7. Seed Initial System Audit Log
    await db["audit_logs"].insert_one({
        "action": "SYSTEM_DATABASE_FLUSH",
        "user_email": "admin@forensics.gov",
        "user_id": None,
        "details": {
            "description": "Full system data flush performed. Baseline accounts, hardware nodes, and settings reinitialized.",
            "mode": "Simulation"
        },
        "ip_address": "127.0.0.1",
        "timestamp": datetime.utcnow()
    })
    print("[+] Created initial system audit log entry")

    # 8. Clean Physical Evidence Storage and Uploads Directories
    storage_dir = os.path.abspath(settings.EVIDENCE_STORAGE_DIR)
    uploads_dir = os.path.abspath(settings.UPLOAD_DIR)

    for target_dir, label in [(storage_dir, "evidence_storage"), (uploads_dir, "uploads")]:
        if os.path.exists(target_dir):
            for item in os.listdir(target_dir):
                item_path = os.path.join(target_dir, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                except Exception as e:
                    print(f"[!] Warning cleaning {item_path}: {e}")
        else:
            os.makedirs(target_dir, exist_ok=True)
        # Ensure base directories exist
        os.makedirs(target_dir, exist_ok=True)
        print(f"[+] Purged and reset storage directory: {label} ({target_dir})")

    # Ensure reports directory exists inside evidence_storage
    reports_dir = os.path.join(storage_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    print(f"[+] Ensured reports directory exists: {reports_dir}")

    await close_mongo_connection()
    print("\n[SUCCESS] All data has been successfully flushed and re-seeded to clean baseline!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(flush_all_data())
