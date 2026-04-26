"""Quick Capture routes — /api/caos/captures.

Owner-gated for the in-app UI (cookie session).
ALSO accepts external posts via Bearer `caos_xxx` API key in the
Authorization header — for Apple Shortcut / Bee poll / custom scripts to
ingest captures without going through OAuth.
"""
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException

from app.schemas.captures import (
    ApiKeyResponse,
    CaptureCreateRequest,
    CaptureListResponse,
    CapturePromoteResponse,
    CaptureRecord,
)
from app.services.auth_service import require_user, resolve_user_from_token
from app.services.captures_service import (
    count_captures_by_status,
    create_capture,
    delete_capture,
    dismiss_capture,
    get_api_key_meta,
    issue_api_key,
    list_captures,
    promote_capture,
    resolve_user_from_api_key,
)


router = APIRouter(prefix="/caos/captures", tags=["caos-captures"])
key_router = APIRouter(prefix="/caos/api-key", tags=["caos-api-key"])


def _ensure_owner(requested_email: str, user: dict) -> None:
    if (requested_email or "").strip().lower() != (user.get("email") or "").strip().lower():
        raise HTTPException(status_code=403, detail="Not your captures")


# ---- Capture endpoints ---------------------------------------------------


@router.post("", response_model=CaptureRecord)
async def create_capture_route(
    payload: CaptureCreateRequest,
    authorization: str | None = Header(default=None),
    session_token: str | None = Cookie(default=None, alias="session_token"),
):
    """Dual-auth ingest:
    - **Cookie session** (in-app manual entry / voice button) → session_token cookie
    - **API key** (`Authorization: Bearer caos_xxx`) → resolve via api_keys table

    Cookie path takes precedence when both present (in-app POSTs always use it).
    """
    user_email: str | None = None
    # 1. Try cookie-based session first (in-app form path).
    if session_token:
        cookie_user = await resolve_user_from_token(session_token)
        if cookie_user:
            user_email = cookie_user["email"]
    # 2. Bearer header fallback — for Apple Shortcut, Bee, scripts.
    if not user_email and authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if token.startswith("caos_"):
            api_user = await resolve_user_from_api_key(token)
            if api_user:
                user_email = api_user["email"]
        else:
            session_user = await resolve_user_from_token(token)
            if session_user:
                user_email = session_user["email"]
    if not user_email:
        raise HTTPException(status_code=401, detail="Missing or invalid auth")
    return await create_capture(user_email, payload)


@router.get("", response_model=CaptureListResponse)
async def list_captures_route(
    user_email: str,
    status: str | None = None,
    user: dict = Depends(require_user),
):
    _ensure_owner(user_email, user)
    captures = await list_captures(user_email, status=status)
    counts = await count_captures_by_status(user_email)
    return CaptureListResponse(user_email=user_email, captures=captures, counts=counts)


@router.post("/{capture_id}/dismiss", response_model=CaptureRecord)
async def dismiss_capture_route(
    capture_id: str,
    user_email: str,
    user: dict = Depends(require_user),
):
    _ensure_owner(user_email, user)
    try:
        return await dismiss_capture(user_email, capture_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{capture_id}")
async def delete_capture_route(
    capture_id: str,
    user_email: str,
    user: dict = Depends(require_user),
):
    _ensure_owner(user_email, user)
    try:
        return await delete_capture(user_email, capture_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{capture_id}/promote", response_model=CapturePromoteResponse)
async def promote_capture_route(
    capture_id: str,
    user_email: str,
    user: dict = Depends(require_user),
):
    _ensure_owner(user_email, user)
    try:
        return await promote_capture(user_email, capture_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---- API key endpoints ---------------------------------------------------


@key_router.get("")
async def get_api_key_route(
    user_email: str,
    user: dict = Depends(require_user),
):
    """Return key metadata (prefix, issued_at, last_used_at). Never returns
    the plaintext — that's only shown ONCE at issuance time."""
    _ensure_owner(user_email, user)
    meta = await get_api_key_meta(user_email)
    if not meta:
        return {"has_key": False}
    return {"has_key": True, **meta}


@key_router.post("/rotate", response_model=ApiKeyResponse)
async def rotate_api_key_route(
    user_email: str,
    user: dict = Depends(require_user),
):
    """Generate a fresh API key, replacing any prior key. Returns plaintext
    ONCE — the user must copy it now or rotate again."""
    _ensure_owner(user_email, user)
    return await issue_api_key(user_email)
