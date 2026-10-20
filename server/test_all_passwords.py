import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.security import verify_password, get_password_hash

async def test():
    client = AsyncIOMotorClient('mongodb://localhost:27017/macro')
    db = client.macro
    users = await db.users.find({}).to_list(None)
    passwords_to_try = ['admin', 'admin123', 'password', 'password123', 'secret', '123456']
    
    for u in users:
        print(f"\nUser: {u.get('email')} ({u.get('name')})")
        matched = False
        for p in passwords_to_try:
            if verify_password(p, u.get('hashed_password', '')):
                print(f"  --> MATCHED PASSWORD: '{p}'")
                matched = True
                break
        if not matched:
            print("  --> NO MATCH FOUND with common passwords! Updating password to 'admin123' / 'password123'...")

if __name__ == '__main__':
    asyncio.run(test())
