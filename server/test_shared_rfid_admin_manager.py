import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_database
from app.repositories.hardware import HardwareRepository
from app.repositories.user import UserRepository
from app.core.bootstrap import ensure_default_users

async def main():
    print("Testing Shared RFID between Admin and Portal Manager...")
    await ensure_default_users()
    db = get_database()
    
    user_repo = UserRepository(db)
    hw_repo = HardwareRepository(db)
    
    admin = await user_repo.get_by_email("admin@forensics.gov")
    manager = await user_repo.get_by_email("manager@forensics.gov")
    
    assert admin is not None, "Admin user must exist"
    assert manager is not None, "Manager user must exist"
    
    print(f"Admin RFID: {admin.get('rfid')}, FID: {admin.get('fingerprint_id')}")
    print(f"Manager RFID: {manager.get('rfid')}, FID: {manager.get('fingerprint_id')}")
    
    # Clean RFID comparison
    admin_rfid = admin.get("rfid", "").replace(" ", "").upper()
    manager_rfid = manager.get("rfid", "").replace(" ", "").upper()
    assert admin_rfid == manager_rfid, f"Admin and Manager RFIDs must match: {admin_rfid} vs {manager_rfid}"
    print(f"[PASS] Both accounts share identical RFID: {admin_rfid}")
    
    # Test get_all_by_rfid
    users_with_card = await user_repo.get_all_by_rfid(admin_rfid)
    emails_with_card = [u["email"] for u in users_with_card]
    print(f"Accounts holding card {admin_rfid}: {emails_with_card}")
    assert "admin@forensics.gov" in emails_with_card
    assert "manager@forensics.gov" in emails_with_card
    print("[PASS] get_all_by_rfid returns both Admin and Portal Manager")
    
    # Test ticket creation with shared allowed_emails
    ticket1 = await hw_repo.create_auth_ticket(
        uid=admin["rfid"],
        user_id=str(admin["_id"]),
        user_email=admin["email"],
        user_name=admin["name"],
        user_role=admin["role"],
        allowed_emails=emails_with_card
    )
    
    # Verify Admin can use ticket1
    is_valid_admin, msg_admin, _ = await hw_repo.verify_ticket_only(ticket1["ticket_id"], "admin@forensics.gov")
    assert is_valid_admin is True, f"Admin verification failed: {msg_admin}"
    print("[PASS] Admin pre-flight ticket verification passed")
    
    # Verify Portal Manager can also use ticket1 (shared card)
    is_valid_mgr, msg_mgr, _ = await hw_repo.verify_ticket_only(ticket1["ticket_id"], "manager@forensics.gov")
    assert is_valid_mgr is True, f"Portal Manager verification failed: {msg_mgr}"
    print("[PASS] Portal Manager pre-flight ticket verification passed for shared card ticket")
    
    # Verify unauthorized user cannot use ticket1
    is_valid_imp, msg_imp, _ = await hw_repo.verify_ticket_only(ticket1["ticket_id"], "impostor@forensics.gov")
    assert is_valid_imp is False, "Impostor should be rejected"
    print(f"[PASS] Impostor rejected correctly: {msg_imp}")
    
    # Consume ticket for manager using validate_and_consume_ticket
    is_consumed, msg_consume, _ = await hw_repo.validate_and_consume_ticket(ticket1["ticket_id"], "manager@forensics.gov")
    assert is_consumed is True, f"Consumption failed: {msg_consume}"
    print("[PASS] Ticket validated and consumed successfully by Portal Manager")
    
    # Second use should be rejected (single-use)
    is_replay_consumed, msg_replay, _ = await hw_repo.validate_and_consume_ticket(ticket1["ticket_id"], "admin@forensics.gov")
    assert is_replay_consumed is False, "Replay should be rejected"
    assert "already been consumed" in msg_replay
    print(f"[PASS] Replay protection enforced across shared users: {msg_replay}")
    
    # Test symmetric case: Ticket issued to Manager, consumed by Admin
    ticket2 = await hw_repo.create_auth_ticket(
        uid=manager["rfid"],
        user_id=str(manager["_id"]),
        user_email=manager["email"],
        user_name=manager["name"],
        user_role=manager["role"],
        allowed_emails=emails_with_card
    )
    is_consumed2, msg_consume2, _ = await hw_repo.validate_and_consume_ticket(ticket2["ticket_id"], "admin@forensics.gov")
    assert is_consumed2 is True, f"Admin consumption failed for manager ticket: {msg_consume2}"
    print("[PASS] Symmetric ticket issued to Portal Manager successfully consumed by Admin")
    
    print("\nALL SHARED RFID TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())
