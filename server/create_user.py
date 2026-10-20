import asyncio
import sys
from datetime import datetime
from app.core.database import connect_to_mongo, get_database, close_mongo_connection
from app.core.security import get_password_hash
from app.repositories.user import UserRepository

async def main():
    if len(sys.argv) < 4:
        print("Usage: python create_user.py <email> <password> <name> [rfid] [fingerprint_id]")
        print("Example: python create_user.py admin@forensics.gov password123 \"Lead Investigator\" \"04A1B2C3\" 12")
        return
    
    email = sys.argv[1]
    password = sys.argv[2]
    name = sys.argv[3]
    rfid = sys.argv[4] if len(sys.argv) > 4 else None
    fingerprint_id = int(sys.argv[5]) if len(sys.argv) > 5 else None

    # Load DB connection
    await connect_to_mongo()
    db = get_database()
    user_repo = UserRepository(db)
    
    # Check if exists
    existing = await user_repo.get_by_email(email)
    if existing:
        print(f"User {email} already exists!")
        await close_mongo_connection()
        return

    # Check if this is the first user
    all_users = await user_repo.list_users()
    role = "admin" if len(all_users) == 0 else "investigator"
    
    user_doc = {
        "email": email.lower(),
        "name": name,
        "role": role,
        "hashed_password": get_password_hash(password),
        "rfid": rfid,
        "fingerprint_id": fingerprint_id,
        "is_active": True,
        "created_at": datetime.utcnow()
    }
    
    created = await user_repo.create(user_doc)
    print(f"\n=======================================================")
    print(f"Created Investigator successfully!")
    print(f"Role: {role.upper()}")
    print(f"ID: {created['_id']}")
    print(f"Email: {created['email']}")
    print(f"RFID Card Bind: {rfid or 'None'}")
    print(f"Fingerprint ID Bind: {fingerprint_id if fingerprint_id is not None else 'None'}")
    print(f"=======================================================\n")
    
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(main())
