from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

client = AsyncIOMotorClient(settings.mongodb_url)
db = client.griha_ai

async def get_db():
    try:
        yield db
    finally:
        pass
