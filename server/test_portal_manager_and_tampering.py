import os
import io
import hashlib
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.routers.settings import _global_settings_cache

def run_tests():
    print("==================================================================")
    print("CRYPTEVID: PORTAL MANAGER ROLE & EVIDENCE TAMPERING TEST SUITE")
    print("==================================================================")

    _global_settings_cache["simulation_mode"] = True

    with TestClient(app) as client:
        # Step 0: Obtain Admin Token
        admin_token = create_access_token(subject="admin@forensics.gov", role="admin")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print("[PASS] 0. Admin Authentication: Obtained JWT Bearer token")

        # Ensure Portal Manager exists and obtain token
        pm_token = create_access_token(subject="manager@forensics.gov", role="portal_manager")
        pm_headers = {"Authorization": f"Bearer {pm_token}"}
        
        # Verify portal manager can fetch their own profile
        me_res = client.get("/api/auth/me", headers=pm_headers)
        if me_res.status_code != 200:
            client.post("/api/auth/register", json={
                "email": "manager@forensics.gov",
                "password": "password123",
                "full_name": "Portal Supervisor Sarah",
                "badge_number": "PM-9001",
                "role": "portal_manager"
            })
            me_res = client.get("/api/auth/me", headers=pm_headers)
        assert me_res.status_code == 200, f"Failed to get PM profile: {me_res.text}"
        pm_user_id = me_res.json()["_id"]
        print(f"[PASS] 0. Portal Manager Authentication: Verified role {me_res.json().get('role')}")

        # Step 1: Portal Manager can access the dashboard
        pm_overview = client.get("/api/portal-manager/overview", headers=pm_headers)
        assert pm_overview.status_code == 200, f"Dashboard access failed: {pm_overview.text}"
        overview_data = pm_overview.json()
        assert "total_users" in overview_data
        assert "total_cases" in overview_data
        assert "total_assigned_officers" in overview_data
        # Evidence data must NOT be present in dashboard metrics
        assert "evidence_list" not in overview_data
        assert "vault_paths" not in overview_data
        print("[PASS] 1. Portal Manager can access dashboard with privacy-safe metrics")

        # Step 2: Portal Manager can list permitted user details (no secrets exposed)
        users_res = client.get("/api/portal-manager/users", headers=pm_headers)
        assert users_res.status_code == 200, f"User list failed: {users_res.text}"
        users_list = users_res.json()["users"]
        assert len(users_list) > 0
        for u in users_list:
            assert "password_hash" not in u
            assert "rfid_secret" not in u
            assert "fingerprint_template" not in u
            assert "pin_salt" not in u
            assert "rfid_uid" not in u
        print("[PASS] 2. Portal Manager lists permitted user directory without credential secrets")

        # Step 3: Portal Manager can view case lists and assigned officer information (no evidence)
        cases_res = client.get("/api/portal-manager/cases", headers=pm_headers)
        assert cases_res.status_code == 200, f"Cases list failed: {cases_res.text}"
        cases_list = cases_res.json()["cases"]
        assert len(cases_list) > 0
        for c in cases_list:
            assert "case_number" in c
            assert "assigned_investigator_name" in c
            # Evidence items must not be leaked in case oversight
            assert "evidence_files" not in c
            assert "evidence_hashes" not in c
        print("[PASS] 3. Portal Manager views case lists and officer assignments without evidence leak")

        # Create an isolated dummy case and evidence using Admin for evidence tests
        dummy_case = client.post("/api/cases", json={
            "title": "Isolated Forensic Exhibit Integrity Test",
            "description": "Case created exclusively to validate evidence integrity, tampering intelligence, and original backup workflows.",
            "case_type": "DATA_BREACH",
            "priority": "HIGH",
            "tags": ["INTEGRITY_TEST", "ISOLATED"]
        }, headers=admin_headers).json()
        case_id = dummy_case["_id"]

        dummy_bytes = b"CRYPTEVID_ISOLATED_EVIDENCE_EXHIBIT_ALPHA_ORIGINAL_PRESERVED_2026"
        dummy_hash = hashlib.sha256(dummy_bytes).hexdigest().lower()
        upload_res = client.post(
            f"/api/cases/{case_id}/evidence",
            files={"file": ("exhibit_alpha.bin", io.BytesIO(dummy_bytes), "application/octet-stream")},
            data={"description": "Original baseline exhibit for tampering testing", "source_device": "WORKSTATION_01"},
            headers=admin_headers
        )
        assert upload_res.status_code == 201, f"Upload failed: {upload_res.text}"
        evidence = upload_res.json()
        evidence_id = evidence["_id"]
        file_path = evidence.get("file_path")
        print(f"[PASS] Setup: Created isolated test exhibit {evidence_id}")

        # Step 4: Portal Manager cannot retrieve evidence bytes
        dl_res = client.get(f"/api/evidence/{evidence_id}/download", headers=pm_headers)
        assert dl_res.status_code == 403, f"Expected 403 Forbidden for PM evidence download, got {dl_res.status_code}"
        print("[PASS] 4. Portal Manager cannot retrieve evidence bytes (403 Forbidden enforced)")

        # Step 5: Portal Manager cannot download original evidence or sensitive reports
        ev_view_res = client.get(f"/api/evidence/{evidence_id}", headers=pm_headers)
        assert ev_view_res.status_code == 403, f"Expected 403 Forbidden for PM evidence view, got {ev_view_res.status_code}"
        
        rep_gen_res = client.post(f"/api/cases/{case_id}/reports", json={
            "title": "Confidential Report",
            "classification": "TOP SECRET"
        }, headers=pm_headers)
        assert rep_gen_res.status_code == 403, f"Expected 403 Forbidden for PM report generation, got {rep_gen_res.status_code}"
        print("[PASS] 5. Portal Manager cannot view evidence metadata or generate/download reports")

        # Step 6: Portal Manager cannot bypass permissions through direct API requests
        verify_bypass = client.post(f"/api/evidence/{evidence_id}/verify", headers=pm_headers)
        assert verify_bypass.status_code == 403, f"Expected 403 for PM direct verify call, got {verify_bypass.status_code}"
        
        custody_bypass = client.get(f"/api/evidence/{evidence_id}/custody", headers=pm_headers)
        assert custody_bypass.status_code == 403, f"Expected 403 for PM custody call, got {custody_bypass.status_code}"
        print("[PASS] 6. Portal Manager cannot bypass permissions through direct API requests")

        # Step 7: Portal Manager cannot escalate privileges
        # Attempt to create an admin account
        esc_create = client.post("/api/portal-manager/users", json={
            "email": "hacked_admin@forensics.gov",
            "password": "password123",
            "full_name": "Rogue Admin",
            "role": "admin"
        }, headers=pm_headers)
        assert esc_create.status_code == 403, f"Expected 403 on admin creation attempt, got {esc_create.status_code}"

        # Attempt to promote self to admin
        esc_promote = client.patch(f"/api/portal-manager/users/{pm_user_id}", json={
            "role": "admin"
        }, headers=pm_headers)
        assert esc_promote.status_code == 403, f"Expected 403 on self-promotion attempt, got {esc_promote.status_code}"
        print("[PASS] 7. Privilege escalation strictly blocked (cannot create admin or self-promote)")

        # Step 8: Unmodified evidence verifies successfully
        verify_res = client.post(f"/api/evidence/{evidence_id}/verify", headers=admin_headers)
        assert verify_res.status_code == 200
        verify_data = verify_res.json()
        assert verify_data["integrity"] == "VERIFIED"
        assert verify_data["calculated_hash"] == dummy_hash
        print("[PASS] 8. Unmodified evidence verifies successfully (VERIFIED)")

        # Step 9: Modified evidence produces a hash mismatch
        # Simulate unauthorized raw byte modification on disk
        from app.core.config import settings
        ev_dir = os.path.join(settings.EVIDENCE_STORAGE_DIR, case_id, evidence_id)
        assert os.path.exists(ev_dir), f"Evidence directory not found at {ev_dir}"
        disk_files = [f for f in os.listdir(ev_dir) if not f.endswith(".bak")]
        assert len(disk_files) > 0, "No files in evidence dir"
        file_path = os.path.join(ev_dir, disk_files[0])

        with open(file_path, "wb") as f:
            f.write(b"CORRUPTED_RAW_BYTES_OUTSIDE_OF_API_CALL")
        
        tampered_disk_hash = hashlib.sha256(b"CORRUPTED_RAW_BYTES_OUTSIDE_OF_API_CALL").hexdigest().lower()
        verify_mismatch_res = client.post(f"/api/evidence/{evidence_id}/verify", headers=admin_headers)
        assert verify_mismatch_res.status_code == 200
        mismatch_data = verify_mismatch_res.json()
        assert mismatch_data["calculated_hash"] == tampered_disk_hash
        print("[PASS] 9. Modified evidence produces cryptographic hash mismatch")

        # Step 12: An unattributed mismatch is marked for investigation rather than falsely attributing an attacker (Rule C)
        assert mismatch_data["integrity"] in ("INTEGRITY_MISMATCH", "UNDER_INVESTIGATION"), f"Expected INTEGRITY_MISMATCH/UNDER_INVESTIGATION, got {mismatch_data['integrity']}"
        ev_after_unattributed = client.get(f"/api/evidence/{evidence_id}", headers=admin_headers).json()
        assert ev_after_unattributed["integrity_status"] in ("INTEGRITY_MISMATCH", "UNDER_INVESTIGATION")
        print("[PASS] 12. Unattributed mismatch correctly classified as INTEGRITY_MISMATCH / UNDER_INVESTIGATION (Rule C)")

        # Step 10: An unauthorized, reliably attributed modification is marked "TAMPERED" (Rule A)
        confirm_tamper_res = client.post(f"/api/evidence/{evidence_id}/confirm-tamper", json={
            "attributed_actor": "Suspect Malory (Rogue Contractor)",
            "investigation_notes": "Forensic disk analysis confirmed unauthorized byte replacement on host storage sector.",
            "tamper_method": "DIRECT_STORAGE_WRITE"
        }, headers=admin_headers)
        assert confirm_tamper_res.status_code == 200
        ev_tampered = confirm_tamper_res.json()
        assert ev_tampered["integrity_status"] == "TAMPERED"
        assert ev_tampered["tamper_details"]["attributed_actor"] == "Suspect Malory (Rogue Contractor)"
        print("[PASS] 10. Reliably attributed unauthorized change classified as confirmed TAMPERED (Rule A)")

        # Step 13: Original evidence bytes and original hash remain unchanged after simulated tampering
        assert ev_tampered["original_sha256_hash"] == dummy_hash
        
        # Locate the backup file on disk
        backup_case_dir = os.path.join(settings.BACKUP_STORAGE_DIR, case_id)
        backup_path = None
        for root, dirs, files in os.walk(backup_case_dir):
            for file in files:
                if file.startswith("exhibit_alpha"):
                    backup_path = os.path.join(root, file)
                    break
        assert backup_path and os.path.exists(backup_path), f"Backup path does not exist in {backup_case_dir}"
        with open(backup_path, "rb") as bf:
            backup_bytes = bf.read()
        assert backup_bytes == dummy_bytes, "Preserved backup bytes were mutated!"
        print("[PASS] 13. Original evidence bytes and baseline SHA-256 hash remain intact and immutable")

        # Step 14: Original Evidence Backup appears only for confirmed tampered evidence
        assert ev_tampered["has_original_backup"] is True
        assert ev_tampered["integrity_status"] == "TAMPERED"
        print("[PASS] 14. Original Evidence Backup section criteria satisfied for confirmed tampered exhibit")

        # Step 15: The original backup download endpoint enforces permissions
        # PM blocked from downloading backup
        pm_backup_dl = client.get(f"/api/evidence/{evidence_id}/backup/download", headers=pm_headers)
        assert pm_backup_dl.status_code == 403, f"Expected 403 Forbidden for PM backup download, got {pm_backup_dl.status_code}"

        # Admin authorized to download backup
        admin_backup_dl = client.get(f"/api/evidence/{evidence_id}/backup/download", headers=admin_headers)
        assert admin_backup_dl.status_code == 200, f"Admin backup download failed: {admin_backup_dl.status_code}"
        assert admin_backup_dl.content == dummy_bytes
        print("[PASS] 15. Original backup download endpoint strictly enforces permissions (403 for PM, 200 for Admin)")

        # Step 11: An authorized modification is recorded as a new version and is not falsely marked as unauthorized tampering (Rule B)
        new_version_bytes = b"OFFICIAL_AUTHORIZED_REDACTED_EVIDENCE_EXHIBIT_VERSION_2_CORRECT"
        new_version_hash = hashlib.sha256(new_version_bytes).hexdigest().lower()
        
        modify_res = client.post(
            f"/api/evidence/{evidence_id}/modify",
            files={"file": ("exhibit_alpha_v2_redacted.bin", io.BytesIO(new_version_bytes), "application/octet-stream")},
            data={
                "reason": "Authorized court-ordered PII redaction of witness identifiers",
                "operation": "PII_REDACTION"
            },
            headers=admin_headers
        )
        assert modify_res.status_code == 200, f"Authorized modification failed: {modify_res.text}"
        ev_v2 = modify_res.json()
        assert ev_v2["version"] == 2
        assert ev_v2["integrity_status"] == "VERIFIED", f"Expected VERIFIED, got {ev_v2['integrity_status']}"
        assert ev_v2["sha256_hash"] == new_version_hash
        assert ev_v2["original_sha256_hash"] == dummy_hash
        assert len(ev_v2.get("version_history", [])) >= 1
        v1_record = ev_v2["version_history"][0]
        assert v1_record["version"] == 1
        assert v1_record["sha256_hash"] == dummy_hash
        print("[PASS] 11. Authorized modification recorded as Version 2 with history, remaining VERIFIED (Rule B)")

        # Step 16: Missing or corrupted backups are handled safely
        # Corrupt the backup file
        with open(backup_path, "wb") as bf:
            bf.write(b"CORRUPTED_BACKUP_BITS")
        corrupted_dl = client.get(f"/api/evidence/{evidence_id}/backup/download", headers=admin_headers)
        assert corrupted_dl.status_code == 409, f"Expected 409 Conflict for corrupted backup, got {corrupted_dl.status_code}"
        
        # Test missing backup
        os.remove(backup_path)
        missing_dl = client.get(f"/api/evidence/{evidence_id}/backup/download", headers=admin_headers)
        assert missing_dl.status_code == 404, f"Expected 404 Not Found for missing backup, got {missing_dl.status_code}"
        print("[PASS] 16. Missing (404) and corrupted (409) backups are safely detected and handled")

        # Step 17: Audit records are created for sensitive operations
        # Verify audit custody events for this evidence
        custody_res = client.get(f"/api/evidence/{evidence_id}/custody", headers=admin_headers)
        assert custody_res.status_code == 200
        events = custody_res.json()["custody_events"]
        action_names = [e["action"] for e in events]
        print(f"Recorded custody actions: {action_names}")
        assert any(a in action_names for a in ("EVIDENCE_UPLOADED", "EVIDENCE_INGESTION"))
        assert any("TAMPER" in a for a in action_names)
        assert "AUTHORIZED_MODIFICATION" in action_names
        assert "BACKUP_DOWNLOADED" in action_names
        print("[PASS] 17. Security audit records created for ingestion, tampering, modification, and backup download")

    print("==================================================================")
    print("ALL 17 TESTS PASSED SUCCESSFULLY!")
    print("==================================================================")

if __name__ == "__main__":
    run_tests()
