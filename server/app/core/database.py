# pyrefly: ignore [missing-import]
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None

db_holder = Database()

async def connect_to_mongo():
    db_holder.client = AsyncIOMotorClient(settings.MONGODB_URL)
    db_holder.db = db_holder.client[settings.DATABASE_NAME]
    print(f"Connected to MongoDB at {settings.MONGODB_URL}")

async def close_mongo_connection():
    if db_holder.client:
        db_holder.client.close()
        db_holder.client = None
        db_holder.db = None
        print("Closed MongoDB connection")

def get_database():
    if db_holder.db is None or db_holder.client is None:
        db_holder.client = AsyncIOMotorClient(settings.MONGODB_URL)
        db_holder.db = db_holder.client[settings.DATABASE_NAME]
    return db_holder.db
