import asyncio
import os
import sys
from datetime import datetime, timezone
from bson import ObjectId

# Ensure server app directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.repositories.diary import DiaryRepository, GENESIS_HASH
from app.models.diary import DiaryEntryCreate, DiaryEntryAmend

async def main():
    print("Connecting to MongoDB...")
    await connect_to_mongo()
    db = get_database()
    repo = DiaryRepository(db)

    # Use a test case ID
    test_case_id = f"test_case_{int(datetime.now().timestamp())}"
    print(f"Creating test case: {test_case_id}")
    await db["cases"].insert_one({
        "_id": ObjectId(),
        "case_number": "CASE-BNSS-TEST",
        "title": "Automated BNSS Diary Test Case",
        "case_type": "DATA_BREACH",
        "priority": "HIGH",
        "status": "OPEN",
        "created_by": "test_inv_001",
        "created_by_name": "Senior Inspector Sharma",
        "assigned_investigator": "test_inv_001",
        "assigned_investigator_name": "Senior Inspector Sharma",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "notes": []
    })

    admin_user = {
        "_id": "admin_user_001",
        "name": "Chief Examiner Verma",
        "email": "verma@cryptevid.internal",
        "role": "admin"
    }

    investigator_user = {
        "_id": "test_inv_001",
        "name": "Senior Inspector Sharma",
        "email": "sharma@cryptevid.internal",
        "role": "investigator"
    }

    auditor_user = {
        "_id": "auditor_user_001",
        "name": "Court Registrar Rao",
        "email": "rao@judiciary.gov.in",
        "role": "readonly"
    }

    try:
        # 1. Test Entry Creation
        print("\n--- Test 1: Record First Diary Entry ---")
        payload1 = DiaryEntryCreate(
            investigation_date="2026-10-15",
            time_info_received="09:15",
            start_time="09:30",
            closing_time="17:45",
            places_visited=["Cyber Cell HQ, Sector 5", "Data Center Unit 4"],
            activities_performed="Conducted bit-stream forensic acquisition of primary file server drives and interviewed system administrator.",
            findings="Identified suspicious external IP connection in firewall logs at 03:14 UTC. Primary volume exhibit acquired.",
            related_evidence_ids=["ev_disk_001", "ev_pcap_002"],
            witness_references="SysAdmin statement recorded regarding unauthorized SSH key addition.",
            next_steps="Transmit drive image for offline memory timeline analysis."
        )

        entry1 = await repo.create_entry(test_case_id, investigator_user, payload1)
        print(f"Entry 1 Created: Code={entry1['entry_code']}, Num={entry1['entry_number']}")
        print(f"Entry 1 Hash={entry1['entry_hash']}")
        print(f"Entry 1 PrevHash={entry1['previous_hash']}")
        assert entry1["entry_number"] == 1, "First entry number should be 1"
        assert entry1["previous_hash"] == GENESIS_HASH, "First entry previous hash should be genesis"
        assert len(entry1["entry_hash"]) == 64, "SHA-256 hash must be 64 characters"

        # 2. Test Second Entry (Hash Chaining)
        print("\n--- Test 2: Record Second Diary Entry (Chaining Check) ---")
        payload2 = DiaryEntryCreate(
            investigation_date="2026-10-16",
            time_info_received="10:00",
            start_time="10:15",
            closing_time="18:30",
            places_visited=["Regional Cyber Forensic Laboratory"],
            activities_performed="Processed memory dump and extracted compromised process trees.",
            findings="Malicious persistence script identified under /etc/cron.d/sync_service.",
            related_evidence_ids=["ev_disk_001"],
            witness_references="Forensic analyst notes on volatility plugin outputs.",
            next_steps="Draft preliminary forensic examination findings."
        )

        entry2 = await repo.create_entry(test_case_id, investigator_user, payload2)
        print(f"Entry 2 Created: Code={entry2['entry_code']}, Num={entry2['entry_number']}")
        print(f"Entry 2 Hash={entry2['entry_hash']}")
        print(f"Entry 2 PrevHash={entry2['previous_hash']}")
        assert entry2["entry_number"] == 2, "Second entry number should be 2"
        assert entry2["previous_hash"] == entry1["entry_hash"], "Second entry must chain to first entry's hash"

        # 3. Test Cryptographic Verification
        print("\n--- Test 3: Verify Integrity of Entries ---")
        v1 = await repo.verify_entry_integrity(entry1["_id"], test_case_id)
        print(f"Verification 1: valid={v1['is_valid']}, chain={v1['previous_hash_matches']}, status={v1['status']}")
        assert v1["is_valid"] is True, "Entry 1 hash recalculation should match stored hash"
        assert v1["previous_hash_matches"] is True, "Entry 1 previous hash match should be True"

        v2 = await repo.verify_entry_integrity(entry2["_id"], test_case_id)
        print(f"Verification 2: valid={v2['is_valid']}, chain={v2['previous_hash_matches']}, status={v2['status']}")
        assert v2["is_valid"] is True, "Entry 2 hash recalculation should match stored hash"
        assert v2["previous_hash_matches"] is True, "Entry 2 chain link must match"

        # 4. Test Versioned Amendment History
        print("\n--- Test 4: Amend Entry 1 with Mandatory Justification ---")
        amend_payload = DiaryEntryAmend(
            reason="Corrected exact spelling of Data Center Unit and added missing secondary exhibit ID.",
            places_visited=["Cyber Cell HQ, Sector 5", "Data Center Unit 4B (Primary Storage Vault)"],
            related_evidence_ids=["ev_disk_001", "ev_pcap_002", "ev_log_003"]
        )

        amended = await repo.amend_entry(entry1["_id"], test_case_id, investigator_user, amend_payload)
        print(f"Amended Entry 1: is_amended={amended['is_amended']}, amendments_count={len(amended['amendments'])}")
        assert amended["is_amended"] is True
        assert len(amended["amendments"]) == 1
        amendment = amended["amendments"][0]
        print(f"Amendment Record: editor={amendment['amended_by_name']}, reason={amendment['reason']}")
        print(f"Amendment Hash={amendment['amendment_hash']}")
        print(f"Previous State: {amendment['previous_state']}")
        print(f"New State: {amendment['new_state']}")
        assert "places_visited" in amendment["new_state"]
        assert "related_evidence_ids" in amendment["new_state"]
        # Baseline entry_hash must remain intact and permanent!
        assert amended["entry_hash"] == entry1["entry_hash"], "Original baseline hash must never be overwritten"

        # 5. Test Listing and RBAC Witness Confidentiality Redaction
        print("\n--- Test 5: List Entries and Enforce RBAC Witness Confidentiality ---")
        # Investigator/Admin view: witness references present
        inv_entries, inv_total = await repo.list_entries(test_case_id, investigator_user)
        print(f"Investigator View: {inv_total} entries. Witness info: '{inv_entries[0]['witness_references']}'")
        assert not inv_entries[0]["is_witness_redacted"]
        assert "SysAdmin statement" in inv_entries[0]["witness_references"]

        # Court Auditor / Read-Only view: witness references redacted
        aud_entries, aud_total = await repo.list_entries(test_case_id, auditor_user)
        print(f"Auditor View: {aud_total} entries. Witness info: '{aud_entries[0]['witness_references']}'")
        assert aud_entries[0]["is_witness_redacted"] is True
        assert "RESTRICTED" in aud_entries[0]["witness_references"]

        # 6. Test Date Filtering
        print("\n--- Test 6: Date Filtering ---")
        filtered_entries, filtered_total = await repo.list_entries(
            test_case_id, investigator_user, start_date="2026-10-16", end_date="2026-10-16"
        )
        print(f"Date Filtered (2026-10-16): total={filtered_total}, entry_code={filtered_entries[0]['entry_code']}")
        assert filtered_total == 1
        assert filtered_entries[0]["entry_number"] == 2

        # 7. Test Audit Log Mirroring
        print("\n--- Test 7: Verify Audit Log Mirroring ---")
        logs = await db["audit_logs"].find({"case_id": test_case_id}).to_list(length=10)
        print(f"Audit logs recorded for test case: {len(logs)}")
        actions = [l["action"] for l in logs]
        print(f"Recorded Actions: {actions}")
        assert "DIARY_ENTRY_CREATED" in actions
        assert "DIARY_ENTRY_AMENDED" in actions

        print("\n[SUCCESS] All Digital Investigation Diary module tests passed successfully!")

    finally:
        # Clean up test artifacts
        print("\nCleaning up test case artifacts...")
        await db["cases"].delete_many({"case_number": "CASE-BNSS-TEST"})
        await db["investigation_diary"].delete_many({"case_id": test_case_id})
        await db["audit_logs"].delete_many({"case_id": test_case_id})
        await close_mongo_connection()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
