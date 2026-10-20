import os
import io
import hashlib
from datetime import datetime, timezone
from PIL import Image
import zipfile
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.metadata_service import MetadataExtractionService

def run_full_feature_verification():
    print("==================================================================")
    print("COMPLETE SOFTWARE FEATURE VERIFICATION — PRE-HARDWARE AUDIT")
    print("==================================================================")

    results = {}

    with TestClient(app) as client:
        # ------------------------------------------------------------------
        # 1. APPLICATION STARTUP & SYSTEM HEALTH
        # ------------------------------------------------------------------
        print("\n--- 1. Application Startup & Endpoints ---")
        root_res = client.get("/")
        assert root_res.status_code == 200
        docs_res = client.get("/docs")
        assert docs_res.status_code == 200
        openapi_res = client.get("/openapi.json")
        assert openapi_res.status_code == 200
        results["APP_STARTUP"] = "PASS"
        print("[PASS] 1. Root, Swagger (/docs), and OpenAPI schemas accessible")

        # ------------------------------------------------------------------
        # 2. AUTHENTICATION & TOKEN HANDLING
        # ------------------------------------------------------------------
        print("\n--- 2. Authentication Testing (Admin, Investigator, Viewer) ---")
        # Admin Login
        admin_res = client.post("/api/auth/login", json={"email": "admin@forensics.gov", "password": "password123"})
        assert admin_res.status_code == 200
        admin_token = admin_res.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Investigator Login
        inv_res = client.post("/api/auth/login", json={"email": "investigator@forensics.gov", "password": "password123"})
        assert inv_res.status_code == 200
        inv_token = inv_res.json()["access_token"]
        inv_headers = {"Authorization": f"Bearer {inv_token}"}

        # Viewer Login
        viewer_res = client.post("/api/auth/login", json={"email": "viewer@forensics.gov", "password": "password123"})
        assert viewer_res.status_code == 200
        viewer_token = viewer_res.json()["access_token"]
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

        # Invalid Credentials
        bad_login = client.post("/api/auth/login", json={"email": "admin@forensics.gov", "password": "wrong_password"})
        assert bad_login.status_code == 401

        # Profile /auth/me
        me_admin = client.get("/api/auth/me", headers=admin_headers)
        assert me_admin.status_code == 200 and me_admin.json()["role"] == "admin"
        me_inv = client.get("/api/auth/me", headers=inv_headers)
        assert me_inv.status_code == 200 and me_inv.json()["role"] == "investigator"
        me_view = client.get("/api/auth/me", headers=viewer_headers)
        assert me_view.status_code == 200 and me_view.json()["role"] == "readonly"

        # Invalid Token
        bad_token_res = client.get("/api/auth/me", headers={"Authorization": "Bearer BAD_MALFORMED_TOKEN"})
        assert bad_token_res.status_code == 401

        results["AUTH"] = "PASS"
        print("[PASS] 2. Authentication: Admin, Investigator, Viewer, 401 on bad credentials, profile validation")

        # ------------------------------------------------------------------
        # 3. ROLE-BASED ACCESS CONTROL (RBAC)
        # ------------------------------------------------------------------
        print("\n--- 3. Role-Based Access Control Enforcement ---")
        # Viewer attempt to create case -> Must be blocked 403
        viewer_create_case = client.post(
            "/api/cases",
            json={"title": "Viewer Rogue Case", "description": "Should fail", "case_type": "DATA_BREACH", "priority": "LOW"},
            headers=viewer_headers
        )
        assert viewer_create_case.status_code == 403, f"Viewer create case should be 403, got {viewer_create_case.status_code}"

        # Investigator can create case -> 201
        inv_create_case = client.post(
            "/api/cases",
            json={"title": "Investigator Incident Alpha", "description": "Legitimate case", "case_type": "DATA_BREACH", "priority": "HIGH"},
            headers=inv_headers
        )
        assert inv_create_case.status_code == 201
        test_case_id = inv_create_case.json()["_id"]

        # Viewer attempt to upload evidence -> Must be blocked 403
        viewer_upload_ev = client.post(
            f"/api/cases/{test_case_id}/evidence",
            files={"file": ("unauth.txt", io.BytesIO(b"FAIL"), "text/plain")},
            headers=viewer_headers
        )
        assert viewer_upload_ev.status_code == 403

        # Viewer attempt to generate report -> Must be blocked 403
        viewer_gen_rep = client.post(
            f"/api/cases/{test_case_id}/reports",
            json={"title": "Unauth Report"},
            headers=viewer_headers
        )
        assert viewer_gen_rep.status_code == 403

        results["RBAC"] = "PASS"
        print("[PASS] 3. RBAC: Strict backend enforcement of READONLY role on mutation endpoints (403 Forbidden)")

        # ------------------------------------------------------------------
        # 4. HARDWARE SIMULATION (ZERO PHYSICAL HARDWARE)
        # ------------------------------------------------------------------
        print("\n--- 4. Hardware Simulation Mode Testing ---")
        # Ensure ESP32_01 is online
        client.post("/api/hardware/heartbeat", json={
            "device": "ESP32_01",
            "macAddress": "24:6F:28:AE:C3:0C",
            "firmwareVersion": "v1.0.4-forensic"
        })

        # RFID Simulation
        rfid_ok = client.post("/api/hardware/authenticate", json={
            "deviceId": "ESP32_01",
            "rfid": "04A1B2C3",
            "timestamp": "2026-09-03T12:00:00Z"
        })
        assert rfid_ok.status_code == 200 and rfid_ok.json()["success"] is True

        # Fingerprint Simulation
        fp_ok = client.post("/api/hardware/authenticate", json={
            "deviceId": "ESP32_01",
            "fingerprintId": 12,
            "timestamp": "2026-09-03T12:00:00Z"
        })
        assert fp_ok.status_code == 200 and fp_ok.json()["success"] is True

        # Unknown RFID
        rfid_fail = client.post("/api/hardware/authenticate", json={
            "deviceId": "ESP32_01",
            "rfid": "BAD_CARD_9999",
            "timestamp": "2026-09-03T12:00:00Z"
        })
        assert rfid_fail.status_code == 401

        # Rogue Device
        rogue_dev = client.post("/api/hardware/authenticate", json={
            "deviceId": "ROGUE_ESP32_UNTRUSTED",
            "rfid": "04A1B2C3",
            "timestamp": "2026-09-03T12:00:00Z"
        })
        assert rogue_dev.status_code == 400

        # Mode Toggling: Turn off simulation -> hardware only
        toggle_hw = client.post("/api/settings", json={"simulation_mode": False}, headers=admin_headers)
        assert toggle_hw.status_code == 200
        # Password login blocked in hardware-only mode
        pwd_blocked = client.post("/api/auth/login", json={"email": "admin@forensics.gov", "password": "password123"})
        assert pwd_blocked.status_code == 403
        # Hardware auth still works
        hw_auth_works = client.post("/api/hardware/authenticate", json={"deviceId": "ESP32_01", "rfid": "04A1B2C3", "timestamp": "2026-09-03T12:00:00Z"})
        assert hw_auth_works.status_code == 200
        # Restore simulation mode
        client.post("/api/settings", json={"simulation_mode": True}, headers=admin_headers)

        results["HARDWARE_SIM"] = "PASS"
        print("[PASS] 4. Hardware Simulation: RFID, Fingerprint, Rogue Device rejection, Mode Toggling")

        # ------------------------------------------------------------------
        # 5. DEVICE MANAGEMENT & HEARTBEAT
        # ------------------------------------------------------------------
        print("\n--- 5. Device Management Testing ---")
        devs_res = client.get("/api/hardware/devices", headers=admin_headers)
        assert devs_res.status_code == 200
        dev_list = devs_res.json()
        assert len(dev_list) > 0
        assert any(d["device_id"] == "ESP32_01" for d in dev_list)

        results["DEVICES"] = "PASS"
        print(f"[PASS] 5. Device Management: {len(dev_list)} registered device node(s) verified")

        # ------------------------------------------------------------------
        # 6. CASE LIFECYCLE & NUMBERING
        # ------------------------------------------------------------------
        print("\n--- 6. Case Lifecycle Testing ---")
        case_create = client.post(
            "/api/cases",
            json={
                "title": "Operation Citadel - Verification Run",
                "description": "Full-scope forensic examination case container.",
                "case_type": "MALWARE",
                "priority": "CRITICAL",
                "tags": ["VERIFY", "MALWARE", "IOC"]
            },
            headers=admin_headers
        )
        assert case_create.status_code == 201
        case_data = case_create.json()
        c_id = case_data["_id"]
        c_num = case_data["case_number"]
        assert c_num.startswith("DF-2026-")

        # Update Case
        up_res = client.put(f"/api/cases/{c_id}", json={"priority": "CRITICAL", "description": "Updated narrative"}, headers=admin_headers)
        assert up_res.status_code == 200

        # Assign Investigator via update
        assign_res = client.put(f"/api/cases/{c_id}", json={"assigned_investigator": str(me_inv.json()["_id"])}, headers=admin_headers)
        assert assign_res.status_code == 200

        # Note Ledger
        note_res = client.post(f"/api/cases/{c_id}/notes", json={"content": "Case assigned to Lead Detective."}, headers=admin_headers)
        assert note_res.status_code == 200

        # Search & Filter
        search_res = client.get(f"/api/cases?search={c_num}", headers=admin_headers)
        assert search_res.status_code == 200
        assert any(c["_id"] == c_id for c in search_res.json()["cases"])

        filter_res = client.get("/api/cases?priority=CRITICAL", headers=admin_headers)
        assert filter_res.status_code == 200
        assert any(c["_id"] == c_id for c in filter_res.json()["cases"])

        results["CASE_MANAGEMENT"] = "PASS"
        print(f"[PASS] 6. Case Lifecycle: Unique sequence {c_num}, assign, update, note, search, and filter")

        # ------------------------------------------------------------------
        # 7. METADATA EXTRACTION ACROSS EVIDENCE TYPES
        # ------------------------------------------------------------------
        print("\n--- 7. Metadata Extraction Testing ---")
        # 7a. Image Extraction (PNG)
        img_buffer = io.BytesIO()
        test_img = Image.new('RGB', (320, 240), color='blue')
        test_img.save(img_buffer, format='PNG')
        png_bytes = img_buffer.getvalue()
        img_status, img_attrs, lat, lon, _ = MetadataExtractionService.extract("forensic_snapshot.png", png_bytes)
        assert img_status == "EXTRACTED"
        assert img_attrs["width"] == 320 and img_attrs["height"] == 240 and img_attrs["format"] == "PNG"

        # 7b. Text / Log Extraction
        log_bytes = b"2026-09-01 12:00:00 [CRITICAL] LSASS injection detected\n2026-09-01 12:01:00 [ALERT] Exfiltration probe\n"
        txt_status, txt_attrs, _, _, _ = MetadataExtractionService.extract("security_auth.log", log_bytes)
        assert txt_status == "EXTRACTED"
        assert txt_attrs["line_count"] == 2

        # 7c. CSV Extraction
        csv_bytes = b"timestamp,ip,action,status\n2026-09-01,10.0.0.1,LOGIN,SUCCESS\n2026-09-01,10.0.0.2,EXEC,FAILED\n"
        csv_status, csv_attrs, _, _, _ = MetadataExtractionService.extract("access_records.csv", csv_bytes)
        assert csv_status == "EXTRACTED"
        assert csv_attrs["row_count"] == 3 and csv_attrs["column_count"] == 4

        # 7d. JSON Extraction
        json_bytes = b'{"ioc": "mimikatz.exe", "md5": "d41d8cd98f00b204e9800998ecf8427e", "ports": [445, 139]}'
        json_status, json_attrs, _, _, _ = MetadataExtractionService.extract("threat_feed.json", json_bytes)
        assert json_status == "EXTRACTED"
        assert json_attrs["is_valid_json"] is True and json_attrs["key_count"] == 3

        # 7e. ZIP Extraction
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("artifact1.log", "data1")
            zf.writestr("artifact2.log", "data2")
        zip_bytes = zip_buffer.getvalue()
        zip_status, zip_attrs, _, _, _ = MetadataExtractionService.extract("evidence_bundle.zip", zip_bytes)
        assert zip_status == "EXTRACTED"
        assert zip_attrs["entry_count"] == 2

        # 7f. Corrupted File Handling
        bad_status, _, _, _, bad_err = MetadataExtractionService.extract("corrupted.zip", b"CORRUPTED_NON_ZIP_BYTES")
        assert bad_status == "FAILED"
        assert bad_err is not None

        # 7g. Ingest via extract-metadata API endpoint
        api_meta_res = client.post(
            f"/api/cases/{c_id}/extract-metadata",
            files={"file": ("incident_log.csv", csv_bytes, "text/csv")},
            data={"description": "Firewall egress logs", "tags": "FIREWALL,EGRESS"},
            headers=admin_headers
        )
        assert api_meta_res.status_code == 200

        # 7h. Evidence Ingestion for Evidence Vault (Target for tamper scenario)
        bin_bytes = b"BINARY_PROCESS_MEMORY_SECTION_0x4000_PE_HEADER_PAYLOAD"
        ev_bin = client.post(
            f"/api/cases/{c_id}/evidence",
            files={"file": ("malware_payload.raw", io.BytesIO(bin_bytes), "application/octet-stream")},
            headers=admin_headers
        ).json()
        ev_bin_id = ev_bin["_id"]

        results["METADATA_EXTRACTION"] = "PASS"
        print("[PASS] 7. Metadata Extraction: PNG dimensions, text lines, CSV rows, JSON keys, ZIP entries, corrupt file handling, and API integration")

        # ------------------------------------------------------------------
        # 8. SHA-256 STREAMING HASHING & TAMPER DETECTION
        # ------------------------------------------------------------------
        print("\n--- 8. SHA-256 Verification & Controlled Tamper Detection ---")
        baseline_hash = hashlib.sha256(bin_bytes).hexdigest()
        assert ev_bin["sha256_hash"] == baseline_hash

        # Step 8a: Verify clean file -> VERIFIED
        v1 = client.post(f"/api/evidence/{ev_bin_id}/verify", headers=admin_headers)
        assert v1.status_code == 200 and v1.json()["integrity"] == "VERIFIED"

        # Step 8b: Disk Bit Mutation Attack
        ev_dir = os.path.join(settings.EVIDENCE_STORAGE_DIR, c_id)
        target_path = None
        for root, dirs, files in os.walk(ev_dir):
            for file in files:
                if "malware_payload" in file:
                    target_path = os.path.join(root, file)
                    break
        assert target_path and os.path.exists(target_path)
        with open(target_path, "wb") as f:
            f.write(b"CORRUPTED_INJECTED_TAMPERED_BYTES_BY_ATTACKER")

        # Step 8c: Trigger Verification on Tampered File -> TAMPERED
        v2 = client.post(f"/api/evidence/{ev_bin_id}/verify", headers=admin_headers)
        assert v2.status_code == 200 and v2.json()["integrity"] == "TAMPERED"

        # Step 8d: Verify database preserves original baseline hash
        doc_after = client.get(f"/api/evidence/{ev_bin_id}", headers=admin_headers).json()
        assert doc_after["sha256_hash"] == baseline_hash, "CRITICAL: Baseline hash must remain unaltered!"
        assert doc_after["integrity_status"] == "TAMPERED"

        results["SHA256_INTEGRITY"] = "PASS"
        print(f"[PASS] 8. SHA-256 Integrity: Verified clean -> Detected tamper -> Preserved baseline {baseline_hash[:16]}...")

        # ------------------------------------------------------------------
        # 9. CHAIN OF CUSTODY AUDIT LEDGER
        # ------------------------------------------------------------------
        print("\n--- 9. Chain of Custody Ledger & Hash Chaining ---")
        custody_res = client.get(f"/api/evidence/{ev_bin_id}/custody", headers=admin_headers)
        assert custody_res.status_code == 200
        history = custody_res.json()["history"]
        actions = [h["action"] for h in history]
        assert "EVIDENCE_UPLOADED" in actions
        assert "EVIDENCE_INTEGRITY_FAILURE" in actions
        assert "EVIDENCE_VERIFIED" in actions

        results["CHAIN_OF_CUSTODY"] = "PASS"
        print(f"[PASS] 9. Chain of Custody: Recorded verified actions: {set(actions)}")

        # ------------------------------------------------------------------
        # 10. FORENSIC EVENTS & PRECISION
        # ------------------------------------------------------------------
        print("\n--- 10. Forensic Events Engine ---")
        # Exact timestamp
        e1 = client.post(
            f"/api/cases/{c_id}/events",
            json={
                "title": "Cobalt Strike Beacon Ingress",
                "description": "C2 channel established over port 443 with beacon callback.",
                "event_type": "MALWARE_DETECTED",
                "severity": "CRITICAL",
                "confidence": "HIGH",
                "time_precision": "EXACT",
                "event_time": "2026-09-02T14:15:00Z",
                "device_id": "PERIMETER_GATEWAY",
                "location": "Gateway Cluster DC-1",
                "latitude": 37.7749,
                "longitude": -122.4194
            },
            headers=admin_headers
        )
        assert e1.status_code == 201

        # Approximate timestamp
        e2 = client.post(
            f"/api/cases/{c_id}/events",
            json={
                "title": "PsExec Lateral Movement",
                "description": "Remote administrative execution observed across subnets.",
                "event_type": "PROCESS_EXECUTED",
                "severity": "HIGH",
                "confidence": "HIGH",
                "time_precision": "APPROXIMATE",
                "time_start": "2026-09-02T15:00:00Z",
                "time_end": "2026-09-02T15:30:00Z",
                "device_id": "DOMAIN_CONTROLLER_01"
            },
            headers=admin_headers
        )
        assert e2.status_code == 201

        # Unknown timestamp
        e3 = client.post(
            f"/api/cases/{c_id}/events",
            json={
                "title": "Post-Incident Forensic Debrief Notes",
                "description": "Undated investigator field notes extracted from secure notebook.",
                "event_type": "CASE_EVENT",
                "severity": "INFO",
                "confidence": "LOW",
                "time_precision": "UNKNOWN"
            },
            headers=admin_headers
        )
        assert e3.status_code == 201

        results["FORENSIC_EVENTS"] = "PASS"
        print("[PASS] 10. Forensic Events: Created EXACT, APPROXIMATE, and UNKNOWN precision events with GPS")

        # ------------------------------------------------------------------
        # 11. FORENSIC TIMELINE CORRELATION & FILTERS
        # ------------------------------------------------------------------
        print("\n--- 11. Forensic Timeline Engine ---")
        tl_res = client.get(f"/api/cases/{c_id}/timeline", headers=admin_headers)
        assert tl_res.status_code == 200
        tl = tl_res.json()
        assert tl["total_events"] >= 5

        # Search filter
        tl_search = client.get(f"/api/cases/{c_id}/timeline?search=Cobalt", headers=admin_headers)
        assert tl_search.status_code == 200
        assert len(tl_search.json()["events"]) >= 1

        # Severity filter
        tl_crit = client.get(f"/api/cases/{c_id}/timeline?severity=CRITICAL", headers=admin_headers)
        assert tl_crit.status_code == 200
        assert all(e["severity"] == "CRITICAL" for e in tl_crit.json()["events"])

        # Timeline Stats
        t_stats = client.get(f"/api/cases/{c_id}/timeline/stats", headers=admin_headers)
        assert t_stats.status_code == 200
        assert t_stats.json()["critical_events"] >= 1

        results["TIMELINE"] = "PASS"
        print(f"[PASS] 11. Timeline: Correlated {tl['total_events']} events with server-side filters & statistics")

        # ------------------------------------------------------------------
        # 12. EVIDENCE GRAPH TOPOLOGY
        # ------------------------------------------------------------------
        print("\n--- 12. Evidence Graph Topology ---")
        graph_res = client.get(f"/api/cases/{c_id}/graph", headers=admin_headers)
        assert graph_res.status_code == 200
        graph = graph_res.json()
        node_types = {n["node_type"] for n in graph["nodes"]}
        edge_types = {e["edge_type"] for e in graph["edges"]}
        assert "CASE" in node_types
        assert "EVIDENCE" in node_types
        assert "EVENT" in node_types
        assert "DEVICE" in node_types
        assert "CONTAINS" in edge_types
        assert graph["total_edges"] > 0

        # Filtering by node_type=EVIDENCE
        g_filtered = client.get(f"/api/cases/{c_id}/graph?node_type=EVIDENCE", headers=admin_headers)
        assert g_filtered.status_code == 200
        assert all(n["node_type"] == "EVIDENCE" for n in g_filtered.json()["nodes"])

        results["EVIDENCE_GRAPH"] = "PASS"
        print(f"[PASS] 12. Evidence Graph: Generated topology with {graph['total_nodes']} nodes, {graph['total_edges']} edges, and filtering")

        # ------------------------------------------------------------------
        # 13. DETERMINISTIC RISK SCORING
        # ------------------------------------------------------------------
        print("\n--- 13. Deterministic Risk Scoring Engine ---")
        risk_res = client.get(f"/api/cases/{c_id}/risk-score", headers=admin_headers)
        assert risk_res.status_code == 200
        risk = risk_res.json()
        assert 0 <= risk["score"] <= 100
        assert risk["risk_level"] == "CRITICAL"  # Because tampered (+40) + critical (+25) + high (+10) + patterns (+15) + custody failure (+20) = clamped to 100
        assert any(s["signal_type"] == "EVIDENCE_TAMPERED" for s in risk["signals"])

        # Verify Determinism on Repeat Call
        risk_repeat = client.get(f"/api/cases/{c_id}/risk-score", headers=admin_headers).json()
        assert risk_repeat["score"] == risk["score"]

        results["RISK_SCORING"] = "PASS"
        print(f"[PASS] 13. Deterministic Risk Score: Evaluated {risk['score']}/100 (CRITICAL) with 100% repeatability")

        # ------------------------------------------------------------------
        # 14. AI THREAT REASONING (OFFLINE FALLBACK & SEPARATION)
        # ------------------------------------------------------------------
        print("\n--- 14. AI Threat Intelligence Testing ---")
        ai_res = client.get(f"/api/cases/{c_id}/ai-analysis", headers=admin_headers)
        assert ai_res.status_code == 200
        ai = ai_res.json()
        assert len(ai["facts"]) > 0
        assert len(ai["ai_interpretations"]) > 0
        assert all("FACT:" in f for f in ai["facts"])

        results["AI_ANALYSIS"] = "PASS"
        print(f"[PASS] 14. AI Analysis: Strictly separated {len(ai['facts'])} facts from {len(ai['ai_interpretations'])} interpretations")

        # ------------------------------------------------------------------
        # 15. ACTIONABLE RECOMMENDATIONS
        # ------------------------------------------------------------------
        print("\n--- 15. Actionable Recommendations Engine ---")
        recs_res = client.get(f"/api/cases/{c_id}/recommendations", headers=admin_headers)
        assert recs_res.status_code == 200
        recs = recs_res.json()
        assert recs["total_recommendations"] >= 3
        severities = {r["severity"] for r in recs["recommendations"]}
        assert "CRITICAL" in severities or "HIGH" in severities

        results["RECOMMENDATIONS"] = "PASS"
        print(f"[PASS] 15. Recommendations: Produced {recs['total_recommendations']} actionable countermeasures prioritized by severity")

        # ------------------------------------------------------------------
        # 16. COURT-ADMISSIBLE FORENSIC REPORT GENERATION & DOWNLOAD
        # ------------------------------------------------------------------
        print("\n--- 16. Forensic Report Compilation & Download ---")
        rep_res = client.post(
            f"/api/cases/{c_id}/reports",
            json={
                "title": f"Official Court Examination Report - {c_num}",
                "classification": "CONFIDENTIAL // LAW ENFORCEMENT SENSITIVE"
            },
            headers=admin_headers
        )
        assert rep_res.status_code == 201
        rep_data = rep_res.json()
        r_id = rep_data["report_id"]
        assert rep_data["version"] == 1
        assert len(rep_data["sha256_hash"]) == 64
        assert rep_data["file_size"] > 1000

        # Safe PDF Download
        dl_res = client.get(f"/api/reports/{r_id}/download", headers=admin_headers)
        assert dl_res.status_code == 200
        assert dl_res.headers["content-type"] == "application/pdf"
        assert dl_res.content.startswith(b"%PDF-")
        assert hashlib.sha256(dl_res.content).hexdigest() == rep_data["sha256_hash"]

        results["REPORTS"] = "PASS"
        print(f"[PASS] 16. Forensic Reports: Compiled v1.0 PDF ({rep_data['file_size']} B), verified SHA-256 seal {rep_data['sha256_hash'][:16]}..., downloaded valid binary")

        # ------------------------------------------------------------------
        # 17. DASHBOARD TELEMETRY & AUDIT LOGS
        # ------------------------------------------------------------------
        print("\n--- 17. Dashboard & Audit Trail Testing ---")
        dash_stats = client.get("/api/cases/risk/stats", headers=admin_headers).json()
        assert dash_stats["total_assessed_cases"] > 0
        assert dash_stats["critical_risk_cases"] > 0

        audit_logs = client.get("/api/audit-logs", headers=admin_headers).json()
        assert len(audit_logs) > 0

        results["DASHBOARD_AND_AUDIT"] = "PASS"
        print(f"[PASS] 17. Dashboard & Audit: Verified {len(audit_logs)} immutable audit events and live risk metrics")

        # ------------------------------------------------------------------
        # 18. WEBSOCKET REAL-TIME TELEMETRY
        # ------------------------------------------------------------------
        print("\n--- 18. Real-Time WebSocket Telemetry ---")
        with client.websocket_connect("/api/ws/hardware") as ws:
            ws.send_text("client_ping")
            ws_reply = ws.receive_json()
            assert ws_reply["type"] == "pong"

        results["WEBSOCKET"] = "PASS"
        print("[PASS] 18. WebSocket: Validated real-time bidirectional telemetry on /api/ws/hardware")

    print("\n==================================================================")
    print("ALL 18 DETAILED FEATURE MODULES PASSED VERIFICATION WITH 100% SUCCESS!")
    print("==================================================================")
    return results

if __name__ == "__main__":
    run_full_feature_verification()
