import asyncio
import os
import shutil
import hashlib
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from app.core.database import connect_to_mongo, get_database, close_mongo_connection
from app.core.config import settings
from app.models.evidence import IntegrityStatus, CustodyAction
from app.models.security_event import SecurityEventType, SecurityAlertSeverity
from app.services.hash_service import HashService
from app.services.custody_service import ChainOfCustodyService
from app.services.backup_service import EvidenceBackupService
from app.repositories.diary import DiaryRepository, GENESIS_HASH

async def seed_two_cases():
    print("=" * 70)
    print("  CRYPTEVID: POPULATING TWO FORENSIC CASES")
    print("  Case 1: Fully Verified Evidence (Operation Ghost Sentinel)")
    print("  Case 2: Tampered Evidence with Backup & Hashing (Operation Red Ledger)")
    print("=" * 70)

    await connect_to_mongo()
    db = get_database()

    admin = await db["users"].find_one({"email": "admin@forensics.gov"})
    investigator = await db["users"].find_one({"email": "investigator@forensics.gov"})

    if not admin or not investigator:
        print("[!] Admin or Investigator user missing.")
        await close_mongo_connection()
        return

    admin_id = str(admin["_id"])
    inv_id = str(investigator["_id"])

    # Clean previous demo runs for these specific case numbers
    target_case_numbers = ["DF-2026-000101", "DF-2026-000102"]
    for cnum in target_case_numbers:
        old_case = await db["cases"].find_one({"case_number": cnum})
        if old_case:
            old_cid = str(old_case["_id"])
            print(f"[*] Removing existing case {cnum} (ID: {old_cid}) for clean seeding...")
            await db["cases"].delete_one({"_id": old_case["_id"]})
            await db["evidence"].delete_many({"case_id": old_cid})
            await db["evidence_metadata"].delete_many({"case_id": old_cid})
            await db["evidence_backups"].delete_many({"case_id": old_cid})
            await db["chain_of_custody"].delete_many({"case_id": old_cid})
            await db["forensic_events"].delete_many({"case_id": old_cid})
            await db["investigation_diary"].delete_many({"case_id": old_cid})
            await db["security_events"].delete_many({"case_id": old_cid})

            # Clean directories
            old_ev_dir = os.path.join(settings.EVIDENCE_STORAGE_DIR, old_cid)
            if os.path.exists(old_ev_dir):
                shutil.rmtree(old_ev_dir, ignore_errors=True)
            old_bk_dir = os.path.join(settings.BACKUP_STORAGE_DIR, old_cid)
            if os.path.exists(old_bk_dir):
                shutil.rmtree(old_bk_dir, ignore_errors=True)

    now = datetime.now(timezone.utc)

    # =========================================================================
    # CASE 1: FULLY VERIFIED EVIDENCE (Operation Ghost Sentinel)
    # =========================================================================
    print("\n-------------------------------------------------------------")
    print("CREATING CASE 1: Operation Ghost Sentinel (DF-2026-000101) [VERIFIED]")
    print("-------------------------------------------------------------")

    case1_id = str(ObjectId())
    case1_dir = os.path.join(settings.EVIDENCE_STORAGE_DIR, case1_id)
    os.makedirs(case1_dir, exist_ok=True)

    case1_doc = {
        "_id": ObjectId(case1_id),
        "case_number": "DF-2026-000101",
        "title": "Operation Ghost Sentinel — Critical Infrastructure SCADA Intrusion",
        "description": "Multi-vector cyber espionage inquiry into unauthorized persistent network intrusion, SCADA telemetry exfiltration, and malicious binary execution targeting Regional Power Grid Substation 04. Digital artifacts recovered from physical perimeter firewall taps, memory captures, and compromised field control units.",
        "status": "IN_PROGRESS",
        "priority": "HIGH",
        "case_type": "CYBER_ESPIONAGE",
        "tags": ["SCADA", "CRITICAL_INFRASTRUCTURE", "CYBER_ESPIONAGE", "NETWORK_INTRUSION", "MEMORY_ANALYSIS"],
        "created_by": ObjectId(admin_id),
        "created_by_name": admin["name"],
        "assigned_investigator": ObjectId(inv_id),
        "assigned_investigator_name": investigator["name"],
        "created_at": now - timedelta(days=4),
        "updated_at": now,
        "notes": [
            {
                "content": "Case initiated following automated IDS alert indicating Modbus function code anomalies on RTU controller 192.168.10.15.",
                "author": admin["name"],
                "created_at": now - timedelta(days=4)
            },
            {
                "content": "Hardware packet tap deployed at Substation 04 Gateway. Bit-stream disk images and volatile RAM dumps acquired.",
                "author": investigator["name"],
                "created_at": now - timedelta(days=3)
            },
            {
                "content": "All evidence exhibits deposited into forensic vault. Baseline SHA-256 hashes generated and verified intact.",
                "author": investigator["name"],
                "created_at": now - timedelta(days=2)
            }
        ]
    }
    await db["cases"].insert_one(case1_doc)
    print(f"[+] Case 1 Inserted: DF-2026-000101 (ID: {case1_id})")

    # Evidence items for Case 1
    case1_evidence_specs = [
        {
            "filename": "scada_network_telemetry_dump.pcap",
            "mime_type": "application/vnd.tcpdump.pcap",
            "content": b"\xd4\xc3\xb2\xa1\x02\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x00\x01\x00\x00\x00" + (b"SCADA_MODBUS_TCP_FRAME_SRC_192.168.10.15_DST_EXTERNAL_C2_BURST_PAYLOAD_" * 16),
            "description": "Continuous PCAP capture of anomalous Modbus TCP packets directed from RTU field unit to foreign C2 server.",
            "source_device": "ETHERNET_TAP_04",
            "source_type": "NETWORK_DEVICE",
            "tags": ["NETWORK_CAPTURE", "SCADA", "PCAP", "INFRASTRUCTURE"]
        },
        {
            "filename": "malware_payload_memory_dump.raw",
            "mime_type": "application/octet-stream",
            "content": b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00\xb8\x00\x00\x00" + (b"VOLATILE_RAM_INJECTED_BEACON_DLL_CRYPTEVID_FORENSIC_EXHIBIT_2026_" * 24),
            "description": "Raw RAM memory dump acquired via hardware DMA from substation HMI terminal showing memory-resident beacon.",
            "source_device": "HMI_TERMINAL_DMA",
            "source_type": "MEMORY_CAPTURE",
            "tags": ["VOLATILE_MEMORY", "MALWARE_INJECTION", "RAM_DUMP"]
        },
        {
            "filename": "firewall_auth_failure_logs.csv",
            "mime_type": "text/csv",
            "content": b"timestamp,source_ip,destination_port,protocol,event,auth_status\n"
                       b"2026-10-19T01:14:02Z,198.51.100.42,502,TCP,MODBUS_WRITE,ACCESS_DENIED\n"
                       b"2026-10-19T01:14:05Z,198.51.100.42,502,TCP,MODBUS_WRITE,ACCESS_DENIED\n"
                       b"2026-10-19T01:14:12Z,198.51.100.42,22,TCP,SSH_LOGIN,FAILED_PASSWORD\n"
                       b"2026-10-19T01:14:18Z,198.51.100.42,22,TCP,SSH_LOGIN,FAILED_PASSWORD\n"
                       b"2026-10-19T01:15:01Z,198.51.100.42,443,TCP,HTTPS_TUNNEL,ESTABLISHED\n",
            "description": "Perimeter firewall syslog records capturing brute-force authentication attacks preceding breach.",
            "source_device": "FORTINET_FW_01",
            "source_type": "LOG_FILE",
            "tags": ["FIREWALL_LOGS", "BRUTE_FORCE", "AUTHENTICATION"]
        }
    ]

    case1_ev_ids = []
    for spec in case1_evidence_specs:
        ev_id = str(ObjectId())
        file_path = os.path.join(case1_dir, f"{ev_id}_{spec['filename']}")
        with open(file_path, "wb") as f:
            f.write(spec["content"])

        file_size = len(spec["content"])
        sha256 = hashlib.sha256(spec["content"]).hexdigest().lower()
        file_ext = os.path.splitext(spec["filename"])[1].lstrip(".").lower()

        # Create Metadata
        meta_id = str(ObjectId())
        meta_doc = {
            "_id": ObjectId(meta_id),
            "evidence_id": ev_id,
            "case_id": case1_id,
            "original_filename": spec["filename"],
            "file_size": file_size,
            "mime_type": spec["mime_type"],
            "file_extension": file_ext,
            "source_device": spec["source_device"],
            "source_type": spec["source_type"],
            "collector": investigator["name"],
            "collection_timestamp": now - timedelta(days=2),
            "description": spec["description"],
            "tags": spec["tags"],
            "latitude": 37.7749,
            "longitude": -122.4194,
            "metadata_status": "EXTRACTED",
            "extracted_attributes": {
                "byte_count": file_size,
                "packet_capture_protocol": "SCADA/TCP",
                "acquisition_method": "BIT_STREAM_IMAGE"
            }
        }
        await db["evidence_metadata"].insert_one(meta_doc)

        # Create Evidence record (VERIFIED)
        ev_doc = {
            "_id": ObjectId(ev_id),
            "case_id": case1_id,
            "original_filename": spec["filename"],
            "stored_filename": f"{ev_id}_{spec['filename']}",
            "file_size": file_size,
            "mime_type": spec["mime_type"],
            "file_extension": file_ext,
            "storage_path": file_path,
            "source_device": spec["source_device"],
            "source_type": spec["source_type"],
            "collector_id": inv_id,
            "collector_name": investigator["name"],
            "collection_timestamp": now - timedelta(days=2),
            "created_at": now - timedelta(days=2),
            "updated_at": now,
            "sha256_hash": sha256,
            "original_sha256_hash": sha256,
            "version": 1,
            "version_history": [],
            "has_original_backup": True,
            "integrity_status": IntegrityStatus.VERIFIED.value,
            "last_verified_at": now,
            "last_calculated_hash": sha256,
            "metadata_id": meta_id,
            "description": spec["description"],
            "tags": spec["tags"],
            "metadata_status": "EXTRACTED"
        }
        await db["evidence"].insert_one(ev_doc)
        case1_ev_ids.append(ev_id)

        # Record Initial Chain of Custody
        await ChainOfCustodyService.record_event(
            db=db,
            evidence_id=ev_id,
            case_id=case1_id,
            action=CustodyAction.EVIDENCE_UPLOADED.value,
            actor_id=inv_id,
            actor_name=investigator["name"],
            details=f"Evidence artifact '{spec['filename']}' ({file_size} bytes) ingested into Case DF-2026-000101. Baseline SHA-256: {sha256}",
            ip_address="127.0.0.1",
            device_id=spec["source_device"]
        )

        # Create Preserved Original Backup
        await EvidenceBackupService.create_backup(
            db=db,
            evidence_id=ev_id,
            case_id=case1_id,
            source_path=file_path,
            original_sha256=sha256,
            created_by=inv_id,
            created_by_name=investigator["name"],
            original_filename=spec["filename"],
            file_size=file_size,
            ip_address="127.0.0.1",
            device_id=spec["source_device"]
        )

        # Record Verification Custody Event
        await ChainOfCustodyService.record_event(
            db=db,
            evidence_id=ev_id,
            case_id=case1_id,
            action=CustodyAction.EVIDENCE_VERIFIED.value,
            actor_id=inv_id,
            actor_name=investigator["name"],
            details=f"Cryptographic integrity check [PASSED - 0 BIT DRIFT]. Calculated SHA-256 matches baseline: {sha256}",
            ip_address="127.0.0.1",
            device_id="WEB_APP"
        )
        print(f"  [+] Ingested & Verified: {spec['filename']} (Hash: {sha256[:16]}...)")

    # Case 1 Timeline Events
    timeline_specs_1 = [
        {
            "case_id": case1_id,
            "title": "Substation Perimeter Fence Motion Alert",
            "description": "IR beam sensor tripped at North Perimeter of Regional Substation 04.",
            "event_type": "HARDWARE_AUTH",
            "severity": "WARNING",
            "precision": "EXACT",
            "confidence": "HIGH",
            "source_type": "IOT_NODE",
            "device_id": "PERIMETER_SENSOR_04",
            "location_name": "Regional Substation 04 North Perimeter",
            "timestamp": now - timedelta(days=4, hours=2)
        },
        {
            "case_id": case1_id,
            "title": "Unauthorized Modbus Command Sequence Initiated",
            "description": "Foreign IP 198.51.100.42 transmitted unauthenticated Modbus write requests to RTU controller.",
            "event_type": "TIMELINE_ANOMALY",
            "severity": "CRITICAL",
            "precision": "EXACT",
            "confidence": "HIGH",
            "source_type": "NETWORK_DEVICE",
            "device_id": "ETHERNET_TAP_04",
            "location_name": "Substation Control Room",
            "timestamp": now - timedelta(days=4)
        },
        {
            "case_id": case1_id,
            "title": "Forensic Volatile Memory Acquisition Complete",
            "description": "Lead investigator successfully cloned active RAM from substation HMI node.",
            "event_type": "EVIDENCE_COLLECTION",
            "severity": "INFO",
            "precision": "EXACT",
            "confidence": "HIGH",
            "source_type": "MANUAL",
            "device_id": "INVESTIGATOR_STATION",
            "location_name": "Forensic Mobile Lab Unit",
            "timestamp": now - timedelta(days=2)
        }
    ]
    for ev in timeline_specs_1:
        ev["created_at"] = now
        await db["forensic_events"].insert_one(ev)

    # Case 1 Digital Investigation Diary
    c1_iso = (now - timedelta(days=2)).isoformat()
    c1_canonical_hash = DiaryRepository.compute_canonical_hash(
        case_id=case1_id,
        entry_number=1,
        investigation_date=(now - timedelta(days=2)).strftime("%Y-%m-%d"),
        time_info_received="08:30",
        start_time="09:00",
        closing_time="17:30",
        places_visited=["Regional Substation 04 Control Room", "Perimeter Guard Post"],
        activities_performed="Conducted bit-stream preservation of network tap logs, memory acquisition, and initial hash baseline calculations.",
        findings="Network dump shows unauthorized SCADA control commands. All evidence SHA-256 digests validated and sealed with preserved original copies.",
        related_evidence_ids=case1_ev_ids,
        created_by=investigator["name"],
        created_at_iso=c1_iso,
        previous_hash=GENESIS_HASH
    )
    diary1_doc = {
        "case_id": case1_id,
        "entry_number": 1,
        "investigation_date": (now - timedelta(days=2)).strftime("%Y-%m-%d"),
        "time_info_received": "08:30",
        "start_time": "09:00",
        "closing_time": "17:30",
        "places_visited": ["Regional Substation 04 Control Room", "Perimeter Guard Post"],
        "officers_present": [investigator["name"], admin["name"]],
        "activities_performed": "Conducted bit-stream preservation of network tap logs, memory acquisition, and initial hash baseline calculations.",
        "findings": "Network dump shows unauthorized SCADA control commands. All evidence SHA-256 digests validated and sealed with preserved original copies.",
        "related_evidence_ids": case1_ev_ids,
        "created_by": str(inv_id),
        "created_by_name": investigator["name"],
        "created_at": now - timedelta(days=2),
        "previous_hash": GENESIS_HASH,
        "entry_hash": c1_canonical_hash,
        "status": "FINALIZED",
        "amendment_history": []
    }
    await db["investigation_diary"].insert_one(diary1_doc)
    print("  [+] Case 1 Investigation Diary & Timeline seeded successfully.")


    # =========================================================================
    # CASE 2: TAMPERED EVIDENCE WITH PRESERVED BACKUP (Operation Red Ledger)
    # =========================================================================
    print("\n-------------------------------------------------------------")
    print("CREATING CASE 2: Operation Red Ledger (DF-2026-000102) [TAMPERED & BACKUP]")
    print("-------------------------------------------------------------")

    case2_id = str(ObjectId())
    case2_dir = os.path.join(settings.EVIDENCE_STORAGE_DIR, case2_id)
    os.makedirs(case2_dir, exist_ok=True)

    case2_doc = {
        "_id": ObjectId(case2_id),
        "case_number": "DF-2026-000102",
        "title": "Operation Red Ledger — Financial Wire Fraud & Evidence Vault Tampering",
        "description": "High-profile forensic inquiry into a $4,850,000.00 unauthorized treasury diversion. Suspect covertly accessed the active forensic evidence storage vault and manipulated the digital transaction ledger to alter beneficiary destination accounts. Cryptographic hash re-verification immediately detected the byte drift, confirmed tampering, and activated the isolated Preserved Original Backup for comparison and recovery.",
        "status": "IN_PROGRESS",
        "priority": "CRITICAL",
        "case_type": "FINANCIAL_FRAUD",
        "tags": ["FINANCIAL_FRAUD", "EVIDENCE_TAMPERING", "WIRE_TRANSFER", "CRITICAL_ALERT", "VAULT_MUTATION"],
        "created_by": ObjectId(admin_id),
        "created_by_name": admin["name"],
        "assigned_investigator": ObjectId(admin_id),
        "assigned_investigator_name": admin["name"],
        "created_at": now - timedelta(days=3),
        "updated_at": now,
        "notes": [
            {
                "content": "Case initiated following audit discrepancy report on treasury wire transaction #WT-2026-99482.",
                "author": admin["name"],
                "created_at": now - timedelta(days=3)
            },
            {
                "content": "Original accounting wire ledger ingested into vault. Preserved original backup created and isolated.",
                "author": admin["name"],
                "created_at": now - timedelta(days=2)
            },
            {
                "content": "CRITICAL TAMPER ALERT: Forensic verification detected SHA-256 hash drift on offshore_wire_transfer_ledger.csv! Investigation confirmed active file was modified on disk. Attributed actor: SUSPECT_INSIDER_HOST.",
                "author": admin["name"],
                "created_at": now - timedelta(hours=6)
            }
        ]
    }
    await db["cases"].insert_one(case2_doc)
    print(f"[+] Case 2 Inserted: DF-2026-000102 (ID: {case2_id})")

    # Exhibit 1: THE TAMPERED EXHIBIT
    tampered_filename = "offshore_wire_transfer_ledger.csv"
    original_ledger_content = (
        b"Transaction_ID,Timestamp,Sender_Entity,Beneficiary_Name,Destination_Account,Routing_Swift,Amount_USD,Authorization_Code,Status\n"
        b"WT-2026-99481,2026-10-18T14:22:10Z,Federal Treasury Corp,EuroClear Custody NV,BE-449201948,ECLRBEBB,1250000.00,AUTH_EXEC_8829,COMPLETED\n"
        b"WT-2026-99482,2026-10-18T16:45:00Z,Federal Treasury Corp,Apex Global Escrow LLC,SWIFT-CH-88492049,UBSWCHZH,4850000.00,AUTH_FRAUD_9901,PENDING_SETTLEMENT\n"
        b"WT-2026-99483,2026-10-18T17:10:30Z,Federal Treasury Corp,Standard Chartered Trust,GB-992014811,SCBLUS33,750000.00,AUTH_EXEC_8835,COMPLETED\n"
    )

    tampered_ledger_content = (
        b"Transaction_ID,Timestamp,Sender_Entity,Beneficiary_Name,Destination_Account,Routing_Swift,Amount_USD,Authorization_Code,Status\n"
        b"WT-2026-99481,2026-10-18T14:22:10Z,Federal Treasury Corp,EuroClear Custody NV,BE-449201948,ECLRBEBB,1250000.00,AUTH_EXEC_8829,COMPLETED\n"
        b"WT-2026-99482,2026-10-18T16:45:00Z,Federal Treasury Corp,Offshore Shell Ltd,CY-99482104,CYPB2201,4850000.00,AUTH_TAMPERED,SETTLED_CONFIRMED\n"
        b"WT-2026-99483,2026-10-18T17:10:30Z,Federal Treasury Corp,Standard Chartered Trust,GB-992014811,SCBLUS33,750000.00,AUTH_EXEC_8835,COMPLETED\n"
    )

    tampered_ev_id = str(ObjectId())
    tampered_file_path = os.path.join(case2_dir, f"{tampered_ev_id}_{tampered_filename}")

    # 1. First, write the ORIGINAL content so the backup service captures the genuine original
    with open(tampered_file_path, "wb") as f:
        f.write(original_ledger_content)

    orig_size = len(original_ledger_content)
    orig_sha256 = hashlib.sha256(original_ledger_content).hexdigest().lower()

    # 2. Create preserved original backup
    backup_resp = await EvidenceBackupService.create_backup(
        db=db,
        evidence_id=tampered_ev_id,
        case_id=case2_id,
        source_path=tampered_file_path,
        original_sha256=orig_sha256,
        created_by=admin_id,
        created_by_name=admin["name"],
        original_filename=tampered_filename,
        file_size=orig_size,
        ip_address="127.0.0.1",
        device_id="BANKING_SERVER_01"
    )

    # 3. NOW PERFORM THE COVERT MUTATION / TAMPERING on the active working file!
    with open(tampered_file_path, "wb") as f:
        f.write(tampered_ledger_content)

    tampered_size = len(tampered_ledger_content)
    tampered_actual_hash = hashlib.sha256(tampered_ledger_content).hexdigest().lower()

    # Metadata for tampered exhibit
    t_meta_id = str(ObjectId())
    t_meta_doc = {
        "_id": ObjectId(t_meta_id),
        "evidence_id": tampered_ev_id,
        "case_id": case2_id,
        "original_filename": tampered_filename,
        "file_size": orig_size,
        "mime_type": "text/csv",
        "file_extension": "csv",
        "source_device": "BANKING_SERVER_01",
        "source_type": "DATABASE_EXPORT",
        "collector": admin["name"],
        "collection_timestamp": now - timedelta(days=2),
        "description": "Treasury wire ledger showing unauthorized transfer. WORKING COPY CONFIRMED TAMPERED ON DISK.",
        "tags": ["FINANCIAL_RECORD", "WIRE_TRANSFER", "EVIDENCE_TAMPERED", "FRAUD"],
        "latitude": 40.7128,
        "longitude": -74.0060,
        "metadata_status": "EXTRACTED",
        "extracted_attributes": {
            "record_count": 3,
            "monitored_transaction": "WT-2026-99482",
            "tamper_detected": True
        }
    }
    await db["evidence_metadata"].insert_one(t_meta_doc)

    # Evidence Record with TAMPERED Status
    tamper_details_obj = {
        "confirmed_at": now - timedelta(hours=6),
        "confirmed_by": admin_id,
        "confirmed_by_name": admin["name"],
        "reason": f"Cryptographic SHA-256 hash mismatch detected: 147 bytes altered on storage volume. Beneficiary field changed from 'Apex Global Escrow LLC' to 'Offshore Shell Ltd'.",
        "attacker_attribution": "SUSPECT_INSIDER_HOST",
        "attributed_actor": "SUSPECT_INSIDER_HOST",
        "tamper_method": "STORAGE_MUTATION",
        "investigation_notes": (
            f"Physical evidence file byte stream mutated after baseline registration.\n"
            f"Registered Baseline Hash: {orig_sha256}\n"
            f"Recalculated Working Hash: {tampered_actual_hash}\n"
            f"Preserved Original Backup ID: {backup_resp.backup_id} is verified intact and available for recovery."
        )
    }

    tampered_ev_doc = {
        "_id": ObjectId(tampered_ev_id),
        "case_id": case2_id,
        "original_filename": tampered_filename,
        "stored_filename": f"{tampered_ev_id}_{tampered_filename}",
        "file_size": tampered_size,
        "mime_type": "text/csv",
        "file_extension": "csv",
        "storage_path": tampered_file_path,
        "source_device": "BANKING_SERVER_01",
        "source_type": "DATABASE_EXPORT",
        "collector_id": admin_id,
        "collector_name": admin["name"],
        "collection_timestamp": now - timedelta(days=2),
        "created_at": now - timedelta(days=2),
        "updated_at": now,
        "sha256_hash": orig_sha256,             # Expected registered baseline
        "original_sha256_hash": orig_sha256,    # Preserved original baseline
        "version": 1,
        "version_history": [],
        "has_original_backup": True,
        "integrity_status": IntegrityStatus.TAMPERED.value,
        "last_verified_at": now - timedelta(hours=6),
        "last_calculated_hash": tampered_actual_hash,
        "tamper_details": tamper_details_obj,
        "metadata_id": t_meta_id,
        "description": "Treasury wire ledger showing unauthorized transfer. CONFIRMED TAMPERED ON DISK.",
        "tags": ["FINANCIAL_RECORD", "WIRE_TRANSFER", "EVIDENCE_TAMPERED", "FRAUD"],
        "metadata_status": "EXTRACTED"
    }
    await db["evidence"].insert_one(tampered_ev_doc)

    # Chain of custody events for the tampered exhibit
    await ChainOfCustodyService.record_event(
        db=db,
        evidence_id=tampered_ev_id,
        case_id=case2_id,
        action=CustodyAction.EVIDENCE_UPLOADED.value,
        actor_id=admin_id,
        actor_name=admin["name"],
        details=f"Evidence artifact '{tampered_filename}' ({orig_size} bytes) ingested. Baseline SHA-256: {orig_sha256}",
        ip_address="127.0.0.1",
        device_id="BANKING_SERVER_01"
    )

    await ChainOfCustodyService.record_event(
        db=db,
        evidence_id=tampered_ev_id,
        case_id=case2_id,
        action=CustodyAction.INTEGRITY_DISCREPANCY_FLAGGED.value,
        actor_id=admin_id,
        actor_name=admin["name"],
        details=f"Integrity discrepancy detected! Expected baseline: {orig_sha256}, Recalculated on active storage: {tampered_actual_hash}. Unauthorized file alteration identified.",
        ip_address="127.0.0.1",
        device_id="AUTOMATED_HASH_VERIFIER"
    )

    await ChainOfCustodyService.record_event(
        db=db,
        evidence_id=tampered_ev_id,
        case_id=case2_id,
        action=CustodyAction.TAMPER_CONFIRMED.value,
        actor_id=admin_id,
        actor_name=admin["name"],
        details=f"CRITICAL TAMPER CONFIRMED by Lead Investigator. Attribution: SUSPECT_INSIDER_HOST. Method: STORAGE_MUTATION. Preserved Original Backup: {backup_resp.backup_id}.",
        ip_address="127.0.0.1",
        device_id="INVESTIGATOR_WORKSTATION"
    )

    # Security Alert in security_events collection
    alert_doc = {
        "event_id": f"ALERT-SEC-{ObjectId()}",
        "event_type": SecurityEventType.TAMPER_DETECTED.value,
        "timestamp": now - timedelta(hours=6),
        "ip_address": "127.0.0.1",
        "ip_source": "vault_monitor",
        "http_method": "POST",
        "endpoint": f"/api/evidence/{tampered_ev_id}/verify",
        "request_type": "INTEGRITY_CHECK",
        "user_id": admin_id,
        "login_id": "admin@forensics.gov",
        "user_role": "admin",
        "user_agent": "CRYPTEVID_CORE_VERIFIER",
        "device_id": "VAULT_STORAGE_NODE_01",
        "case_id": case2_id,
        "case_number": "DF-2026-000102",
        "evidence_id": tampered_ev_id,
        "evidence_name": tampered_filename,
        "action": "EVIDENCE_INTEGRITY_VERIFICATION",
        "result": "TAMPER_FLAGGED",
        "reason": f"Physical evidence file byte mutation confirmed on disk. Expected hash {orig_sha256[:16]}... vs Actual {tampered_actual_hash[:16]}...",
        "severity": SecurityAlertSeverity.CRITICAL.value,
        "metadata": {
            "expected_hash": orig_sha256,
            "calculated_hash": tampered_actual_hash,
            "backup_reference": backup_resp.backup_id,
            "attributed_actor": "SUSPECT_INSIDER_HOST"
        }
    }
    await db["security_events"].insert_one(alert_doc)
    print(f"  [!] TAMPERED EXHIBIT CREATED: {tampered_filename}")
    print(f"      - Registered Baseline Hash: {orig_sha256}")
    print(f"      - Mutated Working File Hash: {tampered_actual_hash}")
    print(f"      - Preserved Original Backup: {backup_resp.backup_id} (Intact & Isolated in {settings.BACKUP_STORAGE_DIR})")

    # Exhibit 2 for Case 2: VERIFIED EXHIBIT (for side-by-side comparison)
    sqlite_filename = "suspect_encrypted_chat_backup.sqlite"
    sqlite_content = (
        b"SQLite format 3\x00\x10\x00\x01\x01\x00@  \x00\x00\x00\x01\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01"
        + (b"CRYPTEVID_ENCRYPTED_SIGNAL_CHAT_MESSAGE_PAYLOAD_TABLE_RECORD_2026_" * 12)
    )
    sq_ev_id = str(ObjectId())
    sq_file_path = os.path.join(case2_dir, f"{sq_ev_id}_{sqlite_filename}")
    with open(sq_file_path, "wb") as f:
        f.write(sqlite_content)

    sq_size = len(sqlite_content)
    sq_sha256 = hashlib.sha256(sqlite_content).hexdigest().lower()

    # Metadata
    sq_meta_id = str(ObjectId())
    await db["evidence_metadata"].insert_one({
        "_id": ObjectId(sq_meta_id),
        "evidence_id": sq_ev_id,
        "case_id": case2_id,
        "original_filename": sqlite_filename,
        "file_size": sq_size,
        "mime_type": "application/x-sqlite3",
        "file_extension": "sqlite",
        "source_device": "SUSPECT_IPHONE_15_PRO",
        "source_type": "MOBILE_DEVICE",
        "collector": admin["name"],
        "collection_timestamp": now - timedelta(days=2),
        "description": "Encrypted messaging database extracted from suspect mobile handset.",
        "tags": ["MOBILE_FORENSICS", "ENCRYPTED_DATABASE", "SQLITE", "MESSAGING"],
        "latitude": 40.7128,
        "longitude": -74.0060,
        "metadata_status": "EXTRACTED",
        "extracted_attributes": {
            "database_engine": "SQLite 3",
            "table_count": 8,
            "integrity": "VERIFIED"
        }
    })

    # Evidence Record (VERIFIED)
    await db["evidence"].insert_one({
        "_id": ObjectId(sq_ev_id),
        "case_id": case2_id,
        "original_filename": sqlite_filename,
        "stored_filename": f"{sq_ev_id}_{sqlite_filename}",
        "file_size": sq_size,
        "mime_type": "application/x-sqlite3",
        "file_extension": "sqlite",
        "storage_path": sq_file_path,
        "source_device": "SUSPECT_IPHONE_15_PRO",
        "source_type": "MOBILE_DEVICE",
        "collector_id": admin_id,
        "collector_name": admin["name"],
        "collection_timestamp": now - timedelta(days=2),
        "created_at": now - timedelta(days=2),
        "updated_at": now,
        "sha256_hash": sq_sha256,
        "original_sha256_hash": sq_sha256,
        "version": 1,
        "version_history": [],
        "has_original_backup": True,
        "integrity_status": IntegrityStatus.VERIFIED.value,
        "last_verified_at": now,
        "last_calculated_hash": sq_sha256,
        "metadata_id": sq_meta_id,
        "description": "Encrypted messaging database extracted from suspect mobile handset.",
        "tags": ["MOBILE_FORENSICS", "ENCRYPTED_DATABASE", "SQLITE", "MESSAGING"],
        "metadata_status": "EXTRACTED"
    })

    # Backup for sqlite exhibit
    await EvidenceBackupService.create_backup(
        db=db,
        evidence_id=sq_ev_id,
        case_id=case2_id,
        source_path=sq_file_path,
        original_sha256=sq_sha256,
        created_by=admin_id,
        created_by_name=admin["name"],
        original_filename=sqlite_filename,
        file_size=sq_size,
        ip_address="127.0.0.1",
        device_id="SUSPECT_IPHONE_15_PRO"
    )

    await ChainOfCustodyService.record_event(
        db=db,
        evidence_id=sq_ev_id,
        case_id=case2_id,
        action=CustodyAction.EVIDENCE_UPLOADED.value,
        actor_id=admin_id,
        actor_name=admin["name"],
        details=f"Mobile database artifact '{sqlite_filename}' ({sq_size} bytes) ingested. Baseline SHA-256: {sq_sha256}",
        ip_address="127.0.0.1",
        device_id="SUSPECT_IPHONE_15_PRO"
    )
    print(f"  [+] Ingested & Verified Comparison Exhibit: {sqlite_filename} (Hash: {sq_sha256[:16]}...)")

    # Case 2 Timeline Events
    timeline_specs_2 = [
        {
            "case_id": case2_id,
            "title": "Wire Transfer Initiated via Corporate Portal",
            "description": "Transfer request WT-2026-99482 for $4,850,000.00 submitted via external VPN IP 203.0.113.88.",
            "event_type": "TIMELINE_ANOMALY",
            "severity": "CRITICAL",
            "precision": "EXACT",
            "confidence": "HIGH",
            "source_type": "WEB_APP",
            "device_id": "BANKING_SERVER_01",
            "location_name": "Corporate Treasury Network",
            "timestamp": now - timedelta(days=3)
        },
        {
            "case_id": case2_id,
            "title": "Forensic Vault Physical File Mutation Detected",
            "description": "Background hash sentinel identified SHA-256 discrepancy on offshore_wire_transfer_ledger.csv.",
            "event_type": "INTEGRITY_MISMATCH",
            "severity": "CRITICAL",
            "precision": "EXACT",
            "confidence": "HIGH",
            "source_type": "SENTINEL",
            "device_id": "VAULT_STORAGE_NODE_01",
            "location_name": "Forensic Evidence Vault",
            "timestamp": now - timedelta(hours=6)
        },
        {
            "case_id": case2_id,
            "title": "Tampering Confirmed & Preserved Backup Verified",
            "description": "Chief Investigator verified original backup BACKUP-EVD... and confirmed evidence tampering on working disk.",
            "event_type": "SECURITY_ALERT",
            "severity": "HIGH",
            "precision": "EXACT",
            "confidence": "HIGH",
            "source_type": "MANUAL",
            "device_id": "INVESTIGATOR_WORKSTATION",
            "location_name": "Forensic Laboratory Secure Node",
            "timestamp": now - timedelta(hours=5)
        }
    ]
    for ev in timeline_specs_2:
        ev["created_at"] = now
        await db["forensic_events"].insert_one(ev)

    # Case 2 Digital Investigation Diary
    c2_iso = (now - timedelta(hours=5)).isoformat()
    c2_canonical_hash = DiaryRepository.compute_canonical_hash(
        case_id=case2_id,
        entry_number=1,
        investigation_date=now.strftime("%Y-%m-%d"),
        time_info_received="14:00",
        start_time="14:15",
        closing_time="18:45",
        places_visited=["Forensic Evidence Storage Room", "Treasury Audit Division"],
        activities_performed="Investigated integrity failure on wire transfer exhibit. Carried out bit-stream comparison against preserved original backup.",
        findings="Confirmed deliberate evidence tampering on working storage. Destination beneficiary was fraudulently mutated. Preserved original backup in isolated vault remains 100% intact.",
        related_evidence_ids=[tampered_ev_id, sq_ev_id],
        created_by=admin["name"],
        created_at_iso=c2_iso,
        previous_hash=GENESIS_HASH
    )
    diary2_doc = {
        "case_id": case2_id,
        "entry_number": 1,
        "investigation_date": now.strftime("%Y-%m-%d"),
        "time_info_received": "14:00",
        "start_time": "14:15",
        "closing_time": "18:45",
        "places_visited": ["Forensic Evidence Storage Room", "Treasury Audit Division"],
        "officers_present": [admin["name"]],
        "activities_performed": "Investigated integrity failure on wire transfer exhibit. Carried out bit-stream comparison against preserved original backup.",
        "findings": "Confirmed deliberate evidence tampering on working storage. Destination beneficiary was fraudulently mutated. Preserved original backup in isolated vault remains 100% intact.",
        "related_evidence_ids": [tampered_ev_id, sq_ev_id],
        "created_by": str(admin_id),
        "created_by_name": admin["name"],
        "created_at": now - timedelta(hours=5),
        "previous_hash": GENESIS_HASH,
        "entry_hash": c2_canonical_hash,
        "status": "FINALIZED",
        "amendment_history": []
    }
    await db["investigation_diary"].insert_one(diary2_doc)
    print("  [+] Case 2 Investigation Diary & Timeline seeded successfully.")

    await close_mongo_connection()

    print("\n" + "=" * 70)
    print("SUCCESSFULLY SEEDED BOTH CASES:")
    print(f"  1. CASE 1 [VERIFIED]: DF-2026-000101 (ID: {case1_id})")
    print(f"     - Title: Operation Ghost Sentinel — Critical Infrastructure SCADA Intrusion")
    print(f"     - Exhibits: 3/3 VERIFIED with sealed backups")
    print(f"  2. CASE 2 [TAMPERED & BACKUP]: DF-2026-000102 (ID: {case2_id})")
    print(f"     - Title: Operation Red Ledger — Financial Wire Fraud & Evidence Tampering")
    print(f"     - Exhibits:")
    print(f"       * {tampered_filename} -> STATUS: TAMPERED (Baseline: {orig_sha256[:12]}..., Recalculated: {tampered_actual_hash[:12]}...)")
    print(f"         Preserved Backup ID: {backup_resp.backup_id} (Intact, original bytes available)")
    print(f"       * {sqlite_filename} -> STATUS: VERIFIED")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(seed_two_cases())
