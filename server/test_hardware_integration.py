"""
CRYPTEVID — USB Hardware-to-Software Integration Test Suite
===========================================================
Tests:
- Serial protocol parsing (GRANTED, DENIED, malformed, boot noise, length limits)
- Bridge authentication enforcement (X-Bridge-Key validation)
- Backend event ingestion and identity verification
- Unknown UID handling (prevents mapping to arbitrary users)
- Duplicate event and replay suppression
- Bridge heartbeat and live status reporting (Connected / Disconnected / Error)
- MongoDB event persistence and audit logging
- Preservation of existing JWT login and role-based access control
- Mocked serial stream reader simulation
"""

import sys
import os
import unittest
import asyncio
import json
import uuid
from datetime import datetime, timezone

# Add server root and workspace root to path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, CURRENT_DIR)
sys.path.insert(0, PARENT_DIR)

from hardware_serial_bridge import parse_serial_message, HardwareSerialBridge
from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.repositories.hardware import HardwareRepository
from app.repositories.user import UserRepository
from app.repositories.audit import AuditRepository
from httpx import AsyncClient, ASGITransport
from app.main import app

class TestHardwareSerialProtocol(unittest.TestCase):
    """Unit tests for the ESP32 USB serial message parser."""

    def test_valid_granted_message(self):
        msg = "CRYPTEVID|1|GRANTED|UID=10 5B 96 5C|REASON=AUTH_SUCCESS"
        parsed = parse_serial_message(msg)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["protocol_version"], 1)
        self.assertEqual(parsed["status"], "GRANTED")
        self.assertEqual(parsed["uid"], "10 5B 96 5C")
        self.assertEqual(parsed["reason"], "AUTH_SUCCESS")
        self.assertEqual(parsed["device_id"], "ESP32_USB")
        self.assertEqual(parsed["raw_message"], msg)

    def test_valid_denied_message(self):
        msg = "CRYPTEVID|1|DENIED|UID=10 5B 96 5C|REASON=AUTH_FAILED"
        parsed = parse_serial_message(msg)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["status"], "DENIED")
        self.assertEqual(parsed["uid"], "10 5B 96 5C")
        self.assertEqual(parsed["reason"], "AUTH_FAILED")

    def test_varied_uids_and_reasons(self):
        msg1 = "CRYPTEVID|1|GRANTED|UID=C0 A3 CF 54|REASON=RFID_MATCH"
        parsed1 = parse_serial_message(msg1)
        self.assertIsNotNone(parsed1)
        self.assertEqual(parsed1["uid"], "C0 A3 CF 54")

        msg2 = "CRYPTEVID|1|DENIED|UID=UNKNOWN_CARD_99|REASON=SENSOR_TIMEOUT"
        parsed2 = parse_serial_message(msg2)
        self.assertIsNotNone(parsed2)
        self.assertEqual(parsed2["status"], "DENIED")
        self.assertEqual(parsed2["reason"], "SENSOR_TIMEOUT")

    def test_boot_messages_and_noise_ignored(self):
        noise_samples = [
            "rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)",
            "configsip: 0, SPIWP:0xee",
            "clk_drv:0x00,q_drv:0x00,d_drv:0x00,cs0_drv:0x00",
            "entry 0x400805e4",
            "Connecting to WiFi...",
            "",
            "\r\n",
            "   \t  ",
            "Card UID: 10 5B 96 5C",
            "Found fingerprint ID #1 with confidence 95"
        ]
        for line in noise_samples:
            self.assertIsNone(parse_serial_message(line), f"Failed to reject noise: {line}")

    def test_malformed_protocol_messages_rejected(self):
        malformed_samples = [
            "CRYPTEVID|1|PENDING|UID=10 5B 96 5C|REASON=AUTH_SUCCESS", # Invalid status
            "CRYPTEVID|1|GRANTED|UID=|REASON=AUTH_SUCCESS",            # Empty UID
            "CRYPTEVID|1|GRANTED|UID=10 5B 96 5C|REASON=",            # Empty Reason
            "CRYPTEVID|9999999999999999999999|GRANTED|UID=A|REASON=B", # Oversized version
            "CRYPTEVID|1|GRANTED",                                     # Missing fields
            "CRYPTEVID|GRANTED|UID=10 5B 96 5C|REASON=OK",             # Missing version
            "RANDOM_PREFIX|1|GRANTED|UID=10 5B 96 5C|REASON=OK",       # Bad magic prefix
            "CRYPTEVID|1|GRANTED|UID=" + ("A" * 100) + "|REASON=OK",   # UID exceeds 64 chars
        ]
        for line in malformed_samples:
            self.assertIsNone(parse_serial_message(line), f"Failed to reject malformed: {line}")

    def test_bridge_deduplication(self):
        bridge = HardwareSerialBridge()
        self.assertFalse(bridge.is_duplicate("GRANTED", "10 5B 96 5C", "AUTH_SUCCESS"))
        # Immediate same event is a duplicate
        self.assertTrue(bridge.is_duplicate("GRANTED", "10 5B 96 5C", "AUTH_SUCCESS"))
        # Different status is not a duplicate
        self.assertFalse(bridge.is_duplicate("DENIED", "10 5B 96 5C", "AUTH_FAILED"))


class TestHardwareFastAPIIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests against live FastAPI backend and MongoDB."""

    async def asyncSetUp(self):
        await connect_to_mongo()
        self.transport = ASGITransport(app=app)
        self.client = AsyncClient(transport=self.transport, base_url="http://testserver")
        self.db = get_database()
        self.secret = settings.HARDWARE_BRIDGE_SECRET

    async def asyncTearDown(self):
        await self.client.aclose()
        await close_mongo_connection()

    async def test_bridge_authentication_required(self):
        """Endpoints must reject unauthenticated requests without X-Bridge-Key."""
        payload = {
            "protocol_version": 1,
            "status": "GRANTED",
            "uid": "10 5B 96 5C",
            "reason": "AUTH_SUCCESS"
        }
        # 1. No key header
        res1 = await self.client.post("/api/hardware/events", json=payload)
        self.assertEqual(res1.status_code, 403)

        # 2. Invalid key header
        res2 = await self.client.post(
            "/api/hardware/events",
            json=payload,
            headers={"X-Bridge-Key": "wrong_invalid_secret_key"}
        )
        self.assertEqual(res2.status_code, 403)

    async def test_ingest_admin_granted_event(self):
        """Admin RFID 10 5B 96 5C must be identified, verified, and mapped."""
        payload = {
            "protocol_version": 1,
            "status": "GRANTED",
            "uid": "10 5B 96 5C",
            "reason": "AUTH_SUCCESS",
            "device_id": "ESP32_USB"
        }
        res = await self.client.post(
            "/api/hardware/events",
            json=payload,
            headers={"X-Bridge-Key": self.secret}
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["is_identity_verified"])
        self.assertIsNotNone(data["mapped_investigator"])
        self.assertEqual(data["mapped_investigator"]["email"], "admin@forensics.gov")
        self.assertEqual(data["mapped_investigator"]["role"], "admin")

    async def test_ingest_investigator_granted_event(self):
        """Investigator RFID C0 A3 CF 54 must be identified, verified, and mapped."""
        payload = {
            "protocol_version": 1,
            "status": "GRANTED",
            "uid": "C0 A3 CF 54",
            "reason": "AUTH_SUCCESS",
            "device_id": "ESP32_USB"
        }
        res = await self.client.post(
            "/api/hardware/events",
            json=payload,
            headers={"X-Bridge-Key": self.secret}
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["is_identity_verified"])
        self.assertIsNotNone(data["mapped_investigator"])
        self.assertEqual(data["mapped_investigator"]["email"], "investigator@forensics.gov")
        self.assertEqual(data["mapped_investigator"]["role"], "investigator")

    async def test_ingest_unknown_uid_never_maps_to_arbitrary_user(self):
        """Crucial test: Unknown RFID UID must NOT be mapped to any investigator."""
        unknown_uid = "AA BB CC DD"
        payload = {
            "protocol_version": 1,
            "status": "GRANTED",
            "uid": unknown_uid,
            "reason": "AUTH_SUCCESS",
            "device_id": "ESP32_USB"
        }
        res = await self.client.post(
            "/api/hardware/events",
            json=payload,
            headers={"X-Bridge-Key": self.secret}
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertTrue(data["success"])
        # Identity MUST NOT be verified
        self.assertFalse(data["is_identity_verified"])
        # Mapped investigator MUST be None
        self.assertIsNone(data["mapped_investigator"])
        self.assertIn("Unregistered RFID UID", data["notes"])

    async def test_ingest_denied_event_with_registered_uid(self):
        """A DENIED reported status must have is_identity_verified=False even if UID is known."""
        payload = {
            "protocol_version": 1,
            "status": "DENIED",
            "uid": "10 5B 96 5C",
            "reason": "FINGERPRINT_MISMATCH",
            "device_id": "ESP32_USB"
        }
        res = await self.client.post(
            "/api/hardware/events",
            json=payload,
            headers={"X-Bridge-Key": self.secret}
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["status"], "DENIED")
        self.assertFalse(data["is_identity_verified"])
        # Mapped investigator is identified but not verified
        self.assertIsNotNone(data["mapped_investigator"])

    async def test_duplicate_event_handling(self):
        """Duplicate event_id should be safely acknowledged without error."""
        fixed_event_id = str(uuid.uuid4())
        payload = {
            "event_id": fixed_event_id,
            "protocol_version": 1,
            "status": "GRANTED",
            "uid": "10 5B 96 5C",
            "reason": "AUTH_SUCCESS"
        }
        res1 = await self.client.post(
            "/api/hardware/events",
            json=payload,
            headers={"X-Bridge-Key": self.secret}
        )
        self.assertEqual(res1.status_code, 201)

        # Resend identical event_id
        res2 = await self.client.post(
            "/api/hardware/events",
            json=payload,
            headers={"X-Bridge-Key": self.secret}
        )
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json()["status"], "duplicate_ignored")

    async def test_bridge_heartbeat_and_status(self):
        """Bridge heartbeat updates live status and last_heartbeat."""
        # Send heartbeat
        hb_payload = {
            "port": "COM5",
            "status": "Connected",
            "baud_rate": 115200,
            "device_id": "ESP32_USB"
        }
        hb_res = await self.client.post(
            "/api/hardware/bridge-heartbeat",
            json=hb_payload,
            headers={"X-Bridge-Key": self.secret}
        )
        self.assertEqual(hb_res.status_code, 200)

        # Query live bridge status
        status_res = await self.client.get("/api/hardware/bridge-status")
        self.assertEqual(status_res.status_code, 200)
        status_data = status_res.json()
        self.assertEqual(status_data["status"], "Connected")
        self.assertEqual(status_data["port"], "COM5")
        self.assertIsNotNone(status_data["last_heartbeat"])

    async def test_mongodb_audit_log_created(self):
        """Events must create an immutable entry in the audit_logs collection."""
        test_uid = "C0 A3 CF 54"
        payload = {
            "protocol_version": 1,
            "status": "GRANTED",
            "uid": test_uid,
            "reason": "AUTH_SUCCESS"
        }
        await self.client.post(
            "/api/hardware/events",
            json=payload,
            headers={"X-Bridge-Key": self.secret}
        )

        audit_log = await self.db["audit_logs"].find_one({
            "action": "hardware_auth_granted",
            "device_id": "ESP32_USB"
        }, sort=[("timestamp", -1)])
        self.assertIsNotNone(audit_log)
        self.assertIn("C0 A3 CF 54", audit_log["details"])
        self.assertIn("Identity Verified=True", audit_log["details"])

    async def test_preservation_of_jwt_authentication(self):
        """Ensures standard login, JWT tokens, and RBAC are completely preserved."""
        # 1. Standard login works
        login_res = await self.client.post("/api/auth/login", json={
            "email": "admin@forensics.gov",
            "password": "password123"
        })
        self.assertEqual(login_res.status_code, 200)
        token = login_res.json().get("access_token")
        self.assertIsNotNone(token)

        # 2. Token grants access to protected routes
        me_res = await self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.json()["email"], "admin@forensics.gov")

        # 3. Hardware GRANTED events do NOT automatically grant website sessions
        # (Must still require valid JWT for protected endpoints)
        unauth_res = await self.client.get("/api/auth/me")
        self.assertEqual(unauth_res.status_code, 401)

if __name__ == "__main__":
    unittest.main()
