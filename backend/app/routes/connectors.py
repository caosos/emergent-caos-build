"""Per-user connector tokens.

Two flavours coexist here:

1. **Token-based** (GitHub PAT) — user pastes a PAT into Settings, we store it
   on `user_profiles.connectors.<service>.token`. Same shape that has been in
   production since the original connectors patch.

2. **OAuth-based** (Google: Gmail/Drive/Docs/Calendar in one consent) — user
   clicks "Connect Google" in the Connectors hub, the popup runs the
   authorization-code flow, the encrypted access+refresh tokens land in the
   `connector_tokens` collection (`token_vault.py`), and Aria's tools read
   them on demand via `services.google_client.build_service`.

Both flavours surface a single unified `ConnectorState` shape on
`GET /connectors/list` so the frontend renders one card per provider.

REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS,
THIS BREAKS THE AUTH. The Google redirect URI is supplied by the frontend
(built from `window.location.origin`) at OAuth start time and echoed back
on callback so the code-exchange uses the SAME URI Google saw.

Routes mounted under `/api/connectors/*` from `server.py`.
"""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db import collection
from app.schemas.connectors import (
    ConnectorState,
    GoogleCallbackRequest,
    GoogleCallbackResponse,
    GoogleStartResponse,
)
from app.services import token_vault
from app.services.auth_service import require_user

router = APIRouter(prefix="/connectors", tags=["connectors"])


# ---- legacy GitHub PAT (extended for Slack / Twilio / Telegram) ----------

# All of these use simple credential storage in `user_profiles.connectors.<key>`
# (no OAuth dance). Slack uses a single bot token (xoxb-…). Twilio uses
# {account_sid, auth_token, from_number}. Telegram uses a bot_token.
LEGACY_PAT_SERVICES = {"github", "slack"}
MESSAGING_SERVICES = {"twilio", "telegram"}


class ConnectorStatus(BaseModel):
    """Legacy GitHub-PAT shape kept for backward compatibility with old UI."""
    service: str
    connected: bool
    masked: str | None = None
    updated_at: str | None = None


class ConnectorTokenSet(BaseModel):
    token: str = Field(..., min_length=8, max_length=500)


def _mask(token: str) -> str:
    if not token or len(token) < 8:
        return "•••"
    return f"{token[:4]}…{token[-3:]}"


async def _get_profile_for_write(user: dict) -> dict:
    email = user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="user missing email")
    profile = await collection("user_profiles").find_one({"user_email": email}, {"_id": 0})
    if profile is None:
        profile = {"user_email": email, "connectors": {}}
        await collection("user_profiles").insert_one(dict(profile))
    return profile


async def get_github_token_for(user_email: str) -> str | None:
    """Internal helper used by aria_tools.github_fetch."""
    if not user_email:
        return None
    profile = await collection("user_profiles").find_one(
        {"user_email": user_email}, {"_id": 0, "connectors": 1},
    )
    if not profile:
        return None
    return (profile.get("connectors") or {}).get("github", {}).get("token") or None


@router.get("/status", response_model=list[ConnectorStatus])
async def list_legacy_connectors(user: dict = Depends(require_user)) -> list[ConnectorStatus]:
    """LEGACY shape — kept so the existing GitHub PAT settings row keeps working."""
    email = user.get("email")
    profile = await collection("user_profiles").find_one(
        {"user_email": email}, {"_id": 0, "connectors": 1}
    ) or {}
    connectors = profile.get("connectors") or {}
    result: list[ConnectorStatus] = []
    for service in LEGACY_PAT_SERVICES:
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
    if service not in LEGACY_PAT_SERVICES:
        raise HTTPException(status_code=400, detail=f"unsupported service: {service}")
    token = body.token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="token is empty")
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
async def delete_legacy_connector_token(
    service: str, user: dict = Depends(require_user)
) -> ConnectorStatus:
    if service not in LEGACY_PAT_SERVICES and service not in MESSAGING_SERVICES:
        raise HTTPException(status_code=400, detail=f"unsupported service: {service}")
    await collection("user_profiles").update_one(
        {"user_email": user["email"]},
        {"$unset": {f"connectors.{service}": ""}},
    )
    return ConnectorStatus(service=service, connected=False)


# ---- Twilio (multi-field credentials) -------------------------------------

class TwilioConfig(BaseModel):
    account_sid: str = Field(..., min_length=10, max_length=200)
    auth_token: str = Field(..., min_length=10, max_length=200)
    from_number: str = Field(..., min_length=4, max_length=30)


@router.put("/twilio", response_model=ConnectorStatus)
async def set_twilio_config(
    body: TwilioConfig, user: dict = Depends(require_user),
) -> ConnectorStatus:
    now_iso = datetime.now(timezone.utc).isoformat()
    await _get_profile_for_write(user)
    await collection("user_profiles").update_one(
        {"user_email": user["email"]},
        {"$set": {
            "connectors.twilio.account_sid": body.account_sid.strip(),
            "connectors.twilio.auth_token": body.auth_token.strip(),
            "connectors.twilio.from_number": body.from_number.strip(),
            "connectors.twilio.updated_at": now_iso,
        }},
    )
    return ConnectorStatus(service="twilio", connected=True, masked=body.from_number, updated_at=now_iso)


# ---- Telegram (single bot_token field) ------------------------------------

class TelegramConfig(BaseModel):
    bot_token: str = Field(..., min_length=10, max_length=300)


@router.put("/telegram", response_model=ConnectorStatus)
async def set_telegram_config(
    body: TelegramConfig, user: dict = Depends(require_user),
) -> ConnectorStatus:
    now_iso = datetime.now(timezone.utc).isoformat()
    await _get_profile_for_write(user)
    await collection("user_profiles").update_one(
        {"user_email": user["email"]},
        {"$set": {
            "connectors.telegram.bot_token": body.bot_token.strip(),
            "connectors.telegram.updated_at": now_iso,
        }},
    )
    return ConnectorStatus(service="telegram", connected=True, masked=_mask(body.bot_token), updated_at=now_iso)


# ---- Connection helpers used by chat_pipeline -----------------------------

async def is_slack_connected(user_email: str) -> bool:
    if not user_email:
        return False
    profile = await collection("user_profiles").find_one(
        {"user_email": user_email}, {"_id": 0, "connectors": 1},
    ) or {}
    return bool(((profile.get("connectors") or {}).get("slack") or {}).get("token"))


async def is_messaging_connected(user_email: str) -> dict[str, bool]:
    if not user_email:
        return {"twilio": False, "telegram": False}
    profile = await collection("user_profiles").find_one(
        {"user_email": user_email}, {"_id": 0, "connectors": 1},
    ) or {}
    cfg = profile.get("connectors") or {}
    tw = cfg.get("twilio") or {}
    tg = cfg.get("telegram") or {}
    return {
        "twilio": bool(tw.get("account_sid") and tw.get("auth_token") and tw.get("from_number")),
        "telegram": bool(tg.get("bot_token")),
    }


# ---- unified hub list ------------------------------------------------------

@router.get("/list", response_model=list[ConnectorState])
async def list_all_connectors(user: dict = Depends(require_user)) -> list[ConnectorState]:
    """Single endpoint the Connectors hub UI calls — returns one card per
    supported provider, regardless of underlying auth flavour.
    """
    email = user.get("email") or ""
    states: list[ConnectorState] = []

    # GitHub (legacy PAT)
    profile = await collection("user_profiles").find_one(
        {"user_email": email}, {"_id": 0, "connectors": 1}
    ) or {}
    connectors_doc = profile.get("connectors") or {}
    gh = connectors_doc.get("github") or {}
    states.append(ConnectorState(
        provider="github",
        label="GitHub",
        connected=bool(gh.get("token")),
        masked_identity=_mask(gh.get("token") or ""),
        scopes=["repo:read"] if gh.get("token") else [],
        updated_at=gh.get("updated_at"),
    ))

    # Slack (bot token, PAT-style)
    sl = connectors_doc.get("slack") or {}
    states.append(ConnectorState(
        provider="slack",
        label="Slack",
        connected=bool(sl.get("token")),
        masked_identity=_mask(sl.get("token") or ""),
        scopes=["channels:read", "channels:history", "chat:write"] if sl.get("token") else [],
        updated_at=sl.get("updated_at"),
    ))

    # Twilio (account sid + auth token + from number)
    tw = connectors_doc.get("twilio") or {}
    tw_connected = bool(tw.get("account_sid") and tw.get("auth_token") and tw.get("from_number"))
    states.append(ConnectorState(
        provider="twilio",
        label="Twilio SMS",
        connected=tw_connected,
        masked_identity=tw.get("from_number") if tw_connected else None,
        scopes=["sms.send", "sms.read"] if tw_connected else [],
        updated_at=tw.get("updated_at"),
    ))

    # Telegram (bot token)
    tg = connectors_doc.get("telegram") or {}
    states.append(ConnectorState(
        provider="telegram",
        label="Telegram",
        connected=bool(tg.get("bot_token")),
        masked_identity=_mask(tg.get("bot_token") or ""),
        scopes=["bot.send", "bot.read"] if tg.get("bot_token") else [],
        updated_at=tg.get("updated_at"),
    ))

    # Google (OAuth)
    google_row = await token_vault.get_token_row(email, "google") if email else None
    if google_row:
        states.append(ConnectorState(
            provider="google",
            label="Google Workspace",
            connected=not google_row.get("needs_reauth", False),
            masked_identity=google_row.get("google_email"),
            scopes=google_row.get("scopes", []),
            needs_reauth=bool(google_row.get("needs_reauth", False)),
            last_error=google_row.get("last_error"),
            updated_at=google_row.get("updated_at"),
        ))
    else:
        states.append(ConnectorState(
            provider="google",
            label="Google Workspace",
            connected=False,
        ))

    # Obsidian (file vault)
    if email:
        vault = await collection("obsidian_vaults").find_one({"user_email": email}, {"_id": 0})
    else:
        vault = None
    if vault and vault.get("note_count"):
        states.append(ConnectorState(
            provider="obsidian",
            label="Obsidian",
            connected=True,
            masked_identity=f"{vault['note_count']} notes · {vault.get('tag_count', 0)} tags",
            updated_at=vault.get("uploaded_at"),
        ))
    else:
        states.append(ConnectorState(provider="obsidian", label="Obsidian", connected=False))

    # MCP servers (one card aggregates the count; the drawer can drill in)
    if email:
        mcp_count = await collection("mcp_servers").count_documents({"user_email": email})
    else:
        mcp_count = 0
    states.append(ConnectorState(
        provider="mcp",
        label="MCP Servers",
        connected=mcp_count > 0,
        masked_identity=f"{mcp_count} server(s)" if mcp_count else None,
    ))

    return states


# ---- Google OAuth ----------------------------------------------------------

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"

# Read-only Workspace scopes for Sprint 1. Adding write scopes (gmail.send,
# calendar.events) will require user consent re-flow + per-action approval UI.
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


class StartGoogleRequest(BaseModel):
    redirect_uri: str  # frontend builds via window.location.origin


@router.post("/google/start", response_model=GoogleStartResponse)
async def start_google_oauth(
    body: StartGoogleRequest, user: dict = Depends(require_user)
) -> GoogleStartResponse:
    """Phase 1 of the Google OAuth dance — return the consent URL the popup
    should open. The frontend supplies the redirect_uri (built from
    window.location.origin) so we honour whatever domain the user is on
    (preview vs custom domain).
    """
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=500, detail="server missing GOOGLE_OAUTH_CLIENT_ID")
    redirect_uri = (body.redirect_uri or "").strip()
    if not redirect_uri.startswith("http"):
        raise HTTPException(status_code=400, detail="redirect_uri must be an absolute URL")

    state = secrets.token_urlsafe(32)
    # Bind state to the user so a stolen code can't be exchanged for someone
    # else's tokens. 10-minute TTL.
    await collection("oauth_state_cache").update_one(
        {"state": state},
        {"$set": {
            "state": state,
            "user_email": user["email"],
            "provider": "google",
            "redirect_uri": redirect_uri,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )
    # Encode params manually so the popup gets a clean canonical URL.
    from urllib.parse import urlencode
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",  # we want a refresh_token
        # `select_account` forces Google to show the account picker instead
        # of silently using whatever account the browser is currently signed
        # into. `consent` forces re-consent so a refresh_token is always
        # issued (Google only returns refresh_tokens on first consent unless
        # consent is forced). Both must be space-separated in a single
        # `prompt` param per Google's spec.
        "prompt": "select_account consent",
        "state": state,
        "include_granted_scopes": "true",
    }
    auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return GoogleStartResponse(auth_url=auth_url, state=state)


@router.post("/google/callback", response_model=GoogleCallbackResponse)
async def google_oauth_callback(
    body: GoogleCallbackRequest, user: dict = Depends(require_user)
) -> GoogleCallbackResponse:
    """Phase 2 — frontend popup forwarded `code` + `state` here; exchange
    the code for tokens, store encrypted, return the connected email.
    """
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="server missing GOOGLE_OAUTH credentials")

    state_doc = await collection("oauth_state_cache").find_one({"state": body.state}, {"_id": 0})
    if not state_doc:
        return GoogleCallbackResponse(ok=False, error="state expired or not found")
    if state_doc.get("user_email") != user["email"]:
        # State belongs to a different user — refuse.
        return GoogleCallbackResponse(ok=False, error="state user mismatch")
    # One-shot — burn the state row.
    await collection("oauth_state_cache").delete_one({"state": body.state})

    redirect_uri = body.redirect_uri or state_doc.get("redirect_uri") or ""
    payload = {
        "code": body.code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            token_resp = await http.post(GOOGLE_TOKEN_URL, data=payload)
    except Exception as error:
        return GoogleCallbackResponse(ok=False, error=f"network error: {str(error)[:120]}")

    if token_resp.status_code != 200:
        return GoogleCallbackResponse(
            ok=False,
            error=f"google rejected code (HTTP {token_resp.status_code}): {token_resp.text[:160]}",
        )
    tokens = token_resp.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    expires_in = int(tokens.get("expires_in", 3600))
    granted_scopes_raw = tokens.get("scope", "")
    granted_scopes = [s for s in granted_scopes_raw.split() if s] or GOOGLE_SCOPES

    if not access_token:
        return GoogleCallbackResponse(ok=False, error="no access_token in response")

    # Fetch the user's google email so we can show "connected as <email>"
    google_email = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            ui = await http.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if ui.status_code == 200:
            google_email = (ui.json() or {}).get("email")
    except Exception:
        pass  # not fatal; we just won't display the email

    await token_vault.store_google_token(
        user["email"],
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        scopes=granted_scopes,
        google_email=google_email,
        redirect_uri=redirect_uri,
    )
    return GoogleCallbackResponse(ok=True, email=google_email, scopes=granted_scopes)


@router.post("/google/disconnect")
async def disconnect_google(user: dict = Depends(require_user)) -> dict:
    """Revoke the Google token + delete the row. Best-effort revoke at Google;
    even if revoke fails, we always delete locally so the user is "off."
    """
    email = user["email"]
    row = await token_vault.get_token_row(email, "google")
    if row:
        try:
            access_token = token_vault.decrypt(row.get("encrypted_access_token"))
            if access_token:
                async with httpx.AsyncClient(timeout=10.0) as http:
                    await http.post(GOOGLE_REVOKE_URL, params={"token": access_token})
        except Exception:
            pass  # never block disconnect on a failed revoke
    await token_vault.delete_token(email, "google")
    return {"ok": True}


# ---- internal helper consumed by chat_pipeline -----------------------------

async def is_google_connected(user_email: str) -> bool:
    """Cheap connection check used to decide whether to inject Google tools
    into Aria's system prompt for this turn.
    """
    if not user_email:
        return False
    row = await token_vault.get_token_row(user_email, "google")
    return bool(row) and not row.get("needs_reauth", False)


# ─── Obsidian (vault upload) ────────────────────────────────────────────────

class ObsidianUploadRequest(BaseModel):
    """The frontend reads .md files via the FileSystem API and posts them
    as a single batch. No multipart, no zip — just a list of {path, content}.
    """
    notes: list[dict] = Field(default_factory=list)


@router.post("/obsidian/upload")
async def upload_obsidian_vault(
    body: ObsidianUploadRequest, user: dict = Depends(require_user),
) -> dict:
    from app.services.obsidian_indexer import index_vault
    if not body.notes:
        raise HTTPException(status_code=400, detail="notes list is empty")
    summary = await index_vault(user["email"], body.notes)
    return {"ok": True, **summary}


@router.delete("/obsidian")
async def disconnect_obsidian(user: dict = Depends(require_user)) -> dict:
    from app.services.obsidian_indexer import delete_vault
    await delete_vault(user["email"])
    return {"ok": True}


@router.get("/obsidian/status")
async def obsidian_status(user: dict = Depends(require_user)) -> dict:
    from app.services.obsidian_indexer import get_vault_summary
    summary = await get_vault_summary(user["email"]) or {}
    return {"connected": bool(summary.get("note_count")), **summary}


async def is_obsidian_connected(user_email: str) -> bool:
    if not user_email:
        return False
    row = await collection("obsidian_vaults").find_one({"user_email": user_email}, {"_id": 0})
    return bool(row and row.get("note_count"))


# ─── MCP servers ────────────────────────────────────────────────────────────

class McpAddRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    url: str = Field(..., min_length=8, max_length=500)
    auth_header: str | None = None  # full header value, e.g. "Bearer xyz"


@router.post("/mcp/add")
async def add_mcp_server(body: McpAddRequest, user: dict = Depends(require_user)) -> dict:
    from app.services.mcp_client import McpError, add_server
    try:
        result = await add_server(user["email"], body.name, body.url, body.auth_header)
        return {"ok": True, **result}
    except McpError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/mcp/list")
async def list_mcp_servers(user: dict = Depends(require_user)) -> list[dict]:
    from app.services.mcp_client import list_servers
    return await list_servers(user["email"])


@router.post("/mcp/{server_id}/refresh")
async def refresh_mcp_server(server_id: str, user: dict = Depends(require_user)) -> dict:
    from app.services.mcp_client import McpError, refresh_server
    try:
        tools = await refresh_server(user["email"], server_id)
        return {"ok": True, "tools": tools}
    except McpError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.delete("/mcp/{server_id}")
async def delete_mcp_server(server_id: str, user: dict = Depends(require_user)) -> dict:
    from app.services.mcp_client import delete_server
    await delete_server(user["email"], server_id)
    return {"ok": True}
