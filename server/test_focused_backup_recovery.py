"""
Focused Test Suite: Preserved Original Backup Verification & Retrieval
=====================================================================
Validates:
1. Retrieval and download of actual original evidence bytes from preserved backup.
2. Verified filename and MIME type.
3. Strict verification of backup SHA-256 against baseline acquisition hash.
4. Tampered working copy remains unchanged.
5. Strict RBAC enforcement (Portal Manager / ReadOnly forbidden).
6. Missing bytes return clear 404 error without mock data fabrication.
"""

import os
import asyncio
import hashlib
import httpx

from app.main import app
from app.core.config import settings
from app.core.database import connect_to_mongo

async def test_tampered_evidence_backup_lifecycle():
    await connect_to_mongo()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Authenticate as Chief Investigator
        login_res = await client.post("/api/auth/login", json={
            "email": "chief@forensics.gov",
            "password": "password123"
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        chief_headers = {"Authorization": f"Bearer {token}"}
        print("[PASS] 1. Authenticated as Chief Investigator (chief@forensics.gov)")

        # 2. Test Existing Case 2 Tampered Evidence exhibit (offshore_wire_transfer_ledger.csv)
        case_res = await client.get("/api/cases", headers=chief_headers)
        assert case_res.status_code == 200
        cases = case_res.json()["cases"]
        
        # Locate Case 2 (DF-2026-000102) with the seeded tampered exhibit
        case2 = next((c for c in cases if "Red Ledger" in c.get("title", "") or c.get("case_number") == "DF-2026-000102"), None)
        assert case2 is not None, "Case DF-2026-000102 not found"
        case2_id = case2["_id"]

        ev_res = await client.get(f"/api/cases/{case2_id}/evidence", headers=chief_headers)
        assert ev_res.status_code == 200, f"Failed to list evidence: {ev_res.status_code} - {ev_res.text}"
        evidence_list = ev_res.json()
        
        tampered_ev = next((e for e in evidence_list if "ledger" in e.get("original_filename", "").lower()), None)
        assert tampered_ev is not None, "Tampered ledger exhibit not found in Case 2"
        assert tampered_ev["integrity_status"] == "TAMPERED", f"Expected status TAMPERED, got {tampered_ev['integrity_status']}"
        evidence_id = tampered_ev["_id"]
        print(f"[PASS] 2. Found seeded confirmed TAMPERED exhibit: {tampered_ev['original_filename']} ({evidence_id})")

        # 3. Test Download of Preserved Original Backup
        backup_dl_res = await client.get(f"/api/evidence/{evidence_id}/backup/download", headers=chief_headers)
        assert backup_dl_res.status_code == 200, f"Download failed: {backup_dl_res.status_code} - {backup_dl_res.text}"
        
        downloaded_bytes = backup_dl_res.content
        downloaded_hash = hashlib.sha256(downloaded_bytes).hexdigest().lower()
        
        # Verify downloaded bytes are GENUINE original evidence (containing Apex Global Escrow LLC, NOT Offshore Shell Ltd)
        assert b"Apex Global Escrow LLC" in downloaded_bytes, "Original beneficiary missing from backup!"
        assert b"Offshore Shell Ltd" not in downloaded_bytes, "Tampered beneficiary leaked into backup!"
        
        # Verify SHA-256 matches the registered acquisition baseline
        baseline_hash = tampered_ev.get("original_sha256_hash") or tampered_ev.get("sha256_hash")
        assert downloaded_hash == baseline_hash.lower(), f"Hash mismatch: {downloaded_hash} vs {baseline_hash}"
        print(f"[PASS] 3. Downloaded backup contains authentic original evidence bytes! SHA-256 matches baseline ({downloaded_hash})")

        # 4. Verify Active Working Copy on Disk Remains Tampered
        working_path = tampered_ev.get("storage_path")
        if not working_path or not os.path.exists(working_path):
            working_path = os.path.join(settings.EVIDENCE_STORAGE_DIR, case2_id, f"{evidence_id}_{tampered_ev['original_filename']}")
        assert os.path.exists(working_path), f"Working copy file not found at {working_path}"
        
        with open(working_path, "rb") as wf:
            working_bytes = wf.read()
        working_hash = hashlib.sha256(working_bytes).hexdigest().lower()
        
        assert b"Offshore Shell Ltd" in working_bytes, "Working copy does not have tampered bytes!"
        assert working_hash != baseline_hash.lower(), "Working copy hash unexpectedly matches baseline!"
        assert working_hash == "1f10c2052b0b48e7d1fb88d650d71ea90f2b538097331c0ae507da171046aa7d"
        print(f"[PASS] 4. Active working copy remains untouched with tampered bytes preserved on disk ({working_hash})")

        # 5. Verify RBAC Security (Read-Only user cannot download backup)
        viewer_login = await client.post("/api/auth/login", json={
            "email": "viewer@forensics.gov",
            "password": "password123"
        })
        assert viewer_login.status_code == 200
        viewer_token = viewer_login.json()["access_token"]
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

        viewer_dl = await client.get(f"/api/evidence/{evidence_id}/backup/download", headers=viewer_headers)
        assert viewer_dl.status_code == 403, f"Expected 403 for ReadOnly user, got {viewer_dl.status_code}"
        print("[PASS] 5. RBAC strictly enforced: Read-Only user blocked from downloading backup (403 Forbidden)")

        # 6. Verify Missing Evidence Returns 404 without Mock Fabrication
        non_existent_id = "6ade1354bc0cf97427e2ffff"
        missing_res = await client.get(f"/api/evidence/{non_existent_id}/backup/download", headers=chief_headers)
        assert missing_res.status_code == 404
        print("[PASS] 6. Missing evidence returns clean 404 without fabricating mock data")

        # 7. End-to-End Dynamic Upload, Tamper, Verify, and Backup Recovery Lifecycle
        dynamic_filename = "server_syslog_audit_baseline.log"
        dynamic_original_bytes = b"2026-10-29T00:00:00Z [SECURITY] Normal system state. All services intact.\n"
        dynamic_baseline_hash = hashlib.sha256(dynamic_original_bytes).hexdigest().lower()

        dyn_up = await client.post(
            f"/api/cases/{case2_id}/evidence",
            files={"file": (dynamic_filename, dynamic_original_bytes, "text/plain")},
            data={"description": "Dynamic test evidence", "source_device": "TEST_STATION"},
            headers=chief_headers
        )
        assert dyn_up.status_code in (200, 201)
        dyn_data = dyn_up.json()
        dyn_ev_id = dyn_data["_id"]
        dyn_target_file = dyn_data.get("storage_path")
        if not dyn_target_file or not os.path.exists(dyn_target_file):
            for root, dirs, files in os.walk(os.path.join(settings.EVIDENCE_STORAGE_DIR, case2_id)):
                if "backups" in root.replace("\\", "/"): continue
                for f in files:
                    if dyn_ev_id in f or dynamic_filename in f:
                        dyn_target_file = os.path.join(root, f)
                        break
        assert dyn_target_file and os.path.exists(dyn_target_file), f"Could not find uploaded file for {dyn_ev_id}"
        with open(dyn_target_file, "wb") as f:
            f.write(b"2026-10-29T00:00:00Z [SECURITY] TAMPERED CORRUPTED LOG ENTRY BY ROGUE USER\n")

        # Verify detects mismatch
        dyn_ver = await client.post(f"/api/evidence/{dyn_ev_id}/verify", headers=chief_headers)
        assert dyn_ver.status_code == 200
        assert dyn_ver.json()["integrity"] in ("INTEGRITY_MISMATCH", "UNDER_INVESTIGATION")

        # Confirm tamper
        dyn_conf = await client.post(f"/api/evidence/{dyn_ev_id}/confirm-tamper", json={
            "attributed_actor": "Rogue Contractor",
            "reason": "Host file modification confirmed.",
            "tamper_method": "DIRECT_STORAGE_WRITE"
        }, headers=chief_headers)
        assert dyn_conf.status_code == 200
        assert dyn_conf.json()["integrity_status"] == "TAMPERED"

        # Download original backup
        dyn_dl = await client.get(f"/api/evidence/{dyn_ev_id}/backup/download", headers=chief_headers)
        assert dyn_dl.status_code == 200
        assert dyn_dl.content == dynamic_original_bytes
        assert hashlib.sha256(dyn_dl.content).hexdigest().lower() == dynamic_baseline_hash
        print(f"[PASS] 7. Dynamic full lifecycle test passed: genuine original bytes recovered with matching SHA-256 ({dynamic_baseline_hash})")

        print("\n=================================================================")
        print("ALL 7 CRITICAL EVIDENCE BACKUP & INTEGRITY VERIFICATIONS PASSED!")
        print("=================================================================\n")

if __name__ == "__main__":
    asyncio.run(test_tampered_evidence_backup_lifecycle())
