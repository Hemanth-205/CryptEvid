# pyrefly: ignore [missing-import]
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_holder = Database()

import asyncio

async def connect_to_mongo():
    url = settings.MONGODB_URL
    db_holder.client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=5000)
    db_holder.db = db_holder.client[settings.DATABASE_NAME]
    safe_log_url = url.split("@")[-1] if "@" in url else url
    print(f"Connecting to MongoDB at {safe_log_url}...")
    try:
        await asyncio.wait_for(db_holder.client.admin.command('ping'), timeout=5.0)
        print(f"Successfully connected to MongoDB at {safe_log_url}")
    except Exception as e:
        print(f"[MONGODB WARNING] Could not ping MongoDB ({safe_log_url}): {e}")
        raise e

async def close_mongo_connection():
    if db_holder.client:
        db_holder.client.close()
        db_holder.client = None
        db_holder.db = None
        print("Closed MongoDB connection")

def get_database():
    if db_holder.db is None or db_holder.client is None:
        url = settings.MONGODB_URL
        db_holder.client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=5000)
        db_holder.db = db_holder.client[settings.DATABASE_NAME]
    return db_holder.db
