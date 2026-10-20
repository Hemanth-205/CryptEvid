import asyncio
from fastapi.testclient import TestClient
from app.main import app

def run_tests():
    print("==================================================")
    print("RUNNING DIGITAL FORENSICS BACKEND VERIFICATION")
    print("==================================================")

    with TestClient(app) as client:
        # 1. Root and Documentation Endpoints
        root_res = client.get("/")
        assert root_res.status_code == 200, f"Root failed: {root_res.status_code}"
        print("[PASS] 1. Root endpoint: 200 OK ->", root_res.json())

        docs_res = client.get("/docs")
        assert docs_res.status_code == 200, f"Docs failed: {docs_res.status_code}"
        print("[PASS] 2. Swagger/OpenAPI docs (/docs): 200 OK")

        openapi_res = client.get("/openapi.json")
        assert openapi_res.status_code == 200, f"OpenAPI JSON failed: {openapi_res.status_code}"
        schema = openapi_res.json()
        assert "paths" in schema, "Invalid OpenAPI schema"
        print(f"[PASS] 3. OpenAPI Schema: 200 OK ({len(schema['paths'])} endpoints documented)")

        # 2. Settings Synchronization
        settings_res = client.get("/api/settings")
        assert settings_res.status_code == 200, f"Settings GET failed: {settings_res.status_code}"
        initial_settings = settings_res.json()
        print("[PASS] 4. Settings GET: 200 OK ->", initial_settings)

        # 3. Standard Credentials Authentication (Simulation Mode Active)
        login_res = client.post("/api/auth/login", json={
            "email": "admin@forensics.gov",
            "password": "password123"
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.status_code} {login_res.text}"
        login_data = login_res.json()
        jwt_token = login_data["access_token"]
        assert jwt_token, "No JWT token returned"
        print("[PASS] 5. Standard Credential Login: 200 OK (JWT Token received)")

        # 4. User Profile (/auth/me) with JWT
        headers = {"Authorization": f"Bearer {jwt_token}"}
        me_res = client.get("/api/auth/me", headers=headers)
        assert me_res.status_code == 200, f"/auth/me failed: {me_res.status_code}"
        user_info = me_res.json()
        assert user_info["email"] == "admin@forensics.gov"
        print(f"[PASS] 6. Authenticated Profile (/auth/me): {user_info['name']} ({user_info['role']})")

        # 5. Hardware Heartbeat Endpoint
        hb_res = client.post("/api/hardware/heartbeat", json={
            "device": "ESP32_01",
            "macAddress": "24:6F:28:AE:C3:0C",
            "firmwareVersion": "v1.0.4-forensic"
        })
        assert hb_res.status_code == 200, f"Heartbeat failed: {hb_res.status_code}"
        print("[PASS] 7. Hardware Heartbeat POST: 200 OK -> Device registered online")

        # 6. Hardware Devices Listing
        devices_res = client.get("/api/hardware/devices", headers=headers)
        assert devices_res.status_code == 200, f"Devices GET failed: {devices_res.status_code}"
        devices = devices_res.json()
        assert len(devices) > 0, "No devices found"
        found_device = any(d["device_id"] == "ESP32_01" for d in devices)
        assert found_device, "ESP32_01 not found in listed devices"
        print(f"[PASS] 8. Hardware Devices GET: 200 OK (Found {len(devices)} device(s))")

        # 7. Hardware Biometric Authentication (RFID Simulation)
        rfid_res = client.post("/api/hardware/authenticate", json={
            "deviceId": "ESP32_01",
            "rfid": "04A1B2C3",
            "timestamp": "2026-09-03T11:00:00Z"
        })
        assert rfid_res.status_code == 200, f"RFID auth failed: {rfid_res.status_code}"
        assert rfid_res.json()["success"] is True
        print("[PASS] 9. Hardware Authentication (RFID 04A1B2C3): 200 OK")

        # 8. Hardware Biometric Authentication (Fingerprint Simulation)
        fp_res = client.post("/api/hardware/authenticate", json={
            "deviceId": "ESP32_01",
            "fingerprintId": 12,
            "timestamp": "2026-09-03T11:00:00Z"
        })
        assert fp_res.status_code == 200, f"Fingerprint auth failed: {fp_res.status_code}"
        assert fp_res.json()["success"] is True
        print("[PASS] 10. Hardware Authentication (Fingerprint ID 12): 200 OK")

        # 9. Hardware Security Rejections (Tamper detection)
        unknown_dev = client.post("/api/hardware/authenticate", json={
            "deviceId": "ROGUE_ESP32",
            "rfid": "04A1B2C3",
            "timestamp": "2026-09-03T11:00:00Z"
        })
        assert unknown_dev.status_code == 400, "Should reject unregistered device"
        print("[PASS] 11. Tamper Alert: Rogue device rejected with 400 Bad Request")

        unknown_card = client.post("/api/hardware/authenticate", json={
            "deviceId": "ESP32_01",
            "rfid": "BAD_CARD_DEADBEEF",
            "timestamp": "2026-09-03T11:00:00Z"
        })
        assert unknown_card.status_code == 401, "Should reject unknown RFID card"
        print("[PASS] 12. Security Enforcement: Unknown RFID rejected with 401 Unauthorized")

        # 10. Simulation Mode Switching Test
        print("\n--- Testing Mode Switching (Hardware-Only vs Simulation) ---")
        # Turn simulation mode OFF
        toggle_off = client.post("/api/settings", json={"simulation_mode": False})
        assert toggle_off.status_code == 200
        assert toggle_off.json()["settings"]["simulation_mode"] is False
        print("[PASS] 13. Switched Simulation Mode -> OFF (Hardware-Only Mode Active)")

        # In Hardware-Only mode, standard password login MUST be blocked
        blocked_login = client.post("/api/auth/login", json={
            "email": "admin@forensics.gov",
            "password": "password123"
        })
        assert blocked_login.status_code == 403, f"Expected 403, got {blocked_login.status_code}"
        print("[PASS] 14. Standard Login in Hardware-Only Mode correctly blocked: 403 Forbidden")

        # Hardware authentication must still succeed in Hardware-Only mode
        hw_auth = client.post("/api/hardware/authenticate", json={
            "deviceId": "ESP32_01",
            "rfid": "04A1B2C3",
            "timestamp": "2026-09-03T11:00:00Z"
        })
        assert hw_auth.status_code == 200, "Hardware auth should work in Hardware-Only mode"
        print("[PASS] 15. Hardware Authentication works in Hardware-Only mode: 200 OK")

        # Re-enable simulation mode
        toggle_on = client.post("/api/settings", json={"simulation_mode": True})
        assert toggle_on.status_code == 200
        assert toggle_on.json()["settings"]["simulation_mode"] is True
        print("[PASS] 16. Switched Simulation Mode -> ON (Simulation Mode Restored)")

        # Verify password login works again
        re_login = client.post("/api/auth/login", json={
            "email": "admin@forensics.gov",
            "password": "password123"
        })
        assert re_login.status_code == 200
        print("[PASS] 17. Standard Password Login re-enabled: 200 OK")

        # 11. Chain of Custody Audit Logs
        audit_res = client.get("/api/audit-logs", headers=headers)
        assert audit_res.status_code == 200, f"Audit logs failed: {audit_res.status_code}"
        logs = audit_res.json()
        assert len(logs) > 0, "No audit logs found"
        print(f"[PASS] 18. Chain of Custody Audit Logs: 200 OK ({len(logs)} immutable log entries recorded)")

        # 12. WebSocket Real-Time Handshake and Communication
        with client.websocket_connect("/api/ws/hardware") as ws:
            ws.send_text("client_ping")
            ws_data = ws.receive_json()
            assert ws_data["type"] == "pong", f"Expected pong, got {ws_data}"
            print(f"[PASS] 19. WebSocket Hardware Endpoint: Connected, ping/pong validated -> {ws_data}")

    print("\n==================================================")
    print("ALL 19 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
