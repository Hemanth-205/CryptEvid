import asyncio
import sys
import os
import uuid
from datetime import datetime, timezone, timedelta

# Ensure server package path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_database
from app.repositories.hardware import HardwareRepository
from app.repositories.user import UserRepository
from app.core.security import get_password_hash, verify_password, create_access_token
from app.routers.settings import _global_settings_cache

async def run_tests():
    print("=" * 65)
    print("  CRYPTEVID — Two-Stage Authentication & Ticket Verification Suite")
    print("=" * 65)
    
    db = get_database()
    hw_repo = HardwareRepository(db)
    user_repo = UserRepository(db)

    # Clean up test tickets
    await db["hardware_auth_tickets"].delete_many({"user_email": "test_agent@forensics.gov"})

    # Ensure test investigator exists
    test_email = "test_agent@forensics.gov"
    existing_user = await user_repo.get_by_email(test_email)
    if not existing_user:
        user_doc = {
            "email": test_email,
            "name": "Special Agent Test",
            "role": "investigator",
            "hashed_password": get_password_hash("testpass123"),
            "rfid": "10 5B 96 5C",
            "fingerprint_id": 6,
            "is_active": True,
            "created_at": datetime.now(timezone.utc)
        }
        test_user = await user_repo.create(user_doc)
    else:
        test_user = existing_user

    user_id = str(test_user["_id"])
    print(f"[+] Loaded Test Investigator: {test_user['name']} ({test_email})")

    # -------------------------------------------------------------
    # Test 1: Generate Stage 1 Challenge Ticket
    # -------------------------------------------------------------
    print("\n--- Test 1: Stage 1 Challenge Ticket Generation ---")
    ticket = await hw_repo.create_auth_ticket(
        uid="10 5B 96 5C",
        user_id=user_id,
        user_email=test_email,
        user_name=test_user["name"],
        user_role=test_user["role"],
        ttl_seconds=300
    )
    assert ticket is not None, "Ticket generation failed"
    assert ticket["status"] == "VALID", f"Expected VALID status, got {ticket['status']}"
    assert ticket["ticket_id"].startswith("hw_ticket_"), "Invalid ticket ID format"
    assert ticket["user_email"] == test_email, "Email mismatch on ticket"
    print(f"  [PASS] Ticket generated: {ticket['ticket_id']} (Expires in: {ticket['expires_in_seconds']}s)")

    # -------------------------------------------------------------
    # Test 2: Verify Ticket Validity (Without Consuming)
    # -------------------------------------------------------------
    print("\n--- Test 2: Ticket Verification Pre-Flight (Non-Destructive) ---")
    is_valid, msg, doc = await hw_repo.verify_ticket_only(ticket["ticket_id"], test_email)
    assert is_valid is True, f"Expected valid ticket, got: {msg}"
    print(f"  [PASS] Pre-flight verification passed: {msg}")

    # -------------------------------------------------------------
    # Test 3: Ticket Email Binding (Cross-Identity Protection)
    # -------------------------------------------------------------
    print("\n--- Test 3: Identity Binding Enforcement ---")
    is_valid, msg, _ = await hw_repo.verify_ticket_only(ticket["ticket_id"], "impostor@forensics.gov")
    assert is_valid is False, "Ticket should NOT be valid for a different email"
    print(f"  [PASS] Cross-identity attack rejected: {msg}")

    # -------------------------------------------------------------
    # Test 4: Password Typo Retain Ticket Validity
    # -------------------------------------------------------------
    print("\n--- Test 4: Password Typo Handling (Ticket Preserved) ---")
    wrong_pwd = "wrong_password_attempt"
    valid_pwd = verify_password(wrong_pwd, test_user["hashed_password"])
    assert valid_pwd is False, "Password verify should fail"
    # Ticket should still be valid!
    is_valid_after_wrong_pwd, _, _ = await hw_repo.verify_ticket_only(ticket["ticket_id"], test_email)
    assert is_valid_after_wrong_pwd is True, "Ticket should remain VALID after a password typo"
    print("  [PASS] Ticket remains VALID after incorrect password attempt (investigator can retry)")

    # -------------------------------------------------------------
    # Test 5: Atomic Ticket Consumption upon Valid Software Login
    # -------------------------------------------------------------
    print("\n--- Test 5: Atomic Ticket Consumption on Login Success ---")
    correct_pwd = "testpass123"
    assert verify_password(correct_pwd, test_user["hashed_password"]) is True, "Password check failed"
    consumed = await hw_repo.consume_ticket(ticket["ticket_id"])
    assert consumed is True, "Ticket consumption failed"
    print(f"  [PASS] Ticket {ticket['ticket_id']} successfully marked CONSUMED")

    # -------------------------------------------------------------
    # Test 6: Replay Attack Prevention (Single-Use Enforcement)
    # -------------------------------------------------------------
    print("\n--- Test 6: Anti-Replay Protection (Single-Use Guarantee) ---")
    is_valid_replay, replay_msg, _ = await hw_repo.verify_ticket_only(ticket["ticket_id"], test_email)
    assert is_valid_replay is False, "Consumed ticket MUST NOT be accepted again"
    assert "consumed" in replay_msg.lower(), f"Unexpected replay error: {replay_msg}"
    print(f"  [PASS] Replay attack blocked: {replay_msg}")

    # -------------------------------------------------------------
    # Test 7: Expired Ticket Rejection
    # -------------------------------------------------------------
    print("\n--- Test 7: Expired Ticket Enforcement ---")
    expired_ticket = await hw_repo.create_auth_ticket(
        uid="10 5B 96 5C",
        user_id=user_id,
        user_email=test_email,
        user_name=test_user["name"],
        user_role=test_user["role"],
        ttl_seconds=-10 # already in the past
    )
    is_valid_exp, exp_msg, _ = await hw_repo.verify_ticket_only(expired_ticket["ticket_id"], test_email)
    assert is_valid_exp is False, "Expired ticket MUST be rejected"
    assert "expired" in exp_msg.lower(), f"Unexpected expiry error message: {exp_msg}"
    print(f"  [PASS] Expired ticket blocked: {exp_msg}")

    # -------------------------------------------------------------
    # Test 8: Revocation on Logout
    # -------------------------------------------------------------
    print("\n--- Test 8: Logout Revocation ---")
    active_ticket = await hw_repo.create_auth_ticket(
        uid="10 5B 96 5C",
        user_id=user_id,
        user_email=test_email,
        user_name=test_user["name"],
        user_role=test_user["role"],
        ttl_seconds=300
    )
    await hw_repo.invalidate_all_tickets_for_user(test_email)
    is_valid_revoked, rev_msg, _ = await hw_repo.verify_ticket_only(active_ticket["ticket_id"], test_email)
    assert is_valid_revoked is False, "Revoked ticket must be rejected"
    print(f"  [PASS] Ticket revoked on user logout: {rev_msg}")

    print("\n" + "=" * 65)
    print("  ALL TWO-STAGE AUTHENTICATION TESTS PASSED PERFECTLY!")
    print("=" * 65)

if __name__ == "__main__":
    asyncio.run(run_tests())
