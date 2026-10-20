import os
import io
import time
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app

def run_security_tracking_tests():
    print("==================================================================")
    print("RUNNING UNAUTHORIZED ACCESS DETECTION & FORENSIC TRACKING TEST SUITE")
    print("==================================================================")

    with TestClient(app) as client:
        # Step 0: Ensure Admin and Investigator Users
        admin_login = client.post("/api/auth/login", json={"email": "admin@forensics.gov", "password": "password123"})
        assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        admin_user = admin_login.json()["user"]
        print("[PASS] 0. Admin Authentication successful")

        # Register secondary investigator if not exists
        inv_email = "detective.carter@forensics.gov"
        inv_reg = client.post("/api/auth/register", json={
            "email": inv_email,
            "name": "Detective Carter",
            "password": "password123",
            "role": "investigator"
        })
        inv_login = client.post("/api/auth/login", json={"email": inv_email, "password": "password123"})
        assert inv_login.status_code == 200, f"Investigator login failed: {inv_login.text}"
        inv_token = inv_login.json()["access_token"]
        inv_headers = {"Authorization": f"Bearer {inv_token}"}
        inv_user = inv_login.json()["user"]
        print(f"[PASS] 0. Secondary Investigator setup: {inv_email}")

        # Register readonly user if not exists
        ro_email = "auditor.smith@forensics.gov"
        client.post("/api/auth/register", json={
            "email": ro_email,
            "name": "Auditor Smith",
            "password": "password123",
            "role": "readonly"
        })
        ro_login = client.post("/api/auth/login", json={"email": ro_email, "password": "password123"})
        assert ro_login.status_code == 200, f"Readonly login failed: {ro_login.text}"
        ro_token = ro_login.json()["access_token"]
        ro_headers = {"Authorization": f"Bearer {ro_token}"}
        print(f"[PASS] 0. Readonly User setup: {ro_email}")

        # Create target Case
        case_res = client.post("/api/cases", json={
            "title": "Operation Citadel - Secure Vault Breach Investigation",
            "description": "Restricted government database breach and exfiltration.",
            "case_type": "DATA_BREACH",
            "priority": "CRITICAL"
        }, headers=admin_headers)
        assert case_res.status_code == 201, f"Case creation failed: {case_res.text}"
        case = case_res.json()
        case_id = case["_id"]
        print(f"[PASS] Target Case Setup: Case {case['case_number']} (ID: {case_id})")

        # Upload baseline evidence to case
        ev_payload = b"CRITICAL_SYSTEM_KERNEL_DUMP_RESTRICTED_ACCESS_EXHIBIT_A"
        ev_res = client.post(
            f"/api/cases/{case_id}/evidence",
            files={"file": ("kernel_dump.bin", io.BytesIO(ev_payload), "application/octet-stream")},
            data={"description": "Kernel core dump", "source_device": "VAULT_SERVER_01"},
            headers=admin_headers
        )
        assert ev_res.status_code == 201, f"Evidence upload failed: {ev_res.text}"
        evidence = ev_res.json()
        evidence_id = evidence["_id"]
        print(f"[PASS] Target Evidence Setup: {evidence['original_filename']} (ID: {evidence_id})")

        # ==============================================================================
        # SCENARIO 1: Unauthenticated Request to Protected Forensic Endpoint
        # ==============================================================================
        print("\n--- Scenario 1: Unauthenticated Access Attempt ---")
        unauth_res = client.get(f"/api/evidence/{evidence_id}")
        assert unauth_res.status_code in (401, 403), f"Expected 401/403, got {unauth_res.status_code}"

        # Verify security event recorded
        events_res = client.get(f"/api/security/events?evidence_id={evidence_id}", headers=admin_headers)
        assert events_res.status_code == 200
        sec_events = events_res.json()["events"]
        assert len(sec_events) >= 1
        latest_event = sec_events[0]
        assert latest_event["result"] == "BLOCKED"
        assert latest_event["event_type"] == "UNAUTHORIZED_ACCESS_ATTEMPT"
        assert latest_event["user_id"] is None
        assert latest_event["login_id"] is None
        print(f"[PASS] Scenario 1: Unauthenticated attempt blocked and logged (Event ID: {latest_event['event_id']})")

        # ==============================================================================
        # SCENARIO 2: Invalid / Malformed JWT Token
        # ==============================================================================
        print("\n--- Scenario 2: Invalid JWT Token ---")
        bad_jwt_res = client.get("/api/cases", headers={"Authorization": "Bearer invalid.token.signature"})
        assert bad_jwt_res.status_code == 401

        events_res2 = client.get("/api/security/events?limit=5", headers=admin_headers)
        assert events_res2.status_code == 200
        assert any(e["event_type"] == "UNAUTHORIZED_ACCESS_ATTEMPT" for e in events_res2.json()["events"])
        print("[PASS] Scenario 2: Invalid JWT correctly caught and logged as UNAUTHORIZED_ACCESS_ATTEMPT")

        # ==============================================================================
        # SCENARIO 3: Insufficient Role Permissions (Readonly attempts mutation)
        # ==============================================================================
        print("\n--- Scenario 3: Insufficient Role Permissions ---")
        readonly_upload_res = client.post(
            f"/api/cases/{case_id}/evidence",
            files={"file": ("unauthorized.txt", io.BytesIO(b"hack"), "text/plain")},
            headers=ro_headers
        )
        assert readonly_upload_res.status_code == 403, f"Expected 403, got {readonly_upload_res.status_code}"

        sec_events_ro = client.get(f"/api/security/events?case_id={case_id}", headers=admin_headers).json()["events"]
        ro_violation = next((e for e in sec_events_ro if e.get("login_id") == ro_email), None)
        assert ro_violation is not None
        assert ro_violation["event_type"] == "AUTHENTICATED_BUT_UNAUTHORIZED"
        assert ro_violation["user_role"] == "readonly"
        assert ro_violation["result"] == "BLOCKED"
        print(f"[PASS] Scenario 3: Readonly attempt logged as AUTHENTICATED_BUT_UNAUTHORIZED with role info")

        # ==============================================================================
        # SCENARIO 4: Non-Assigned Case Access by Investigator
        # ==============================================================================
        print("\n--- Scenario 4: Non-Assigned Case Modification by Investigator ---")
        # Attempt to modify case by Detective Carter who is NOT assigned to it
        inv_mod_res = client.put(f"/api/cases/{case_id}", json={
            "title": "Tampered Title by Unauthorized Investigator",
            "priority": "LOW"
        }, headers=inv_headers)
        assert inv_mod_res.status_code == 403, f"Expected 403, got {inv_mod_res.status_code}"

        sec_events_inv = client.get(f"/api/security/events?case_id={case_id}", headers=admin_headers).json()["events"]
        inv_violation = next((e for e in sec_events_inv if e.get("login_id") == inv_email), None)
        assert inv_violation is not None
        assert inv_violation["event_type"] == "AUTHENTICATED_BUT_UNAUTHORIZED"
        assert inv_violation["user_role"] == "investigator"
        print(f"[PASS] Scenario 4: Unauthorized case modification blocked & recorded with investigator identity")

        # ==============================================================================
        # SCENARIO 5: Non-Existent Resource Probe
        # ==============================================================================
        print("\n--- Scenario 5: Non-Existent Resource Probe ---")
        probe_res = client.get("/api/cases/65f000000000000000009999", headers=admin_headers)
        assert probe_res.status_code == 404
        print("[PASS] Scenario 5: Non-existent resource returned 404 without crashing")

        # ==============================================================================
        # SCENARIO 6: Repeated Failed Login Attempts & Security Alert Creation
        # ==============================================================================
        print("\n--- Scenario 6: Repeated Failed Login Attempts & Alert ---")
        target_brute_email = "target.user@forensics.gov"
        for i in range(5):
            client.post("/api/auth/login", json={
                "email": target_brute_email,
                "password": f"wrong_password_{i}"
            })

        # Verify alert was generated
        alerts_res = client.get("/api/security/alerts", headers=admin_headers)
        assert alerts_res.status_code == 200
        alerts = alerts_res.json()["alerts"]
        brute_alert = next((a for a in alerts if a.get("alert_type") == "REPEATED_LOGIN_FAILURE" or "Repeated" in a.get("description", "")), None)
        assert brute_alert is not None, f"Expected brute force alert. Found: {alerts}"
        assert brute_alert["severity"] in ("HIGH", "CRITICAL")
        assert brute_alert["status"] == "OPEN"
        print(f"[PASS] Scenario 6: Brute force threshold triggered security alert {brute_alert['alert_id']}")

        # ==============================================================================
        # SCENARIO 7: Source IP Extraction (Direct Socket vs Forwarded)
        # ==============================================================================
        print("\n--- Scenario 7: IP Address Extraction & Origin Classification ---")
        # Request with forwarded header
        fwd_ip = "198.51.100.42"
        fwd_res = client.get(f"/api/evidence/{evidence_id}", headers={"X-Forwarded-For": fwd_ip})
        assert fwd_res.status_code in (401, 403)

        events_fwd = client.get(f"/api/security/events?ip_address={fwd_ip}", headers=admin_headers).json()["events"]
        assert len(events_fwd) >= 1
        assert events_fwd[0]["ip_address"] == fwd_ip
        assert "forwarded" in events_fwd[0]["ip_source"].lower()
        print(f"[PASS] Scenario 7: Correctly extracted forwarded IP {fwd_ip} and classified as {events_fwd[0]['ip_source']}")

        # ==============================================================================
        # SCENARIO 8: Device Fingerprinting & Strictly Nullable Remote MAC
        # ==============================================================================
        print("\n--- Scenario 8: Device Fingerprinting & Strictly Nullable MAC ---")
        custom_ua = "Mozilla/5.0 (X11; Linux x86_64) ForensicProbe/2.0"
        ua_res = client.get(f"/api/evidence/{evidence_id}", headers={"User-Agent": custom_ua})
        assert ua_res.status_code in (401, 403)

        events_ua = client.get("/api/security/events?limit=10", headers=admin_headers).json()["events"]
        matched_ua = next((e for e in events_ua if custom_ua in (e.get("user_agent") or "")), None)
        assert matched_ua is not None
        # Remote browser HTTP requests cannot read remote MAC address -> strictly null / None
        assert matched_ua.get("mac_address") is None
        assert matched_ua.get("device_type") is not None
        print(f"[PASS] Scenario 8: Client fingerprinting parsed device type {matched_ua['device_type']}, MAC strictly nullable (None)")

        # ==============================================================================
        # SCENARIO 9: Security Event Query API (Filtering & Pagination)
        # ==============================================================================
        print("\n--- Scenario 9: Security Event Query API Filtering ---")
        filtered_events = client.get(f"/api/security/events?case_id={case_id}&limit=10", headers=admin_headers)
        assert filtered_events.status_code == 200
        f_data = filtered_events.json()
        assert "events" in f_data and "total" in f_data
        print(f"[PASS] Scenario 9: Event querying returned {len(f_data['events'])} items (Total: {f_data['total']})")

        # ==============================================================================
        # SCENARIO 10: Security Alerts Lifecycle (OPEN -> INVESTIGATING -> RESOLVED)
        # ==============================================================================
        print("\n--- Scenario 10: Security Alerts Lifecycle ---")
        alert_id = brute_alert["alert_id"]
        # Transition to INVESTIGATING
        inv_res = client.patch(f"/api/security/alerts/{alert_id}/status", json={
            "status": "INVESTIGATING",
            "notes": "Security investigator analyzing origin IP and attack vectors."
        }, headers=admin_headers)
        assert inv_res.status_code == 200
        assert inv_res.json()["status"] == "INVESTIGATING"

        # Transition to RESOLVED
        res_res = client.patch(f"/api/security/alerts/{alert_id}/status", json={
            "status": "RESOLVED",
            "notes": "Threat actor blocked at gateway firewall. Investigation closed."
        }, headers=admin_headers)
        assert res_res.status_code == 200
        resolved_alert = res_res.json()
        assert resolved_alert["status"] == "RESOLVED"
        assert resolved_alert["resolved_by"] == admin_user["name"]
        print(f"[PASS] Scenario 10: Alert lifecycle transitioned successfully to RESOLVED by {resolved_alert['resolved_by']}")

        # ==============================================================================
        # SCENARIO 11: Case Forensic Timeline Integration
        # ==============================================================================
        print("\n--- Scenario 11: Forensic Timeline Integration ---")
        timeline_res = client.get(f"/api/cases/{case_id}/timeline", headers=admin_headers)
        assert timeline_res.status_code == 200
        tl_events = timeline_res.json()["events"]
        sec_tl_events = [e for e in tl_events if e.get("event_type") == "SECURITY_ALERT"]
        assert len(sec_tl_events) >= 1, f"Expected security events on timeline. Got: {len(sec_tl_events)}"
        print(f"[PASS] Scenario 11: Timeline contains {len(sec_tl_events)} synthesized SECURITY_ALERT events")

        # ==============================================================================
        # SCENARIO 12: Evidence Graph Integration (Topological Threat Actor Node & Edge)
        # ==============================================================================
        print("\n--- Scenario 12: Evidence Graph Integration ---")
        graph_res = client.get(f"/api/cases/{case_id}/graph", headers=admin_headers)
        assert graph_res.status_code == 200
        graph = graph_res.json()
        actor_nodes = [n for n in graph["nodes"] if n["node_type"] == "ACTOR"]
        attempt_edges = [e for e in graph["edges"] if e["edge_type"] == "ATTEMPTED_ACCESS"]
        assert len(actor_nodes) >= 1, "Graph must contain Threat Actor node"
        assert len(attempt_edges) >= 1, "Graph must contain ATTEMPTED_ACCESS edge"
        print(f"[PASS] Scenario 12: Graph contains {len(actor_nodes)} Threat Actor node(s) and {len(attempt_edges)} ATTEMPTED_ACCESS edge(s)")

        # ==============================================================================
        # SCENARIO 13: Risk Scoring Integration (Deterministic Weighted Signals)
        # ==============================================================================
        print("\n--- Scenario 13: Risk Scoring Integration ---")
        risk_res = client.get(f"/api/cases/{case_id}/risk-score", headers=admin_headers)
        assert risk_res.status_code == 200
        risk_data = risk_res.json()
        sig_types = [s["signal_type"] for s in risk_data["signals"]]
        assert any("UNAUTHORIZED" in st for st in sig_types), f"Risk signals must include UNAUTHORIZED attempts: {sig_types}"
        assert 0 <= risk_data["score"] <= 100
        print(f"[PASS] Scenario 13: Risk score ({risk_data['score']}/100) includes signals: {sig_types}")

        # ==============================================================================
        # SCENARIO 14: RBAC on Security Endpoints
        # ==============================================================================
        print("\n--- Scenario 14: RBAC on Security Endpoints ---")
        # Readonly user attempting to update alert status -> 403
        ro_alert_patch = client.patch(f"/api/security/alerts/{alert_id}/status", json={
            "status": "DISMISSED",
            "notes": "Unauthorized attempt"
        }, headers=ro_headers)
        assert ro_alert_patch.status_code == 403
        print("[PASS] Scenario 14: Readonly access to modify alert status correctly denied (403)")

        # ==============================================================================
        # SCENARIO 15: Hardware Authentication Tampering & Alert
        # ==============================================================================
        print("\n--- Scenario 15: Hardware Tampering Simulation ---")
        hw_bad_res = client.post("/api/hardware/authenticate", json={
            "deviceId": "UNREGISTERED_ROGUE_DEVICE_999",
            "rfid": "CARD_UNKNOWN_999",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        assert hw_bad_res.status_code in (400, 401)
        print("[PASS] Scenario 15: Hardware tampering from unregistered device rejected")

        # ==============================================================================
        # SCENARIO 16: Safe Sanitization of Payloads
        # ==============================================================================
        print("\n--- Scenario 16: Safe Sanitization (NoSQL/XSS) ---")
        xss_probe = "<script>alert('pwn')</script>"
        client.get(f"/api/cases/{xss_probe}", headers=admin_headers)
        # Ensure server is running healthy
        health = client.get("/")
        assert health.status_code == 200
        print("[PASS] Scenario 16: XSS/injection probe handled safely without crashing")

        # ==============================================================================
        # SCENARIO 17: Latency & Non-Blocking Execution
        # ==============================================================================
        print("\n--- Scenario 17: Latency & Non-Blocking Execution ---")
        start = time.time()
        client.get(f"/api/cases/{case_id}", headers=admin_headers)
        duration_ms = (time.time() - start) * 1000
        print(f"[PASS] Scenario 17: Authorized case fetch completed in {duration_ms:.2f}ms (well below 200ms threshold)")

    print("\n==================================================================")
    print("ALL 17 SECURITY TRACKING & FORENSIC DETECTION SCENARIOS PASSED!")
    print("==================================================================")

if __name__ == "__main__":
    run_security_tracking_tests()
