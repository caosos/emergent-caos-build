"""Authenticated Google API client factory.

Returns a `googleapiclient.discovery.Resource` for any Google service the user
has connected. Handles on-demand refresh of expired access_tokens via the
stored refresh_token, persists the new access_token, and surfaces a clean
"needs reauth" signal if Google revokes us.

REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS,
THIS BREAKS THE AUTH. The original redirect_uri is read from the stored row
because Google's refresh endpoint demands it match.
"""
from __future__ import annotations

import os
from typing import Any, Optional

import httpx

from app.services import token_vault

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GoogleAuthError(Exception):
    """Raised when we cannot mint a valid access_token for the user."""


async def _refresh_access_token(row: dict[str, Any]) -> dict[str, Any]:
    """Use the stored refresh_token to mint a new access_token.

    Returns the freshly-stored row (after persistence). Raises GoogleAuthError
    if Google rejects the refresh — caller should treat as `needs_reauth`.
    """
    user_email = row["user_email"]
    refresh_token = token_vault.decrypt(row.get("encrypted_refresh_token"))
    if not refresh_token:
        await token_vault.mark_needs_reauth(user_email, "google", "no refresh token stored")
        raise GoogleAuthError("no refresh_token — user must reconnect Google")

    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise GoogleAuthError("server missing GOOGLE_OAUTH_CLIENT_ID/SECRET")

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            resp = await http.post(GOOGLE_TOKEN_URL, data=payload)
    except Exception as error:
        raise GoogleAuthError(f"network error refreshing google token: {error}") from error

    if resp.status_code != 200:
        body_preview = (resp.text or "")[:200]
        await token_vault.mark_needs_reauth(
            user_email, "google", f"refresh failed (HTTP {resp.status_code}): {body_preview}"
        )
        raise GoogleAuthError(f"google refresh rejected: {resp.status_code} {body_preview}")

    body = resp.json()
    new_access = body.get("access_token")
    if not new_access:
        raise GoogleAuthError("google refresh returned no access_token")
    new_expires_in = int(body.get("expires_in", 3600))
    # Google sometimes does NOT re-issue a refresh_token on refresh — keep the existing one.
    new_refresh = body.get("refresh_token") or refresh_token

    await token_vault.store_google_token(
        user_email,
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=new_expires_in,
        scopes=row.get("scopes", []),
        google_email=row.get("google_email"),
        redirect_uri=row.get("redirect_uri", ""),
    )
    return await token_vault.get_token_row(user_email, "google") or row


async def get_authenticated_credentials(user_email: str) -> Any:
    """Return a `google.oauth2.credentials.Credentials` for the user.

    On expired tokens, refreshes transparently. On revocation, raises
    GoogleAuthError with a clean message the UI can surface.
    """
    # Lazy import — google libs are heavy; only load when a connector is invoked.
    from google.oauth2.credentials import Credentials  # type: ignore

    row = await token_vault.get_token_row(user_email, "google")
    if not row:
        raise GoogleAuthError("Google not connected")
    if row.get("needs_reauth"):
        raise GoogleAuthError(
            f"Google connection needs re-auth: {row.get('last_error') or 'token revoked'}"
        )

    if token_vault.is_expired(row):
        row = await _refresh_access_token(row)

    access_token = token_vault.decrypt(row.get("encrypted_access_token"))
    if not access_token:
        raise GoogleAuthError("decrypted access_token is empty")

    return Credentials(
        token=access_token,
        refresh_token=token_vault.decrypt(row.get("encrypted_refresh_token")),
        token_uri=GOOGLE_TOKEN_URL,
        client_id=os.environ.get("GOOGLE_OAUTH_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET"),
        scopes=row.get("scopes", []),
    )


async def build_service(user_email: str, service_name: str, version: str) -> Any:
    """Factory: returns an authenticated googleapiclient Resource.

    Examples:
        await build_service(email, "gmail", "v1")
        await build_service(email, "drive", "v3")
        await build_service(email, "docs", "v1")
        await build_service(email, "calendar", "v3")
    """
    from googleapiclient.discovery import build  # type: ignore

    creds = await get_authenticated_credentials(user_email)
    # `cache_discovery=False` avoids a noisy warning + a write to the local
    # filesystem inside the container that we don't need.
    return build(service_name, version, credentials=creds, cache_discovery=False)
