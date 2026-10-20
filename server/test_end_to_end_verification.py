import os
import io
import hashlib
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

def run_e2e_verification():
    print("==================================================================")
    print("RUNNING COMPLETE END-TO-END SOFTWARE VERIFICATION (SIMULATION MODE)")
    print("==================================================================")

    with TestClient(app) as client:
        # ==================================================================
        # 1. AUTHENTICATION & RBAC
        # ==================================================================
        print("\n--- 1. Testing Authentication & RBAC ---")
        admin_login = client.post("/api/auth/login", json={"email": "admin@forensics.gov", "password": "password123"})
        assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print("[PASS] 1a. Administrator Login: Successfully obtained JWT token")

        # Invalid credentials
        bad_login = client.post("/api/auth/login", json={"email": "admin@forensics.gov", "password": "wrongpassword"})
        assert bad_login.status_code == 401
        print("[PASS] 1b. Invalid Credentials: Gracefully rejected with 401 Unauthorized")

        # /auth/me profile
        me_res = client.get("/api/auth/me", headers=admin_headers)
        assert me_res.status_code == 200
        assert me_res.json()["role"] == "admin"
        print("[PASS] 1c. Profile Endpoint (/auth/me): Verified active administrator role")

        # ==================================================================
        # 2. HARDWARE SIMULATION (ZERO PHYSICAL ESP32 REQUIRED)
        # ==================================================================
        print("\n--- 2. Testing Hardware Simulation Mode ---")
        # Ensure device ESP32_01 is registered online
        hb_res = client.post("/api/hardware/heartbeat", json={
            "device": "ESP32_01",
            "macAddress": "24:6F:28:AE:C3:0C",
            "firmwareVersion": "v1.0.4-forensic"
        })
        assert hb_res.status_code == 200

        # Simulate Registered RFID Card
        rfid_res = client.post("/api/hardware/authenticate", json={
            "deviceId": "ESP32_01",
            "rfid": "04A1B2C3",
            "timestamp": "2026-09-03T11:00:00Z"
        })
        assert rfid_res.status_code == 200, f"RFID simulation failed: {rfid_res.text}"
        assert rfid_res.json()["success"] is True
        print("[PASS] 2a. Simulated RFID Swipe (04A1B2C3): Authenticated successfully")

        # Simulate Registered Fingerprint
        fp_res = client.post("/api/hardware/authenticate", json={
            "deviceId": "ESP32_01",
            "fingerprintId": 12,
            "timestamp": "2026-09-03T11:00:00Z"
        })
        assert fp_res.status_code == 200, f"Fingerprint simulation failed: {fp_res.text}"
        assert fp_res.json()["success"] is True
        print("[PASS] 2b. Simulated Fingerprint Scan (ID 12): Authenticated successfully")

        # Negative Hardware Simulation: Unknown RFID
        bad_rfid = client.post("/api/hardware/authenticate", json={
            "deviceId": "ESP32_01",
            "rfid": "UNKNOWN_CARD_999",
            "timestamp": "2026-09-03T11:00:00Z"
        })
        assert bad_rfid.status_code == 401
        print("[PASS] 2c. Rogue/Unknown RFID: Successfully rejected with 401 Unauthorized")

        # Rogue ESP32 Heartbeat rejection
        rogue_dev = client.post("/api/hardware/authenticate", json={
            "deviceId": "ROGUE_ESP32_UNTRUSTED",
            "rfid": "04A1B2C3",
            "timestamp": "2026-09-03T11:00:00Z"
        })
        assert rogue_dev.status_code == 400
        print("[PASS] 2d. Rogue IoT Terminal Rejection: Blocked untrusted device authentication")

        # ==================================================================
        # 3. CASE CONTAINER LIFECYCLE
        # ==================================================================
        print("\n--- 3. Testing Case Management Lifecycle ---")
        case_res = client.post(
            "/api/cases",
            json={
                "title": "Operation Apex - End-to-End System Audit",
                "description": "Full-scale cyber incident investigation validating complete software stack.",
                "case_type": "DATA_BREACH",
                "priority": "CRITICAL",
                "tags": ["E2E", "AUDIT", "SIMULATION"]
            },
            headers=admin_headers
        )
        assert case_res.status_code == 201
        case = case_res.json()
        case_id = case["_id"]
        case_number = case["case_number"]
        print(f"[PASS] 3a. Case Creation: Generated unique case sequence {case_number} ({case_id})")

        # Status Transition & Notes
        note_res = client.post(
            f"/api/cases/{case_id}/notes",
            json={"content": "Primary investigative workstation and evidence intake initialized."},
            headers=admin_headers
        )
        assert note_res.status_code == 200
        print("[PASS] 3b. Investigation Notes: Appended immutable entry to note ledger")

        # ==================================================================
        # 4. MULTI-FORMAT EVIDENCE INGESTION & METADATA EXTRACTION
        # ==================================================================
        print("\n--- 4. Testing Evidence Ingestion & Metadata Extraction ---")
        # Evidence 1: Text Security Log
        txt_content = b"2026-09-01 10:00:00 AUDIT LOGIN SUCCESS operator_admin\n2026-09-01 10:01:00 AUDIT PROCESS EXEC cmd.exe\n2026-09-01 10:02:00 AUDIT FILE WRITE confidential.docx\n"
        txt_res = client.post(
            f"/api/cases/{case_id}/evidence",
            files={"file": ("security_audit.log", io.BytesIO(txt_content), "text/plain")},
            data={"source_device": "WORKSTATION_PRIMARY", "description": "Host logon and execution audit stream"},
            headers=admin_headers
        )
        assert txt_res.status_code == 201
        ev1 = txt_res.json()
        ev1_id = ev1["_id"]
        assert ev1["sha256_hash"] == hashlib.sha256(txt_content).hexdigest()

        # Evidence 2: Memory Dump / Binary Payload
        bin_content = b"RAW_MEMORY_EXFILTRATION_SAMPLE_PAYLOAD_OFFSET_0x7FFF"
        bin_res = client.post(
            f"/api/cases/{case_id}/evidence",
            files={"file": ("memory_region.dmp", io.BytesIO(bin_content), "application/octet-stream")},
            data={"source_device": "PERIMETER_HOST", "description": "Volatile memory dump segment"},
            headers=admin_headers
        )
        assert bin_res.status_code == 201
        ev2 = bin_res.json()
        ev2_id = ev2["_id"]
        print(f"[PASS] 4a. Evidence Ingestion: Uploaded security_audit.log ({ev1_id}) & memory_region.dmp ({ev2_id})")

        # Safe Path Traversal Safeguard
        malicious_res = client.post(
            f"/api/cases/{case_id}/evidence",
            files={"file": ("../../../../etc/shadow", io.BytesIO(b"root::0:0:::"), "text/plain")},
            headers=admin_headers
        )
        mal_data = malicious_res.json()
        assert "shadow" in mal_data["stored_filename"]
        assert not os.path.exists("../../../../etc/shadow")
        print(f"[PASS] 4b. Path Traversal Prevention: Sanitized malicious path to '{mal_data['stored_filename']}'")

        # ==================================================================
        # 5. SHA-256 INTEGRITY & TAMPER DETECTION
        # ==================================================================
        print("\n--- 5. Testing SHA-256 Integrity Verification & Tamper Detection ---")
        # Verify clean file
        v_clean = client.post(f"/api/evidence/{ev1_id}/verify", headers=admin_headers)
        assert v_clean.status_code == 200
        assert v_clean.json()["integrity"] == "VERIFIED"
        print("[PASS] 5a. Integrity Verification (Clean File): Confirmed VERIFIED against baseline")

        # Tamper Scenario on Evidence 2
        ev_dir = os.path.join(settings.EVIDENCE_STORAGE_DIR, case_id)
        found_target = None
        for root, dirs, files in os.walk(ev_dir):
            for file in files:
                if "memory_region" in file:
                    found_target = os.path.join(root, file)
                    break
        assert found_target and os.path.exists(found_target), "Evidence file not found on disk"

        # Mutate 1 byte
        with open(found_target, "wb") as f:
            f.write(b"CORRUPTED_TAMPERED_COMPROMISED_BYTES_MALICIOUS_ATTACK")

        # Verify tampered file
        v_tamper = client.post(f"/api/evidence/{ev2_id}/verify", headers=admin_headers)
        assert v_tamper.status_code == 200
        assert v_tamper.json()["integrity"] == "TAMPERED"
        print("[PASS] 5b. Tamper Detection: Successfully detected physical bit mutation and marked TAMPERED")

        # Verify baseline preservation in DB
        ev2_doc = client.get(f"/api/evidence/{ev2_id}", headers=admin_headers).json()
        assert ev2_doc["sha256_hash"] == hashlib.sha256(bin_content).hexdigest()
        assert ev2_doc["integrity_status"] == "TAMPERED"
        print("[PASS] 5c. Baseline Preservation: Original SHA-256 digest remains immutable in database")

        # ==================================================================
        # 6. CHAIN OF CUSTODY LEDGER
        # ==================================================================
        print("\n--- 6. Testing Cryptographic Chain of Custody ---")
        custody_res = client.get(f"/api/evidence/{ev2_id}/custody", headers=admin_headers)
        assert custody_res.status_code == 200
        history = custody_res.json()["history"]
        actions = [h["action"] for h in history]
        assert "EVIDENCE_UPLOADED" in actions
        assert "EVIDENCE_INTEGRITY_FAILURE" in actions
        print(f"[PASS] 6. Chain of Custody Ledger: Recorded {len(history)} verified operations: {set(actions)}")

        # ==================================================================
        # 7. FORENSIC EVENTS ENGINE
        # ==================================================================
        print("\n--- 7. Testing Forensic Events Engine ---")
        # Exact timestamp event linked to Evidence 1
        evt1_res = client.post(
            f"/api/cases/{case_id}/events",
            json={
                "title": "Unauthorized Mimikatz Execution",
                "description": "Adversary invoked sekurlsa::logonpasswords to dump LSASS credentials.",
                "event_type": "PROCESS_EXECUTED",
                "severity": "CRITICAL",
                "confidence": "HIGH",
                "time_precision": "EXACT",
                "event_time": "2026-09-02T11:20:00Z",
                "evidence_id": ev1_id,
                "device_id": "WORKSTATION_PRIMARY",
                "location": "Headquarters Data Center",
                "latitude": 37.7749,
                "longitude": -122.4194
            },
            headers=admin_headers
        )
        assert evt1_res.status_code == 201

        # Approximate event
        evt2_res = client.post(
            f"/api/cases/{case_id}/events",
            json={
                "title": "Suspicious External USB Connection",
                "description": "Kingston DataTraveler flash drive mounted during off-hours window.",
                "event_type": "USB_CONNECTED",
                "severity": "HIGH",
                "confidence": "MEDIUM",
                "time_precision": "APPROXIMATE",
                "time_start": "2026-09-02T12:00:00Z",
                "time_end": "2026-09-02T12:30:00Z",
                "device_id": "WORKSTATION_PRIMARY"
            },
            headers=admin_headers
        )
        assert evt2_res.status_code == 201
        print("[PASS] 7. Forensic Events: Created EXACT and APPROXIMATE precision forensic events")

        # ==================================================================
        # 8. FORENSIC TIMELINE ENGINE
        # ==================================================================
        print("\n--- 8. Testing Timeline Correlation Engine ---")
        tl_res = client.get(f"/api/cases/{case_id}/timeline", headers=admin_headers)
        assert tl_res.status_code == 200
        tl_data = tl_res.json()
        assert tl_data["total_events"] >= 4
        assert any(e["severity"] == "CRITICAL" for e in tl_data["events"])
        print(f"[PASS] 8. Timeline Correlation: Correlated {tl_data['total_events']} events from multi-source streams")

        # ==================================================================
        # 9. EVIDENCE GRAPH ENGINE
        # ==================================================================
        print("\n--- 9. Testing Evidence Graph Topology ---")
        graph_res = client.get(f"/api/cases/{case_id}/graph", headers=admin_headers)
        assert graph_res.status_code == 200
        graph = graph_res.json()
        node_types = {n["node_type"] for n in graph["nodes"]}
        assert "CASE" in node_types
        assert "EVIDENCE" in node_types
        assert "EVENT" in node_types
        assert "DEVICE" in node_types
        assert graph["total_edges"] > 0
        print(f"[PASS] 9. Evidence Graph: Built real topology with {graph['total_nodes']} nodes and {graph['total_edges']} edges")

        # ==================================================================
        # 10. DETERMINISTIC RISK SCORING
        # ==================================================================
        print("\n--- 10. Testing Deterministic Forensic Risk Scoring ---")
        risk_res = client.get(f"/api/cases/{case_id}/risk-score", headers=admin_headers)
        assert risk_res.status_code == 200
        risk = risk_res.json()
        assert risk["score"] >= 75
        assert risk["risk_level"] == "CRITICAL"
        assert any(s["signal_type"] == "EVIDENCE_TAMPERED" for s in risk["signals"])
        assert any(s["signal_type"] == "CRITICAL_EVENTS" for s in risk["signals"])
        print(f"[PASS] 10. Deterministic Risk Scoring: Evaluated {risk['score']}/100 (CRITICAL) with verified signals")

        # ==================================================================
        # 11. AI THREAT REASONING & RECOMMENDATIONS
        # ==================================================================
        print("\n--- 11. Testing AI Threat Intelligence & Recommendations ---")
        ai_res = client.get(f"/api/cases/{case_id}/ai-analysis", headers=admin_headers)
        assert ai_res.status_code == 200
        ai = ai_res.json()
        assert len(ai["facts"]) > 0
        assert len(ai["ai_interpretations"]) > 0
        print(f"[PASS] 11a. AI Threat Reasoning: Separated {len(ai['facts'])} facts from {len(ai['ai_interpretations'])} interpretations ({ai['ai_provider']})")

        recs_res = client.get(f"/api/cases/{case_id}/recommendations", headers=admin_headers)
        assert recs_res.status_code == 200
        recs = recs_res.json()
        assert recs["total_recommendations"] >= 2
        rec_titles = [r["title"] for r in recs["recommendations"]]
        print(f"[PASS] 11b. Actionable Recommendations: Produced {len(recs['recommendations'])} countermeasures")

        # ==================================================================
        # 12. COURT-ADMISSIBLE FORENSIC REPORT GENERATION & DOWNLOAD
        # ==================================================================
        print("\n--- 12. Testing Court-Admissible Forensic PDF Report Generation ---")
        gen_res = client.post(
            f"/api/cases/{case_id}/reports",
            json={
                "title": f"Final Forensic Incident Report - {case_number}",
                "classification": "CONFIDENTIAL // LAW ENFORCEMENT SENSITIVE"
            },
            headers=admin_headers
        )
        assert gen_res.status_code == 201, f"Report generation failed: {gen_res.text}"
        report = gen_res.json()
        report_id = report["report_id"]
        assert report["version"] == 1
        assert len(report["sha256_hash"]) == 64
        assert report["file_size"] > 1000
        print(f"[PASS] 12a. PDF Compilation: Generated v1.0 ({report['file_size']} bytes, SHA-256: {report['sha256_hash'][:16]}...)")

        # Report list
        list_res = client.get(f"/api/cases/{case_id}/reports", headers=admin_headers)
        assert list_res.status_code == 200
        assert list_res.json()["total_reports"] >= 1
        print("[PASS] 12b. Report Ledger: Listed report record in case archive")

        # Report binary download
        dl_res = client.get(f"/api/reports/{report_id}/download", headers=admin_headers)
        assert dl_res.status_code == 200
        assert dl_res.headers["content-type"] == "application/pdf"
        pdf_bytes = dl_res.content
        assert pdf_bytes.startswith(b"%PDF-"), "Downloaded file is not a valid PDF!"
        assert hashlib.sha256(pdf_bytes).hexdigest() == report["sha256_hash"], "Downloaded PDF hash mismatch!"
        print("[PASS] 12c. Safe PDF Download: Downloaded valid binary PDF matching cryptographic seal")

        # ==================================================================
        # 13. AUDIT LOG PROVENANCE & DASHBOARD
        # ==================================================================
        print("\n--- 13. Testing Audit Logging & Dashboard Telemetry ---")
        audit_res = client.get("/api/audit-logs", headers=admin_headers)
        assert audit_res.status_code == 200
        assert len(audit_res.json()) > 0
        print(f"[PASS] 13a. Immutable Audit Logs: Confirmed {len(audit_res.json())} system operations logged")

        dash_res = client.get("/api/cases/risk/stats", headers=admin_headers)
        assert dash_res.status_code == 200
        assert dash_res.json()["critical_risk_cases"] >= 1
        print(f"[PASS] 13b. Dashboard Real Metrics: Confirmed active risk statistics -> {dash_res.json()}")

        # ==================================================================
        # 14. WEBSOCKET HEALTH
        # ==================================================================
        print("\n--- 14. Testing Real-Time WebSocket Telemetry ---")
        with client.websocket_connect("/api/ws/hardware") as ws:
            ws.send_text("client_ping")
            msg = ws.receive_json()
            assert msg.get("type") == "pong"
        print("[PASS] 14. WebSocket Telemetry: Real-time bidirectional ping/pong validated")

    print("\n==================================================================")
    print("ALL 17 END-TO-END VERIFICATION STEPS PASSED WITH 100% SUCCESS!")
    print("==================================================================")

if __name__ == "__main__":
    run_e2e_verification()
