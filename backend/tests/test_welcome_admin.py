"""Backend tests for iteration 14: welcome/tour screen + admin auto-assignment."""
import os
import uuid
import asyncio
from datetime import datetime, timezone, timedelta

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://caos-workspace-1.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


def _seed_session(email: str, name: str = "Test User") -> str:
    """Seed a user + session and return the session token (sync wrapper)."""
    async def _inner():
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        token = f"test_session_{uuid.uuid4().hex}"
        user_id = f"user_test_{uuid.uuid4().hex[:8]}"
        # Simulate what auth_service.upsert_user does for admin emails
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
        # Re-read user_id in case it was pre-existing
        u = await db.users.find_one({"email": email.lower()}, {"_id": 0})
        await db.user_sessions.insert_one({
            "user_id": u["user_id"],
            "session_token": token,
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        client.close()
        return token
    return asyncio.run(_inner())


# --- Health subsystem parity ---
class TestHealth:
    def test_health_ok(self):
        r = requests.get(f"{BASE_URL}/api/health", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        subs = data.get("subsystems", {})
        for key in ("mongo", "auth", "object_storage", "emergent_llm_proxy", "openai_voice", "agent_swarm"):
            assert key in subs, f"missing subsystem: {key}"
            assert subs[key].get("ok") is True, f"subsystem {key} not ok: {subs[key]}"


# --- Admin auto-assignment ---
class TestAdminAssignment:
    def test_admin_email_gets_admin_role(self):
        token = _seed_session("mytaxicloud@gmail.com", name="Admin User")
        r = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("email") == "mytaxicloud@gmail.com"
        assert data.get("role") == "admin", f"expected role=admin, got {data.get('role')}"
        assert data.get("is_admin") is True, f"expected is_admin=true, got {data.get('is_admin')}"

    def test_regular_email_gets_user_role(self):
        token = _seed_session(f"TEST_regular_{uuid.uuid4().hex[:6]}@example.com", name="Regular User")
        r = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("role") == "user"
        assert data.get("is_admin") is False

    def test_auth_me_without_token_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 401
