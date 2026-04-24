"""Per-user connector tokens (GitHub PAT for now; Gmail/Drive later).

Tokens are stored on `user_profiles.connectors.<service>.token` (raw string) and
NEVER returned in API responses — callers only see a masked preview
(`ghp_...xK2`) and a boolean `connected`. Each route is user-scoped via
`require_user` so one user cannot read/write another user's tokens.

SECURITY NOTE:
- MongoDB database is private; raw tokens are at rest in the DB and in memory.
- This is acceptable for a personal tool; for multi-tenant SaaS, add Fernet
  encryption with a key in env and swap in `encrypt_token()/decrypt_token()`
  helpers below (stubs already scaffolded).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db import collection
from app.services.auth_service import require_user

router = APIRouter(prefix="/connectors", tags=["connectors"])


SUPPORTED_SERVICES = {"github"}


class ConnectorStatus(BaseModel):
    service: str
    connected: bool
    masked: str | None = None  # e.g. "ghp_...xK2"
    updated_at: str | None = None


class ConnectorTokenSet(BaseModel):
    token: str = Field(..., min_length=8, max_length=500)


def _mask(token: str) -> str:
    if not token or len(token) < 8:
        return "•••"
    return f"{token[:4]}…{token[-3:]}"


async def _get_profile_for_write(user: dict) -> dict:
    """Return (or upsert) the user's profile doc (user_email scoped)."""
    email = user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="user missing email")
    profile = await collection("user_profiles").find_one({"user_email": email}, {"_id": 0})
    if profile is None:
        # Minimal skeleton — matches existing upsert logic in caos.py
        profile = {"user_email": email, "connectors": {}}
        await collection("user_profiles").insert_one(dict(profile))
    return profile


async def get_github_token_for(user_email: str) -> str | None:
    """Internal helper: returns the raw GitHub token for a user, or None.
    Used by aria_tools.github_fetch to fall back to per-user token.
    """
    if not user_email:
        return None
    profile = await collection("user_profiles").find_one(
        {"user_email": user_email},
        {"_id": 0, "connectors": 1},
    )
    if not profile:
        return None
    return (profile.get("connectors") or {}).get("github", {}).get("token") or None


@router.get("/status", response_model=list[ConnectorStatus])
async def list_connectors(user: dict = Depends(require_user)) -> list[ConnectorStatus]:
    """List all connectors for the current user (masked)."""
    email = user.get("email")
    profile = await collection("user_profiles").find_one(
        {"user_email": email}, {"_id": 0, "connectors": 1}
    ) or {}
    connectors = profile.get("connectors") or {}
    result: list[ConnectorStatus] = []
    for service in SUPPORTED_SERVICES:
        entry = connectors.get(service) or {}
        token = entry.get("token") or ""
        result.append(ConnectorStatus(
            service=service,
            connected=bool(token),
            masked=_mask(token) if token else None,
            updated_at=entry.get("updated_at"),
        ))
    return result


@router.put("/{service}", response_model=ConnectorStatus)
async def set_connector_token(
    service: str,
    body: ConnectorTokenSet,
    user: dict = Depends(require_user),
) -> ConnectorStatus:
    """Store (or rotate) the token for a service. Owner-only."""
    if service not in SUPPORTED_SERVICES:
        raise HTTPException(status_code=400, detail=f"unsupported service: {service}")
    token = body.token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="token is empty")
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).isoformat()
    await _get_profile_for_write(user)
    await collection("user_profiles").update_one(
        {"user_email": user["email"]},
        {"$set": {
            f"connectors.{service}.token": token,
            f"connectors.{service}.updated_at": now_iso,
        }},
    )
    return ConnectorStatus(service=service, connected=True, masked=_mask(token), updated_at=now_iso)


@router.delete("/{service}", response_model=ConnectorStatus)
async def delete_connector_token(service: str, user: dict = Depends(require_user)) -> ConnectorStatus:
    """Remove a service token. Owner-only."""
    if service not in SUPPORTED_SERVICES:
        raise HTTPException(status_code=400, detail=f"unsupported service: {service}")
    await collection("user_profiles").update_one(
        {"user_email": user["email"]},
        {"$unset": {f"connectors.{service}": ""}},
    )
    return ConnectorStatus(service=service, connected=False)
