"""Seed two sessions (admin + regular) and print tokens as JSON."""
import asyncio, json, os, uuid
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv("/app/backend/.env")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


async def seed(email: str, name: str) -> str:
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    token = f"test_session_{uuid.uuid4().hex}"
    user_id = f"user_test_{uuid.uuid4().hex[:8]}"
    is_admin = email.lower().strip() in {"mytaxicloud@gmail.com"}
    role = "admin" if is_admin else "user"
    await db.users.update_one(
        {"email": email.lower()},
        {"$set": {
            "user_id": user_id,
            "email": email.lower(),
            "name": name,
            "picture": "",
            "role": role,
            "is_admin": is_admin,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )
    u = await db.users.find_one({"email": email.lower()}, {"_id": 0})
    await db.user_sessions.insert_one({
        "user_id": u["user_id"],
        "session_token": token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    client.close()
    return token


async def main():
    admin = await seed("mytaxicloud@gmail.com", "Admin User")
    regular = await seed(f"TEST_regular_{uuid.uuid4().hex[:6]}@example.com", "Regular User")
    print(json.dumps({"admin_token": admin, "regular_token": regular}))


asyncio.run(main())
