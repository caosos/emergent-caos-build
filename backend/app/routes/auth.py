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
    user: dict = Depends(require_user),
    session_token: str | None = Cookie(default=None, alias="session_token"),
):
    """Delete the current session from DB and clear the cookie."""
    if session_token:
        await delete_session(session_token)
    response.delete_cookie(key="session_token", path="/", secure=True, samesite="none")
    return {"ok": True}
