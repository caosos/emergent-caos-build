"""Quick Capture schema — voice notes / text drafts dumped from a phone,
pendant, or any external source. Each capture is a sticky-note in the
user's inbox, optionally promotable to a full chat thread.

Capture sources we know about today:
  - manual          (typed in the CAOS Quick Capture form)
  - shortcut        (iOS / Android share sheet, Siri Shortcut)
  - bee_pendant     (Phase 2: Bee API poll job)
  - api             (any external script POSTing with the user's API key)
  - voice           (Composer mic STT, dumped to inbox without sending to chat)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


CaptureSource = Literal[
    "manual",
    "shortcut",
    "bee_pendant",
    "api",
    "voice",
]

CaptureStatus = Literal["new", "promoted", "dismissed"]


class CaptureRecord(BaseModel):
    """One sticky-note in the user's Quick Capture inbox."""
    id: str = Field(default_factory=lambda: f"cap_{uuid.uuid4().hex[:14]}")
    user_email: str
    text: str  # the dictated / typed content
    source: CaptureSource = "manual"
    status: CaptureStatus = "new"
    # Optional context — pendant / phone may stamp these
    captured_at: datetime = Field(default_factory=_utc_now)  # WHEN the user said it
    location: str | None = None  # human-readable place ("car", "warehouse")
    latitude: float | None = None
    longitude: float | None = None
    # Wiring to the rest of CAOS
    promoted_session_id: str | None = None  # set when user promotes to a chat
    atoms_extracted: int = 0  # how many memory atoms we filed from this
    # Bookkeeping
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class CaptureCreateRequest(BaseModel):
    """Payload for `POST /api/caos/captures` from manual entry, Apple Shortcut,
    Bee poll job, or any external script."""
    text: str = Field(..., min_length=1, max_length=4000)
    source: CaptureSource = "manual"
    captured_at: datetime | None = None
    location: str | None = Field(default=None, max_length=120)
    latitude: float | None = None
    longitude: float | None = None


class CaptureListResponse(BaseModel):
    user_email: str
    captures: list[CaptureRecord]
    counts: dict[str, int]  # by status


class CapturePromoteResponse(BaseModel):
    capture_id: str
    session_id: str
    message_id: str


class ApiKeyResponse(BaseModel):
    """Returned when user generates / rotates their personal API key. The
    plaintext token is only shown ONCE — afterward only the prefix and
    issued_at are queryable."""
    api_key: str  # plaintext, shown once
    prefix: str   # last-4 + first-4 for the UI display
    issued_at: datetime
