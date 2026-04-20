"""Emergent-managed Google OAuth.

Flow:
1. Frontend redirects to `https://auth.emergentagent.com/?redirect=<app_url>/dashboard`
2. After Google auth, user lands at `<app_url>/dashboard#session_id=<id>`
3. Frontend posts the session_id to `/api/auth/process-session` which exchanges
   it with Emergent's `/oauth/session-data` endpoint server-side, stores the
   returned session_token in our DB, and sets it as an httpOnly cookie.
4. Every subsequent request reads `session_token` from cookie (or Authorization
   header), looks it up in `user_sessions`, returns the linked `users` row.

We never trust `user_email` from the client again — the authenticator always
returns the email from the DB session, not from request params.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import Cookie, Header, HTTPException

from app.db import db


EMERGENT_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
SESSION_TTL = timedelta(days=7)


async def exchange_session_id(session_id: str) -> dict:
    """Exchange a one-time session_id (from URL fragment) for a persistent session_token."""
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(EMERGENT_SESSION_URL, headers={"X-Session-ID": session_id})
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail=f"Session exchange failed: {response.text[:200]}")
    data = response.json()
    for field in ("email", "name", "session_token"):
        if not data.get(field):
            raise HTTPException(status_code=401, detail=f"Session payload missing {field}")
    return data


async def upsert_user(email: str, name: str, picture: str) -> dict:
    """Create or update the users row. Returns the stored user dict (no _id)."""
    email = email.lower().strip()
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        await db.users.update_one(
            {"email": email},
            {"$set": {"name": name, "picture": picture, "last_login": datetime.now(timezone.utc).isoformat()}},
        )
        return {**existing, "name": name, "picture": picture}
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    doc = {
        "user_id": user_id,
        "email": email,
        "name": name,
        "picture": picture,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    return {k: v for k, v in doc.items() if k != "_id"}


async def record_session(user_id: str, session_token: str) -> None:
    expires_at = datetime.now(timezone.utc) + SESSION_TTL
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


async def resolve_user_from_token(token: str | None) -> dict | None:
    """Return the user doc for a valid session_token, or None."""
    if not token:
        return None
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        return None
    expires_at_raw = session.get("expires_at")
    if isinstance(expires_at_raw, str):
        expires_at = datetime.fromisoformat(expires_at_raw)
    else:
        expires_at = expires_at_raw
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at < datetime.now(timezone.utc):
        return None
    user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    return user


async def delete_session(token: str) -> None:
    await db.user_sessions.delete_one({"session_token": token})


async def require_user(
    session_token: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> dict:
    """FastAPI dependency — returns the authenticated user or 401s."""
    token = session_token
    if not token and authorization:
        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
    user = await resolve_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# Backwards-compatibility flag — can be flipped per-env to make auth advisory
# only (so we can roll out without breaking existing localStorage-only clients).
AUTH_ENFORCED = os.environ.get("AUTH_ENFORCED", "true").lower() not in ("false", "0", "no")


async def optional_user(
    session_token: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
) -> dict | None:
    """Resolve user if authenticated; return None otherwise. Never raises."""
    token = session_token
    if not token and authorization:
        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
    return await resolve_user_from_token(token)
