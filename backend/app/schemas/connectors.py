"""Pydantic models for Connector hub state and OAuth flows.

These are the user-facing shapes returned by `/api/connectors/*` endpoints.
Token bytes never leave the backend — responses only carry connection state,
masked previews, and metadata.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ConnectorState(BaseModel):
    """Single connector's status as the UI sees it.

    Stays generic enough to cover Google (one row, multiple scopes), Slack,
    Notion, MCP servers — every card in the hub renders from one of these.
    """
    provider: str  # "google" | "github" | "slack" | "mcp" | ...
    label: str  # human-readable display name
    connected: bool
    masked_identity: Optional[str] = None  # e.g. "user@gmail.com" or "ghp_…xK2"
    scopes: list[str] = Field(default_factory=list)
    needs_reauth: bool = False
    last_error: Optional[str] = None
    updated_at: Optional[str] = None


class GoogleStartResponse(BaseModel):
    """Returned by POST /connectors/google/start — the URL the popup opens."""
    auth_url: str
    state: str


class GoogleCallbackRequest(BaseModel):
    """Frontend forwards { code, state } here from the popup.

    REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS,
    THIS BREAKS THE AUTH. The redirect URI is built from `window.location.origin`
    on the frontend and matched server-side from the request.
    """
    code: str
    state: str
    redirect_uri: str  # echoed back so backend uses the SAME URI as the popup


class GoogleCallbackResponse(BaseModel):
    ok: bool
    email: Optional[str] = None  # the connected Google account
    scopes: list[str] = Field(default_factory=list)
    error: Optional[str] = None


class ConnectorAuditEntry(BaseModel):
    """Single row in the per-connector activity log surfaced in the UI."""
    provider: str
    tool: str  # e.g. "gmail_search"
    success: bool
    summary: str  # human-readable one-liner
    latency_ms: int
    created_at: str
