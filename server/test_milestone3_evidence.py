import os
import io
import hashlib
from fastapi.testclient import TestClient
from app.main import app
from app.services.hash_service import HashService

def run_milestone3_tests():
    print("==================================================================")
    print("RUNNING PHASE 2 (MILESTONE 3) EVIDENCE INTEGRITY & CUSTODY SUITE")
    print("==================================================================")

    with TestClient(app) as client:
        # Step 0: Obtain Admin and Readonly Tokens
        admin_login = client.post("/api/auth/login", json={
            "email": "admin@forensics.gov",
            "password": "password123"
        })
        assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print("[PASS] 0. Admin Authentication: Obtained JWT Bearer token")

        # Step 1: Create a Case Container for Evidence
        case_res = client.post("/api/cases", json={
            "title": "Operation Citadel - Evidence Integrity Audit",
            "description": "Cryptographic chain-of-custody and evidence hashing validation case.",
            "case_type": "DATA_BREACH",
            "priority": "HIGH",
            "tags": ["INTEGRITY", "TEST", "EVIDENCE"]
        }, headers=admin_headers)
        assert case_res.status_code == 201
        case = case_res.json()
        case_id = case["_id"]
        case_num = case["case_number"]
        print(f"[PASS] 1. Case Container Setup: Created {case_num} (ID: {case_id})")

        # Step 2: Evidence Upload & Streaming SHA-256 Calculation
        test_payload_bytes = b"SECURITY_INCIDENT_EXHIBIT_001_CORPO_DATABASE_DUMP_STREAM_HASH_2026"
        expected_sha256 = hashlib.sha256(test_payload_bytes).hexdigest().lower()

        upload_res = client.post(
            f"/api/cases/{case_id}/evidence",
            files={"file": ("incident_db_dump.sql", io.BytesIO(test_payload_bytes), "application/sql")},
            data={
                "description": "Core database transaction logs extracted from suspect terminal",
                "tags": "DATABASE,TRANSACTION,EXHIBIT_A",
                "source_device": "IOT_TERMINAL_01",
                "source_type": "PHYSICAL_EXTRACTION"
            },
            headers=admin_headers
        )
        assert upload_res.status_code == 201, f"Upload failed: {upload_res.text}"
        evidence1 = upload_res.json()
        evidence1_id = evidence1["_id"]
        stored_hash = evidence1["sha256_hash"]

        # Step 3: SHA-256 Correctness Verification
        assert stored_hash == expected_sha256, f"Hash mismatch: stored={stored_hash}, expected={expected_sha256}"
        assert evidence1["integrity_status"] == "VERIFIED"
        assert evidence1["case_id"] == case_id
        assert evidence1["file_size"] == len(test_payload_bytes)
        print(f"[PASS] 2-3. Evidence Upload & SHA-256: Generated baseline {stored_hash[:16]}... (matches raw bytes)")

        # Step 4: Chunked/Streaming Hash Verification on Large File
        print("\n--- Testing Chunked Streaming Hashing on Multi-MB Data ---")
        large_data = b"0123456789ABCDEF" * (256 * 1024)  # 4 MB
        large_expected_hash = hashlib.sha256(large_data).hexdigest().lower()
        large_stream = io.BytesIO(large_data)
        chunked_hash = HashService.calculate_sha256_stream(large_stream, chunk_size=64 * 1024)
        assert chunked_hash == large_expected_hash
        print(f"[PASS] 4. Chunked Streaming Hashing: 4MB artifact hashed across 64KB chunks -> {chunked_hash[:16]}...")

        # Step 5: Case-Evidence Relationship Listing
        case_ev_res = client.get(f"/api/cases/{case_id}/evidence", headers=admin_headers)
        assert case_ev_res.status_code == 200
        case_evidence_items = case_ev_res.json()
        assert len(case_evidence_items) >= 1
        assert any(e["_id"] == evidence1_id for e in case_evidence_items)
        print(f"[PASS] 5. Case-Evidence Relationship: Isolated {len(case_evidence_items)} artifact(s) for Case {case_num}")

        # Step 6: Evidence Retrieval & View Custody Logging
        get_res = client.get(f"/api/evidence/{evidence1_id}", headers=admin_headers)
        assert get_res.status_code == 200
        retrieved_ev = get_res.json()
        assert retrieved_ev["original_filename"] == "incident_db_dump.sql"
        assert retrieved_ev["case_number"] == case_num
        print("[PASS] 6. Evidence Retrieval: Metadata and case details hydrated")

        # Step 7: Safe Download of Evidence
        download_res = client.get(f"/api/evidence/{evidence1_id}/download", headers=admin_headers)
        assert download_res.status_code == 200
        assert download_res.content == test_payload_bytes
        print(f"[PASS] 7. Safe Evidence Download: Downloaded {len(download_res.content)} bytes accurately")

        # Step 8: Successful Integrity Verification (Unmodified)
        verify_res = client.post(f"/api/evidence/{evidence1_id}/verify", headers=admin_headers)
        assert verify_res.status_code == 200
        verify_data = verify_res.json()
        assert verify_data["integrity"] == "VERIFIED"
        assert verify_data["stored_hash"] == stored_hash
        assert verify_data["calculated_hash"] == stored_hash
        print(f"[PASS] 8. Integrity Verification (PASS): Artifact verified against baseline ({verify_data['integrity']})")

        # Step 9: Tamper Detection (Physical Bit Mutation)
        print("\n--- Simulating Forensic Tamper Attack on Evidence Disk Storage ---")
        from app.core.config import settings
        evidence_dir = os.path.join(settings.EVIDENCE_STORAGE_DIR, case_id, evidence1_id)
        assert os.path.exists(evidence_dir), f"Evidence storage directory missing at {evidence_dir}"
        stored_files = os.listdir(evidence_dir)
        assert len(stored_files) > 0, "No files found in evidence storage directory"
        storage_path = os.path.join(evidence_dir, stored_files[0])

        # Mutate 1 byte in the physical file on disk!
        with open(storage_path, "wb") as f:
            tampered_content = b"TAMPERED_COMPROMISED_CORRUPT_BYTES_INJECTED_BY_MALICIOUS_ACTOR"
            f.write(tampered_content)

        # Trigger verification on tampered file
        tamper_verify_res = client.post(f"/api/evidence/{evidence1_id}/verify", headers=admin_headers)
        assert tamper_verify_res.status_code == 200
        tamper_data = tamper_verify_res.json()

        assert tamper_data["integrity"] == "TAMPERED"
        assert tamper_data["stored_hash"] == stored_hash, "Original baseline hash must NOT be replaced!"
        assert tamper_data["calculated_hash"] != stored_hash, "Recalculated hash must differ from baseline"

        # Verify DB still preserves original baseline hash via API
        ev_after_tamper = client.get(f"/api/evidence/{evidence1_id}", headers=admin_headers).json()
        assert ev_after_tamper["sha256_hash"] == stored_hash, "CRITICAL RULE: Database sha256_hash must remain baseline!"
        assert ev_after_tamper["integrity_status"] == "TAMPERED"
        assert ev_after_tamper["last_calculated_hash"] == tamper_data["calculated_hash"]
        print(f"[PASS] 9. Tamper Detection (PASS): Correctly marked TAMPERED, preserved baseline {stored_hash[:16]}...")

        # Step 10: Cryptographic Chain of Custody History & Hash Chain Verification
        print("\n--- Testing Cryptographic Chain of Custody Ledger & Hash Chaining ---")
        custody_res = client.get(f"/api/evidence/{evidence1_id}/custody", headers=admin_headers)
        assert custody_res.status_code == 200
        custody_data = custody_res.json()
        history = custody_data["history"]

        assert len(history) >= 4  # UPLOADED, VIEWED, DOWNLOADED, VERIFIED, INTEGRITY_FAILURE
        actions = [h["action"] for h in history]
        assert "EVIDENCE_UPLOADED" in actions
        assert "EVIDENCE_VIEWED" in actions
        assert "EVIDENCE_DOWNLOADED" in actions
        assert "EVIDENCE_VERIFIED" in actions
        assert "EVIDENCE_INTEGRITY_FAILURE" in actions

        # Verify Cryptographic Hash Chain Continuity
        for i, entry in enumerate(history):
            assert entry["is_chain_valid"] is True, f"Hash chain broken at event index {i}!"
            if i > 0:
                assert entry["previous_hash"] == history[i - 1]["event_hash"]
        print(f"[PASS] 10. Chain of Custody: {len(history)} events cryptographically sealed and verified")

        # Step 11: Real-time Dashboard Evidence Statistics
        stats_res = client.get("/api/evidence/stats", headers=admin_headers)
        assert stats_res.status_code == 200
        stats = stats_res.json()
        assert stats["total_evidence"] >= 1
        assert stats["tampered_evidence"] >= 1
        print(f"[PASS] 11. Dashboard Evidence Stats: Validated -> {stats}")

        # Step 12: Path Traversal Prevention
        print("\n--- Testing Security Safeguards & Path Traversal Prevention ---")
        traversal_res = client.post(
            f"/api/cases/{case_id}/evidence",
            files={"file": ("../../../../etc/passwd", io.BytesIO(b"root:x:0:0::/root:/bin/bash"), "text/plain")},
            data={"description": "Path traversal probe"},
            headers=admin_headers
        )
        assert traversal_res.status_code == 201  # Should be safely sanitized, NOT written to /etc/passwd
        sanitized_ev = traversal_res.json()
        assert sanitized_ev["stored_filename"] == "etc_passwd" or "passwd" in sanitized_ev["stored_filename"]
        assert not os.path.exists("../../../../etc/passwd")
        print(f"[PASS] 12. Path Traversal Safeguard: Malicious filename sanitized to '{sanitized_ev['stored_filename']}'")

        # Step 13: Role Authorization
        # Create or fetch a readonly user or test unauthenticated
        no_auth_res = client.post(f"/api/cases/{case_id}/evidence")
        assert no_auth_res.status_code in (401, 403), "Unauthenticated upload must be rejected"

        no_auth_verify = client.post(f"/api/evidence/{evidence1_id}/verify")
        assert no_auth_verify.status_code in (401, 403), "Unauthenticated verify must be rejected"
        print("[PASS] 13. Role Authorization: Unauthenticated requests blocked with 401/403")

        # Step 14: Global Evidence Search & Filtering
        all_ev_res = client.get(f"/api/evidence?search=incident_db_dump", headers=admin_headers)
        assert all_ev_res.status_code == 200
        found_ev = all_ev_res.json()["evidence"]
        assert any(e["_id"] == evidence1_id for e in found_ev)

        tampered_filter = client.get("/api/evidence?integrity_status=TAMPERED", headers=admin_headers)
        assert tampered_filter.status_code == 200
        tampered_items = tampered_filter.json()["evidence"]
        assert any(e["_id"] == evidence1_id for e in tampered_items)
        print(f"[PASS] 14. Global Evidence Vault Search & Filter: Correctly found {len(found_ev)} by query, {len(tampered_items)} tampered")

        # Step 15: Non-existent IDs (404 Handling)
        bad_get = client.get("/api/evidence/65f000000000000000000000", headers=admin_headers)
        assert bad_get.status_code == 404
        bad_verify = client.post("/api/evidence/65f000000000000000000000/verify", headers=admin_headers)
        assert bad_verify.status_code == 404
        print("[PASS] 15. Error Handling: Non-existent evidence returns 404")

    print("\n==================================================================")
    print("ALL PHASE 2 (MILESTONE 3) EVIDENCE TESTS PASSED WITH ZERO FAILURES!")
    print("==================================================================")

if __name__ == "__main__":
    run_milestone3_tests()
