from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings


client = AsyncIOMotorClient(settings.mongo_url)
db = client[settings.db_name]


def collection(name: str):
    return db[name]