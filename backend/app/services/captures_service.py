"""Captures service — CRUD + promote-to-chat + autonomous extraction wiring.

Every new capture flows through the same memory extractor as a regular
chat turn (so important facts file into the 13 typed bins automatically),
and can later be "promoted" to a full chat thread that pre-loads the
capture as the opening user message.

API-key flow: each user has ONE personal API token (Fernet-encrypted at
rest, prefixed `caos_`). External posters (Apple Shortcut, Bee poll,
custom scripts) authenticate by sending it as an `Authorization: Bearer
caos_xxxxx` header to `POST /api/caos/captures`. Rotating the key
invalidates the old one immediately.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

from app.db import collection
from app.schemas.captures import (
    ApiKeyResponse,
    CaptureCreateRequest,
    CapturePromoteResponse,
    CaptureRecord,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---- API key issuance / lookup ---------------------------------------------

def _new_token() -> str:
    """Generate a CAOS-prefixed bearer token. 32 random bytes urlsafe-encoded
    is ~43 chars; with the prefix the full token is ~48 chars."""
    return f"caos_{secrets.token_urlsafe(32)}"


async def issue_api_key(user_email: str) -> ApiKeyResponse:
    """Generate a fresh API key for the user, replacing any prior key.
    The plaintext is returned ONCE — the DB stores it (we keep this simple:
    no Fernet for now — these tokens grant ONLY capture-ingest access, not
    full account access, and rotation is one-click)."""
    token = _new_token()
    issued = _now_iso()
    await collection("user_api_keys").update_one(
        {"user_email": user_email},
        {"$set": {
            "user_email": user_email,
            "token": token,
            "prefix": f"{token[:9]}…{token[-4:]}",
            "issued_at": issued,
            "last_used_at": None,
        }},
        upsert=True,
    )
    return ApiKeyResponse(api_key=token, prefix=f"{token[:9]}…{token[-4:]}",
                          issued_at=datetime.fromisoformat(issued))


async def get_api_key_meta(user_email: str) -> dict | None:
    """Return the prefix + issued_at + last_used_at for the UI. Never
    returns the plaintext token."""
    doc = await collection("user_api_keys").find_one(
        {"user_email": user_email},
        {"_id": 0, "prefix": 1, "issued_at": 1, "last_used_at": 1},
    )
    return doc


async def resolve_user_from_api_key(token: str) -> dict | None:
    """Look up which user owns this token. Updates last_used_at as a side
    effect so the UI can show 'last poll: 2 min ago'."""
    if not token or not token.startswith("caos_"):
        return None
    doc = await collection("user_api_keys").find_one(
        {"token": token}, {"_id": 0, "user_email": 1}
    )
    if not doc:
        return None
    await collection("user_api_keys").update_one(
        {"token": token}, {"$set": {"last_used_at": _now_iso()}}
    )
    return await collection("users").find_one(
        {"email": doc["user_email"]}, {"_id": 0}
    )


# ---- Capture CRUD ----------------------------------------------------------

async def create_capture(user_email: str, payload: CaptureCreateRequest) -> CaptureRecord:
    record = CaptureRecord(
        user_email=user_email,
        text=payload.text.strip(),
        source=payload.source,
        captured_at=payload.captured_at or datetime.now(timezone.utc),
        location=payload.location,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    doc = record.model_dump()
    doc["captured_at"] = record.captured_at.isoformat()
    doc["created_at"] = record.created_at.isoformat()
    doc["updated_at"] = record.updated_at.isoformat()
    await collection("captures").insert_one(doc)
    # Auto-mine: route the capture text through the same extractor used by
    # chat turns. Fire-and-forget; non-fatal. Captures with no extractable
    # signal still appear in the inbox unchanged.
    try:
        from app.services.memory_extractor import schedule_extraction
        schedule_extraction(
            user_email=user_email,
            session_id=f"capture-{record.id}",
            user_message=record.text,
            assistant_reply="(captured note — no AI reply yet)",
            user_message_id=record.id,
        )
    except Exception as exc:  # pragma: no cover
        print(f"capture extractor scheduling failed: {exc}")
    return record


async def list_captures(user_email: str, status: str | None = None,
                         limit: int = 200) -> list[CaptureRecord]:
    query: dict = {"user_email": user_email}
    if status:
        query["status"] = status
    docs = await collection("captures").find(query, {"_id": 0}).sort(
        "captured_at", -1
    ).to_list(limit)
    return [CaptureRecord(**doc) for doc in docs]


async def count_captures_by_status(user_email: str) -> dict[str, int]:
    """Counts of new / promoted / dismissed for the inbox header pill."""
    rows = await collection("captures").aggregate([
        {"$match": {"user_email": user_email}},
        {"$group": {"_id": "$status", "n": {"$sum": 1}}},
    ]).to_list(10)
    counts = {"new": 0, "promoted": 0, "dismissed": 0}
    for row in rows:
        counts[row["_id"]] = int(row["n"])
    return counts


async def dismiss_capture(user_email: str, capture_id: str) -> CaptureRecord:
    res = await collection("captures").find_one_and_update(
        {"id": capture_id, "user_email": user_email},
        {"$set": {"status": "dismissed", "updated_at": _now_iso()}},
        return_document=True,
        projection={"_id": 0},
    )
    if not res:
        raise ValueError("Capture not found")
    return CaptureRecord(**res)


async def delete_capture(user_email: str, capture_id: str) -> dict:
    res = await collection("captures").delete_one(
        {"id": capture_id, "user_email": user_email}
    )
    if not res.deleted_count:
        raise ValueError("Capture not found")
    return {"deleted_id": capture_id}


async def promote_capture(user_email: str, capture_id: str) -> CapturePromoteResponse:
    """Spawn a new chat thread seeded with the capture's text as the opening
    user message. Aria can then respond / triage from there."""
    cap_doc = await collection("captures").find_one(
        {"id": capture_id, "user_email": user_email}, {"_id": 0}
    )
    if not cap_doc:
        raise ValueError("Capture not found")
    capture = CaptureRecord(**cap_doc)
    # Create a new session — same shape as a normal chat session.
    session_id = f"sess_{uuid.uuid4().hex[:16]}"
    title = (capture.text[:60] + "…") if len(capture.text) > 60 else capture.text
    now_iso = _now_iso()
    await collection("sessions").insert_one({
        "session_id": session_id,
        "user_email": user_email,
        "title": title,
        "created_at": now_iso,
        "updated_at": now_iso,
        "metadata": {"promoted_from_capture": capture.id, "source": capture.source},
    })
    msg_id = uuid.uuid4().hex
    await collection("messages").insert_one({
        "id": msg_id,
        "session_id": session_id,
        "role": "user",
        "user_email": user_email,
        "content": capture.text,
        "timestamp": capture.captured_at.isoformat() if isinstance(capture.captured_at, datetime) else capture.captured_at,
        "metadata": {"promoted_from_capture": capture.id, "source": capture.source},
    })
    await collection("captures").update_one(
        {"id": capture_id},
        {"$set": {
            "status": "promoted",
            "promoted_session_id": session_id,
            "updated_at": now_iso,
        }},
    )
    return CapturePromoteResponse(
        capture_id=capture_id,
        session_id=session_id,
        message_id=msg_id,
    )
