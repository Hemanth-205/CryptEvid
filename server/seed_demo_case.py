import asyncio
import os
import hashlib
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from app.core.database import connect_to_mongo, get_database, close_mongo_connection
from app.core.config import settings
from app.services.hash_service import HashService
from app.services.custody_service import ChainOfCustodyService
from app.services.report_service import ForensicReportService

async def seed_demo():
    print("==================================================")
    print("SEEDING RICH DEMO INVESTIGATION FOR FULL UI ACCESS")
    print("==================================================")

    await connect_to_mongo()
    db = get_database()

    # 1. Fetch user accounts
    admin = await db["users"].find_one({"email": "admin@forensics.gov"})
    investigator = await db["users"].find_one({"email": "investigator@forensics.gov"})

    if not admin or not investigator:
        print("[!] Admin or Investigator user not found. Please run flush_and_reset.py first.")
        await close_mongo_connection()
        return

    admin_id = str(admin["_id"])
    inv_id = str(investigator["_id"])

    # 2. Check if a case already exists
    existing_case = await db["cases"].find_one({"case_number": "DF-2026-000001"})
    if existing_case:
        print(f"[+] Demo case DF-2026-000001 already exists (ID: {existing_case['_id']}). Skipping case creation.")
        case_id = str(existing_case["_id"])
    else:
        # Create Demo Case
        now = datetime.now(timezone.utc)
        case_doc = {
            "case_number": "DF-2026-000001",
            "title": "Operation Cyber Aegis - Corporate Data Exfiltration",
            "description": "Suspected insider threat and unauthorized intellectual property exfiltration targeting enterprise research databases. Evidence recovered from physical workstations and local network taps.",
            "status": "IN_PROGRESS",
            "priority": "HIGH",
            "case_type": "DATA_BREACH",
            "tags": ["DATA_BREACH", "INSIDER_THREAT", "NETWORK_SECURITY", "HIGH_PRIORITY"],
            "created_by": ObjectId(admin_id),
            "created_by_name": admin["name"],
            "assigned_investigator": ObjectId(inv_id),
            "assigned_investigator_name": investigator["name"],
            "created_at": now - timedelta(days=2),
            "updated_at": now,
            "notes": [
                {
                    "content": "Case initiated following SIEM alert indicating abnormal midnight egress traffic.",
                    "author": admin["name"],
                    "created_at": now - timedelta(days=2)
                },
                {
                    "content": "Physical workstation secured at Node ESP32_01. Forensic disk imaging underway.",
                    "author": investigator["name"],
                    "created_at": now - timedelta(days=1)
                }
            ]
        }
        res = await db["cases"].insert_one(case_doc)
        case_id = str(res.inserted_id)
        # Increment counter
        await db["counters"].update_one(
            {"_id": "case_seq_2026"},
            {"$set": {"seq": 1}},
            upsert=True
        )
        print(f"[+] Created Case: DF-2026-000001 (ID: {case_id})")

    # 3. Create Sample Evidence Files on Disk and in DB
    case_storage_dir = os.path.join(os.path.abspath(settings.EVIDENCE_STORAGE_DIR), case_id)
    os.makedirs(case_storage_dir, exist_ok=True)

    evidence_samples = [
        {
            "filename": "cctv_server_room_intrusion.jpg",
            "mime_type": "image/jpeg",
            "content": b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB\x00C\x00FORENSIC_CCTV_SAMPLE_EVIDENCE_STREAM_DATA_2026",
            "tags": ["SURVEILLANCE", "PHYSICAL_SECURITY", "CCTV"],
            "description": "CCTV camera capture of unauthorized entry at server room door B2."
        },
        {
            "filename": "exfiltration_network_dump.csv",
            "mime_type": "text/csv",
            "content": b"timestamp,src_ip,dst_ip,proto,bytes,flags\n2026-09-02T23:14:02Z,192.168.1.45,198.51.100.23,TCP,45210000,SYN-ACK-PSH\n2026-09-02T23:15:10Z,192.168.1.45,198.51.100.23,TCP,89450000,PSH-ACK\n",
            "tags": ["NETWORK_LOG", "PCAP_DATA", "EXFILTRATION"],
            "description": "Wireshark packet flow log showing 134MB exfiltration burst to external IP."
        },
        {
            "filename": "stolen_research_manifest.zip",
            "mime_type": "application/zip",
            "content": b"PK\x03\x04\x14\x00\x00\x00\x08\x00FORENSIC_ZIP_ARCHIVE_MEMBER_CONFIDENTIAL_MANIFEST_DATA_2026",
            "tags": ["ARCHIVE", "COMPRESSED_DATA", "CONFIDENTIAL"],
            "description": "Encrypted archive recovered from suspect USB flash drive."
        }
    ]

    ev_docs_created = []
    for item in evidence_samples:
        existing_ev = await db["evidence"].find_one({"case_id": case_id, "original_filename": item["filename"]})
        if existing_ev:
            ev_docs_created.append(existing_ev)
            continue

        file_id = str(ObjectId())
        file_path = os.path.join(case_storage_dir, f"{file_id}_{item['filename']}")
        with open(file_path, "wb") as f:
            f.write(item["content"])

        file_size = len(item["content"])
        sha256 = hashlib.sha256(item["content"]).hexdigest()

        ev_doc = {
            "_id": ObjectId(file_id),
            "case_id": case_id,
            "original_filename": item["filename"],
            "storage_path": file_path,
            "file_size": file_size,
            "mime_type": item["mime_type"],
            "sha256_hash": sha256,
            "integrity_status": "VERIFIED",
            "last_verified_at": datetime.now(timezone.utc),
            "uploaded_by": ObjectId(inv_id),
            "uploaded_by_name": investigator["name"],
            "source_device": "ESP32_01",
            "source_type": "MANUAL_UPLOAD",
            "description": item["description"],
            "tags": item["tags"],
            "created_at": datetime.now(timezone.utc) - timedelta(days=1),
            "updated_at": datetime.now(timezone.utc)
        }
        await db["evidence"].insert_one(ev_doc)
        ev_docs_created.append(ev_doc)
        print(f"[+] Ingested Evidence: {item['filename']} | SHA-256: {sha256[:16]}...")

        # Record Initial Chain of Custody Event
        await ChainOfCustodyService.record_event(
            db=db,
            evidence_id=file_id,
            case_id=case_id,
            action="EVIDENCE_INGESTED",
            actor_id=inv_id,
            actor_name=investigator["name"],
            details=f"Evidence artifact '{item['filename']}' deposited into vault via Terminal ESP32_01.",
            ip_address="127.0.0.1",
            device_id="ESP32_01"
        )
        # Record Verification Custody Event
        await ChainOfCustodyService.record_event(
            db=db,
            evidence_id=file_id,
            case_id=case_id,
            action="EVIDENCE_VERIFIED",
            actor_id=inv_id,
            actor_name=investigator["name"],
            details=f"Initial integrity check: [PASS - 0 BIT DRIFT]. Baseline hash: {sha256}",
            ip_address="127.0.0.1",
            device_id="WEB_APP"
        )

    # 4. Seed Forensic Events (Timeline)
    sample_events = [
        {
            "case_id": case_id,
            "title": "Abnormal Server Room Door Access",
            "description": "RFID badge tap recorded at Door B2 outside standard shift hours.",
            "event_type": "HARDWARE_AUTH",
            "severity": "WARNING",
            "precision": "EXACT",
            "confidence": "HIGH",
            "source_type": "IOT_NODE",
            "device_id": "ESP32_01",
            "location_name": "Server Room Corridor B",
            "timestamp": datetime.now(timezone.utc) - timedelta(hours=36)
        },
        {
            "case_id": case_id,
            "title": "High-Volume Data Egress Detected",
            "description": "Firewall blocked outgoing port 443 stream after 134MB transferred to unknown external IP.",
            "event_type": "TIMELINE_ANOMALY",
            "severity": "CRITICAL",
            "precision": "EXACT",
            "confidence": "HIGH",
            "source_type": "FIREWALL",
            "device_id": "GATEWAY_ROUTER",
            "location_name": "Data Center",
            "timestamp": datetime.now(timezone.utc) - timedelta(hours=35)
        },
        {
            "case_id": case_id,
            "title": "Workstation Drive Preservation",
            "description": "Lead investigator cloned suspect SSD and calculated bit-stream baseline.",
            "event_type": "EVIDENCE_COLLECTION",
            "severity": "INFO",
            "precision": "EXACT",
            "confidence": "HIGH",
            "source_type": "MANUAL",
            "device_id": "INVESTIGATOR_WORKSTATION",
            "location_name": "Forensic Lab Room 4",
            "timestamp": datetime.now(timezone.utc) - timedelta(hours=24)
        }
    ]

    for ev in sample_events:
        exists = await db["forensic_events"].find_one({"case_id": case_id, "title": ev["title"]})
        if not exists:
            ev["created_at"] = datetime.now(timezone.utc)
            await db["forensic_events"].insert_one(ev)
            print(f"[+] Logged Timeline Event: {ev['title']}")

    # 5. Generate Initial Court Report
    reports_count = await db["forensic_reports"].count_documents({"case_id": case_id})
    if reports_count == 0:
        print("[*] Compiling initial court report...")
        report = await ForensicReportService.generate_case_report(
            db=db,
            case_id=case_id,
            user=admin,
            title="Preliminary Forensic Investigation Report",
            classification="CONFIDENTIAL"
        )
        print(f"[+] Court Report Generated: {report.title} (Seal: {report.sha256_hash[:16]}...)")

    await close_mongo_connection()
    print("\n[SUCCESS] Demo Investigation successfully populated with rich evidence, custody ledger, timeline, graph, and court report!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(seed_demo())
