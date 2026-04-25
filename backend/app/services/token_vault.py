"""Encrypted token vault for connector OAuth tokens.

DESIGN
======
- Every connector token (access_token + refresh_token) is encrypted at rest
  with Fernet using `CONNECTOR_TOKEN_FERNET_KEY` from env.
- Storage: MongoDB collection `connector_tokens`, keyed on (user_email, provider).
- Refresh strategy: on demand. When a caller asks for an access_token and the
  stored one is expired (or expires within 60s), we use the refresh_token to
  obtain a fresh access_token from Google, persist it, and return it. No
  background worker — refreshes only happen when there's actual API traffic.
- If the refresh itself fails (token revoked on Google's side, network error,
  etc.) we mark the row `needs_reauth=True` so the UI surfaces a "reconnect"
  button on the card.

REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS,
THIS BREAKS THE AUTH. The redirect URI is supplied by the frontend at OAuth
start time and reused at refresh time (Google requires the original).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from cryptography.fernet import Fernet, InvalidToken

from app.db import collection

_REFRESH_BUFFER_SECONDS = 60


def _fernet() -> Fernet:
    key = os.environ.get("CONNECTOR_TOKEN_FERNET_KEY")
    if not key:
        raise RuntimeError(
            "CONNECTOR_TOKEN_FERNET_KEY missing from env — connector tokens "
            "cannot be encrypted/decrypted. Set it before any connector flow runs."
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plaintext: str) -> bytes:
    """Encrypt a token string. Returns bytes safe to store as MongoDB Binary."""
    if plaintext is None:
        return b""
    return _fernet().encrypt(plaintext.encode("utf-8"))


def decrypt(ciphertext: bytes | None) -> Optional[str]:
    """Decrypt to plaintext string. Returns None if input is empty.
    Raises InvalidToken if ciphertext is corrupt or wrong key.
    """
    if not ciphertext:
        return None
    return _fernet().decrypt(ciphertext).decode("utf-8")


async def store_google_token(
    user_email: str,
    *,
    access_token: str,
    refresh_token: Optional[str],
    expires_in: int,
    scopes: list[str],
    google_email: Optional[str],
    redirect_uri: str,
) -> None:
    """Upsert the user's Google connector tokens (encrypted).

    `expires_in` is seconds-from-now per Google's OAuth2 response.
    `redirect_uri` is persisted because Google requires the same URI on
    refresh as was used on the initial code-exchange.
    """
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()
    encrypted_access = encrypt(access_token)
    encrypted_refresh = encrypt(refresh_token) if refresh_token else b""
    now_iso = datetime.now(timezone.utc).isoformat()
    await collection("connector_tokens").update_one(
        {"user_email": user_email, "provider": "google"},
        {
            "$set": {
                "user_email": user_email,
                "provider": "google",
                "encrypted_access_token": encrypted_access,
                "encrypted_refresh_token": encrypted_refresh,
                "expires_at": expires_at,
                "scopes": scopes,
                "google_email": google_email,
                "redirect_uri": redirect_uri,
                "needs_reauth": False,
                "last_error": None,
                "updated_at": now_iso,
            },
            "$setOnInsert": {"created_at": now_iso},
        },
        upsert=True,
    )


async def get_token_row(user_email: str, provider: str) -> Optional[dict[str, Any]]:
    """Fetch the raw stored row for a user+provider. _id excluded."""
    if not user_email or not provider:
        return None
    return await collection("connector_tokens").find_one(
        {"user_email": user_email, "provider": provider}, {"_id": 0}
    )


async def mark_needs_reauth(user_email: str, provider: str, reason: str) -> None:
    await collection("connector_tokens").update_one(
        {"user_email": user_email, "provider": provider},
        {"$set": {"needs_reauth": True, "last_error": (reason or "")[:240]}},
    )


async def delete_token(user_email: str, provider: str) -> None:
    """Hard-delete a connector token row. Caller is responsible for any
    upstream revocation (e.g. POST to Google's /revoke endpoint).
    """
    await collection("connector_tokens").delete_one(
        {"user_email": user_email, "provider": provider}
    )


def is_expired(row: dict[str, Any]) -> bool:
    """True if the access_token has expired (or expires within the buffer)."""
    expires_at_iso = row.get("expires_at")
    if not expires_at_iso:
        return True
    try:
        expires_at = datetime.fromisoformat(expires_at_iso)
    except Exception:
        return True
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) + timedelta(seconds=_REFRESH_BUFFER_SECONDS) >= expires_at
