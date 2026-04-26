"""Auth endpoints: process OAuth callback, whoami, logout."""
from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel

from app.services.auth_service import (
    delete_session,
    exchange_session_id,
    record_session,
    require_user,
    upsert_user,
)


router = APIRouter(prefix="/auth", tags=["auth"])


class ProcessSessionRequest(BaseModel):
    session_id: str


@router.post("/process-session")
async def process_session(input: ProcessSessionRequest, response: Response):
    """Called by the frontend after it lands on /dashboard#session_id=...

    Backend exchanges the one-time session_id for a 7-day session_token,
    stores it in MongoDB, and sets it as an httpOnly cookie.
    """
    data = await exchange_session_id(input.session_id)
    email = data["email"].lower().strip()
    name = data["name"]
    picture = data.get("picture", "")
    session_token = data["session_token"]

    user = await upsert_user(email, name, picture)
    await record_session(user["user_id"], session_token)

    # 7-day httpOnly cookie — secure + samesite=none so the cookie travels
    # across the frontend preview domain and the backend API domain.
    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=60 * 60 * 24 * 7,
        path="/",
        httponly=True,
        secure=True,
        samesite="none",
    )
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "picture": user.get("picture", ""),
        "role": user.get("role", "user"),
        "is_admin": bool(user.get("is_admin", False)),
    }


@router.get("/me")
async def whoami(user: dict = Depends(require_user)):
    """Returns the current user or 401. Source of truth for frontend auth state."""
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "picture": user.get("picture", ""),
        "role": user.get("role", "user"),
        "is_admin": bool(user.get("is_admin", False)),
    }


@router.post("/logout")
async def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias="session_token"),
):
    """Delete the current browser's session and clear the cookie.

    Intentionally does NOT require an authenticated user — a half-expired or
    mismatched session must still be able to log out cleanly. Otherwise the
    frontend gets a 401 here and the cookie never gets cleared, creating an
    "I click logout and it logs me right back in" loop.

    Per-device only — only deletes the session row matching the cookie's
    token. Other browsers / devices the user is signed in on stay alive.
    """
    if session_token:
        await delete_session(session_token)
    # Cookie attributes MUST match the ones used in set_cookie above (httponly,
    # secure, samesite). If any attribute differs the browser silently keeps
    # the original cookie and the user appears to never log out.
    response.delete_cookie(
        key="session_token",
        path="/",
        httponly=True,
        secure=True,
        samesite="none",
    )
    # Belt-and-suspenders: also send an explicit expired cookie header. Some
    # Starlette versions don't include all attrs in delete_cookie consistently.
    response.set_cookie(
        key="session_token",
        value="",
        max_age=0,
        path="/",
        httponly=True,
        secure=True,
        samesite="none",
    )
    return {"ok": True}
