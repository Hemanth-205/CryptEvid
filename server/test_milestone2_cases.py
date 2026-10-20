import io
import json
import zipfile
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.services.metadata_service import MetadataExtractionService

def run_milestone2_tests():
    print("==================================================================")
    print("RUNNING PHASE 1 (MILESTONE 2) CASE REGISTRY & METADATA TEST SUITE")
    print("==================================================================")

    with TestClient(app) as client:
        # Step 0: Login as Admin to obtain JWT
        login_res = client.post("/api/auth/login", json={
            "email": "admin@forensics.gov",
            "password": "password123"
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        admin_token = login_res.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print("[PASS] 0. Admin Authentication: Obtained JWT Bearer token")

        # Step 1: Investigators Listing
        inv_res = client.get("/api/investigators", headers=admin_headers)
        assert inv_res.status_code == 200
        investigators = inv_res.json()
        assert len(investigators) > 0
        investigator_id = investigators[0]["_id"]
        print(f"[PASS] 1. Investigators list: Found {len(investigators)} investigator(s) for assignment")

        # Step 2: Create First Case
        case1_payload = {
            "title": "Operation Nightshade - Unauthorized Exfiltration",
            "description": "Suspected breach of engineering subnet with outbound HTTPS beaconing.",
            "case_type": "DATA_BREACH",
            "priority": "HIGH",
            "assigned_investigator": investigator_id,
            "tags": ["BREACH", "EXFILTRATION", "ENGINEERING"],
            "initial_note": "Incident flagged by EDR at 03:14 UTC."
        }
        create1_res = client.post("/api/cases", json=case1_payload, headers=admin_headers)
        assert create1_res.status_code == 201, f"Create case failed: {create1_res.text}"
        case1 = create1_res.json()
        assert case1["case_number"].startswith("DF-")
        assert case1["title"] == case1_payload["title"]
        assert case1["status"] == "OPEN"
        assert len(case1["notes"]) == 1
        case1_id = case1["_id"]
        case1_num = case1["case_number"]
        print(f"[PASS] 2. Case Creation 1: Created {case1_num} (Status: {case1['status']})")

        # Step 3: Create Second Case to verify Unique Case Number sequence
        case2_payload = {
            "title": "Phishing Campaign Targeting Finance Executives",
            "description": "Credential harvesting landing page reported by CFO office.",
            "case_type": "PHISHING",
            "priority": "CRITICAL",
            "tags": ["PHISHING", "FINANCE", "VIP"],
            "initial_note": "Suspicious domain registered 24h prior."
        }
        create2_res = client.post("/api/cases", json=case2_payload, headers=admin_headers)
        assert create2_res.status_code == 201
        case2 = create2_res.json()
        case2_id = case2["_id"]
        case2_num = case2["case_number"]
        assert case2_num != case1_num, "Case numbers must be distinct"
        print(f"[PASS] 3. Unique Case Number sequence: {case1_num} -> {case2_num}")

        # Step 4: List Cases with Pagination
        list_res = client.get("/api/cases?limit=10&skip=0", headers=admin_headers)
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert list_data["total"] >= 2
        assert len(list_data["cases"]) >= 2
        print(f"[PASS] 4. Case Listing: Found {list_data['total']} total cases")

        # Step 5: Server-side Search
        search_res = client.get(f"/api/cases?search={case1_num}", headers=admin_headers)
        assert search_res.status_code == 200
        search_cases = search_res.json()["cases"]
        assert any(c["case_number"] == case1_num for c in search_cases)
        assert not any(c["case_number"] == case2_num for c in search_cases)
        print(f"[PASS] 5. Server-side Search by Case Number: Correctly isolated {case1_num}")

        # Step 6: Server-side Filtering by Priority
        filter_crit = client.get("/api/cases?priority=CRITICAL", headers=admin_headers)
        assert filter_crit.status_code == 200
        crit_cases = filter_crit.json()["cases"]
        assert all(c["priority"] == "CRITICAL" for c in crit_cases)
        assert any(c["_id"] == case2_id for c in crit_cases)
        print(f"[PASS] 6. Server-side Filter by Priority (CRITICAL): {len(crit_cases)} case(s) found")

        # Step 7: Server-side Filtering by Case Type
        filter_type = client.get("/api/cases?case_type=PHISHING", headers=admin_headers)
        assert filter_type.status_code == 200
        phish_cases = filter_type.json()["cases"]
        assert all(c["case_type"] == "PHISHING" for c in phish_cases)
        print(f"[PASS] 7. Server-side Filter by Case Type (PHISHING): {len(phish_cases)} case(s) found")

        # Step 8: Get Individual Case Details
        get_res = client.get(f"/api/cases/{case1_id}", headers=admin_headers)
        assert get_res.status_code == 200
        case_detail = get_res.json()
        assert case_detail["_id"] == case1_id
        assert case_detail["case_number"] == case1_num
        assert case_detail.get("created_by_name") is not None
        print(f"[PASS] 8. Get Individual Case Details: Verified metadata & investigator hydration")

        # Step 9: Update Case Properties
        update_res = client.put(f"/api/cases/{case1_id}", json={
            "title": "Operation Nightshade - Confirmed Data Leakage",
            "priority": "CRITICAL",
            "description": "Updated assessment: 1.2GB archived databases transferred via encrypted channel.",
            "tags": ["BREACH", "EXFILTRATION", "CONFIRMED"]
        }, headers=admin_headers)
        assert update_res.status_code == 200
        updated = update_res.json()
        assert updated["priority"] == "CRITICAL"
        assert updated["title"] == "Operation Nightshade - Confirmed Data Leakage"
        print(f"[PASS] 9. Update Case Metadata: Priority escalated to CRITICAL, description refreshed")

        # Step 10: Append Investigation Note
        note_res = client.post(f"/api/cases/{case1_id}/notes", json={
            "content": "Malware reverse engineering confirms C2 domain match with known threat actor."
        }, headers=admin_headers)
        assert note_res.status_code == 200
        assert len(note_res.json()["notes"]) == 2
        print(f"[PASS] 10. Append Investigation Note: Note ledger contains {len(note_res.json()['notes'])} entries")

        # Step 11: Case Status Transition (OPEN -> IN_PROGRESS -> CLOSED)
        patch_res = client.patch(f"/api/cases/{case1_id}/status", json={"status": "IN_PROGRESS"}, headers=admin_headers)
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "IN_PROGRESS"

        close_res = client.patch(f"/api/cases/{case1_id}/status", json={"status": "CLOSED"}, headers=admin_headers)
        assert close_res.status_code == 200
        assert close_res.json()["status"] == "CLOSED"
        assert close_res.json()["closed_at"] is not None
        print(f"[PASS] 11. Case Status Transition: OPEN -> IN_PROGRESS -> CLOSED (closed_at timestamp set)")

        # Step 12: Real-time Dashboard Statistics
        stats_res = client.get("/api/cases/stats", headers=admin_headers)
        assert stats_res.status_code == 200
        stats = stats_res.json()
        assert stats["total_cases"] >= 2
        assert stats["closed_cases"] >= 1
        assert stats["critical_cases"] >= 1
        print(f"[PASS] 12. Dashboard Case Stats: Real data validated -> {stats}")

        # Step 13: Case Archive (Soft-Delete)
        archive_res = client.delete(f"/api/cases/{case2_id}", headers=admin_headers)
        assert archive_res.status_code == 200
        # Verify case is now ARCHIVED
        archived_case = client.get(f"/api/cases/{case2_id}", headers=admin_headers).json()
        assert archived_case["status"] == "ARCHIVED"
        # Verify it does not appear in default listing (without include_archived=True)
        default_list = client.get("/api/cases", headers=admin_headers).json()["cases"]
        assert not any(c["_id"] == case2_id for c in default_list)
        # Verify it appears when include_archived=True
        archived_list = client.get("/api/cases?include_archived=true", headers=admin_headers).json()["cases"]
        assert any(c["_id"] == case2_id for c in archived_list)
        print(f"[PASS] 13. Soft-Delete Archive: Case preserved for chain of custody with status ARCHIVED")

        # Step 14: Error Handling & Security Validation
        # Missing/Short title validation
        bad_create = client.post("/api/cases", json={"title": "No"}, headers=admin_headers)
        assert bad_create.status_code == 422, "Short title should trigger 422 Unprocessable Entity"

        # Nonexistent case 404
        bad_get = client.get("/api/cases/65f000000000000000000000", headers=admin_headers)
        assert bad_get.status_code == 404, "Unknown case should return 404"

        # Unauthenticated request
        no_auth = client.get("/api/cases")
        assert no_auth.status_code in (401, 403), "Missing token must be rejected"
        print("[PASS] 14. Error Handling: 422 validation, 404 CASE_NOT_FOUND, 401/403 authorization confirmed")

        # Step 15: Chain of Custody Audit Log Generation for Case Operations
        audit_res = client.get("/api/audit-logs?limit=50", headers=admin_headers)
        assert audit_res.status_code == 200
        logs = audit_res.json()
        logged_actions = [l["action"] for l in logs]
        assert "CASE_CREATED" in logged_actions, "CASE_CREATED must be recorded"
        assert "CASE_VIEWED" in logged_actions, "CASE_VIEWED must be recorded"
        assert "CASE_UPDATED" in logged_actions, "CASE_UPDATED must be recorded"
        assert "CASE_STATUS_CHANGED" in logged_actions, "CASE_STATUS_CHANGED must be recorded"
        assert "CASE_ARCHIVED" in logged_actions, "CASE_ARCHIVED must be recorded"
        print(f"[PASS] 15. Audit Trail Verification: CASE_CREATED, VIEWED, UPDATED, STATUS_CHANGED, ARCHIVED all logged")

        # Step 16: MetadataExtractionService Unit Verification
        print("\n--- Testing MetadataExtractionService on Multiple File Types ---")

        # Image Extraction (PNG)
        img_buffer = io.BytesIO()
        test_img = Image.new('RGB', (320, 240), color='blue')
        test_img.save(img_buffer, format='PNG')
        png_bytes = img_buffer.getvalue()
        img_status, img_attrs, lat, lon, err = MetadataExtractionService.extract("forensic_snapshot.png", png_bytes)
        assert img_status == "EXTRACTED"
        assert img_attrs["width"] == 320
        assert img_attrs["height"] == 240
        assert img_attrs["format"] == "PNG"
        assert lat is None and lon is None  # No fake GPS!
        print("[PASS] 16a. Metadata Image: Dimensions (320x240), format (PNG), safe null GPS")

        # Text/Log Extraction
        log_content = "2026-09-03 11:15:00 [SECURITY] Failed login attempt from 192.168.1.10\n2026-09-03 11:15:05 [SECURITY] Port scan detected\n2026-09-03 11:15:10 [SECURITY] Alert triggered\n"
        log_bytes = log_content.encode("utf-8")
        txt_status, txt_attrs, _, _, _ = MetadataExtractionService.extract("auth_failure.log", log_bytes)
        assert txt_status == "EXTRACTED"
        assert txt_attrs["line_count"] == 3
        assert txt_attrs["detected_encoding"] == "utf-8"
        print(f"[PASS] 16b. Metadata Text/Log: line_count={txt_attrs['line_count']}, encoding={txt_attrs['detected_encoding']}")

        # CSV Extraction
        csv_content = "timestamp,source_ip,destination_ip,port,action\n2026-09-03 10:00:00,10.0.0.1,10.0.0.2,443,ALLOW\n2026-09-03 10:00:01,10.0.0.3,10.0.0.2,22,DROP\n"
        csv_bytes = csv_content.encode("utf-8")
        csv_status, csv_attrs, _, _, _ = MetadataExtractionService.extract("firewall_traffic.csv", csv_bytes)
        assert csv_status == "EXTRACTED"
        assert csv_attrs["row_count"] == 3
        assert csv_attrs["column_count"] == 5
        print(f"[PASS] 16c. Metadata CSV: rows={csv_attrs['row_count']}, columns={csv_attrs['column_count']}, delimiter='{csv_attrs['detected_delimiter']}'")

        # JSON Extraction
        json_dict = {"event_id": 1001, "source": "snort_sensor_01", "classification": "trojan-activity", "severity": 3}
        json_bytes = json.dumps(json_dict).encode("utf-8")
        json_status, json_attrs, _, _, _ = MetadataExtractionService.extract("telemetry.json", json_bytes)
        assert json_status == "EXTRACTED"
        assert json_attrs["is_valid_json"] is True
        assert json_attrs["root_type"] == "object"
        assert json_attrs["key_count"] == 4
        print(f"[PASS] 16d. Metadata JSON: valid={json_attrs['is_valid_json']}, key_count={json_attrs['key_count']}")

        # ZIP Extraction
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("evidence_log.txt", "Log data 12345")
            zf.writestr("config.ini", "setting=true")
        zip_bytes = zip_buffer.getvalue()
        zip_status, zip_attrs, _, _, _ = MetadataExtractionService.extract("evidence_bundle.zip", zip_bytes)
        assert zip_status == "EXTRACTED"
        assert zip_attrs["entry_count"] == 2
        print(f"[PASS] 16e. Metadata ZIP: entry_count={zip_attrs['entry_count']}, uncompressed={zip_attrs['uncompressed_bytes']} bytes")

        # Corrupt file handling
        bad_status, bad_attrs, _, _, bad_err = MetadataExtractionService.extract("broken.zip", b"THIS_IS_NOT_A_VALID_ZIP_FILE")
        assert bad_status == "FAILED"
        assert bad_err is not None
        print(f"[PASS] 16f. Corrupt File Handling: Status gracefully marked {bad_status} without crashing")

        # Step 17: Upload Evidence via API & Attach Metadata to Case
        upload_res = client.post(
            f"/api/cases/{case1_id}/extract-metadata",
            files={"file": ("network_capture_summary.csv", csv_bytes, "text/csv")},
            data={"description": "Egress firewall traffic logs", "tags": "TRAFFIC,FIREWALL"},
            headers=admin_headers
        )
        assert upload_res.status_code == 200
        extracted_doc = upload_res.json()
        assert extracted_doc["original_filename"] == "network_capture_summary.csv"
        assert extracted_doc["metadata_status"] == "EXTRACTED"
        assert extracted_doc["case_id"] == case1_id
        print(f"[PASS] 17. Evidence Ingestion API: Successfully attached metadata record to Case {case1_num}")

        # Step 18: Regression Testing (Auth, WebSocket, Hardware)
        print("\n--- Regression Testing Foundation Services ---")
        # Me profile
        me = client.get("/api/auth/me", headers=admin_headers).json()
        assert me["email"] == "admin@forensics.gov"
        print("[PASS] 18a. Regression: /auth/me profile intact")

        # Hardware simulation
        hw_sim = client.post("/api/hardware/authenticate", json={
            "deviceId": "ESP32_01",
            "rfid": "04A1B2C3",
            "timestamp": "2026-09-03T11:00:00Z"
        })
        assert hw_sim.status_code == 200
        print("[PASS] 18b. Regression: ESP32 Hardware RFID simulation intact")

        # WebSocket
        with client.websocket_connect("/api/ws/hardware") as ws:
            ws.send_text("test_ping")
            pong = ws.receive_json()
            assert pong["type"] == "pong"
        print("[PASS] 18c. Regression: WebSocket ping/pong intact")

    print("\n==================================================================")
    print("ALL PHASE 1 (MILESTONE 2) TESTS PASSED WITH ZERO FAILURES!")
    print("==================================================================")

if __name__ == "__main__":
    run_milestone2_tests()
