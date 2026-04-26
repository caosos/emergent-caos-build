"""Memory backfill — global, per-user, idempotent.

Mines every past user message across every session for memory atoms,
filing them into the 13 typed bins. Each message is stamped in
`memory_extraction_log` so subsequent runs skip what's already been
mined and only process truly new content.

Two entry paths:

1. **Full backfill** — `backfill_user_memories(user_email)`: scans ALL
   the user's messages globally. Used by the explicit "Mine past
   conversations" button in the Memory Console.

2. **Targeted session backfill** — `backfill_session_memories(...)`:
   scans only the messages in one session. Used by the auto-incremental
   path that fires every time the user opens a session (so by the time
   they look at the Memory Console, atoms from the session are already
   visible).

Both paths share the same per-message extractor + log stamping, so
idempotency is preserved across them and across the per-turn extractor
in `chat_pipeline`.

Job tracking lives in-memory (per-process). For our single-pod deploy
that's fine; if/when we shard, swap to a redis/db-backed job state.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from app.db import collection
from app.services.memory_extractor import (
    EXTRACTION_LOG_COLLECTION,
    extract_memories_from_turn,
    is_message_mined,
)


# Tuning knobs. Backfill should never burn the LLM budget — keep these conservative.
BACKFILL_MAX_PER_RUN = 200          # absolute cap per run; user can re-run for more
BACKFILL_CONCURRENCY = 3            # parallel extractor calls (Gemini Flash handles this fine)
BACKFILL_MIN_USER_MSG_CHARS = 30    # skip "ok", "yes", "thanks" — no signal
BACKFILL_RATE_LIMIT_SLEEP_S = 0.05  # 50ms between waves to be a good API citizen


# Per-process job tracking. Keyed by job_id; a job represents one backfill run.
_jobs: dict[str, dict[str, Any]] = {}


def _new_job(user_email: str, scope: str) -> str:
    job_id = uuid.uuid4().hex[:16]
    _jobs[job_id] = {
        "job_id": job_id,
        "user_email": user_email,
        "scope": scope,                # "user" or session_id
        "status": "queued",            # queued | running | completed | failed
        "started_at": time.time(),
        "finished_at": None,
        "processed": 0,
        "atoms_created": 0,
        "skipped_already_mined": 0,
        "skipped_low_signal": 0,
        "total_candidates": 0,
        "error": None,
    }
    return job_id


def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)


def get_active_job_for(user_email: str) -> dict | None:
    """If the user has a backfill currently running, return it. Used by the
    UI to avoid kicking off duplicate jobs while one is still going."""
    for job in _jobs.values():
        if job["user_email"] == user_email and job["status"] in {"queued", "running"}:
            return job
    return None


async def count_unmined_for_user(user_email: str, session_id: str | None = None) -> int:
    """Cheap pre-flight count for the UI button label.
    Returns how many candidate user messages exist that haven't been mined.
    Optionally scope to one `session_id` for the per-session pulse.

    Mirrors the same filters the backfill uses (≥30 chars) so the UI count
    matches what the job will actually process — nothing more annoying than
    a button saying '1 unmined' that does nothing when clicked.
    """
    if session_id:
        session_ids = [session_id]
    else:
        session_ids = [
            doc["session_id"] async for doc in collection("sessions").find(
                {"user_email": user_email}, {"_id": 0, "session_id": 1}
            )
        ]
    if not session_ids:
        return 0
    # Count user messages with content ≥ BACKFILL_MIN_USER_MSG_CHARS.
    pipeline = [
        {"$match": {"session_id": {"$in": session_ids}, "role": "user"}},
        {"$project": {"_id": 0, "id": 1, "len": {"$strLenCP": {"$ifNull": ["$content", ""]}}}},
        {"$match": {"len": {"$gte": BACKFILL_MIN_USER_MSG_CHARS}}},
        {"$count": "n"},
    ]
    rows = await collection("messages").aggregate(pipeline).to_list(1)
    total_user_msgs = int(rows[0]["n"]) if rows else 0
    log_filter = {"user_email": user_email}
    if session_id:
        log_filter["session_id"] = session_id
    mined = await collection(EXTRACTION_LOG_COLLECTION).count_documents(log_filter)
    return max(0, total_user_msgs - mined)


async def _candidate_messages_for_user(user_email: str, *, session_id: str | None = None,
                                        limit: int = BACKFILL_MAX_PER_RUN) -> list[dict]:
    """Resolve ordered (user_message, optional_assistant_reply) pairs for the
    user (across every session OR just one), filtering out short/mined ones.

    Returns a list of dicts ready for the extractor:
      [{user_msg_id, user_msg_content, session_id, assistant_reply_content}, ...]
    """
    if session_id:
        session_ids = [session_id]
    else:
        session_ids = [
            doc["session_id"] async for doc in collection("sessions").find(
                {"user_email": user_email}, {"_id": 0, "session_id": 1}
            )
        ]
    if not session_ids:
        return []

    # Fetch up to a generous slice of messages per session, sorted by created_at.
    all_msgs: list[dict] = []
    async for doc in collection("messages").find(
        {"session_id": {"$in": session_ids}},
        {"_id": 0, "id": 1, "session_id": 1, "role": 1, "content": 1, "timestamp": 1},
    ).sort([("session_id", 1), ("timestamp", 1)]):
        all_msgs.append(doc)

    # Walk the timeline, pairing each user message with the next assistant
    # reply in the same session (if present).
    candidates: list[dict] = []
    for i, msg in enumerate(all_msgs):
        if msg.get("role") != "user":
            continue
        content = (msg.get("content") or "").strip()
        if len(content) < BACKFILL_MIN_USER_MSG_CHARS:
            continue
        msg_id = msg.get("id")
        if not msg_id:
            continue
        # Look ahead for a same-session assistant reply.
        assistant_reply = ""
        for nxt in all_msgs[i + 1:i + 6]:
            if nxt.get("session_id") != msg.get("session_id"):
                break
            if nxt.get("role") == "assistant" and nxt.get("content"):
                assistant_reply = nxt["content"]
                break
        candidates.append({
            "user_msg_id": msg_id,
            "user_msg_content": content,
            "session_id": msg["session_id"],
            "assistant_reply_content": assistant_reply,
        })
        if len(candidates) >= limit * 2:
            # We over-fetch by 2x because mined ones get filtered out next.
            break
    return candidates


async def _run_job(job_id: str, *, session_id: str | None = None) -> None:
    """Worker coroutine. Pulls candidates, filters mined, runs extractor with
    bounded concurrency, updates the job dict in place."""
    job = _jobs[job_id]
    job["status"] = "running"
    try:
        candidates = await _candidate_messages_for_user(
            job["user_email"], session_id=session_id, limit=BACKFILL_MAX_PER_RUN,
        )
        # Filter already-mined upfront (cheap DB lookup beats LLM call).
        unmined: list[dict] = []
        for cand in candidates:
            if await is_message_mined(job["user_email"], cand["user_msg_id"]):
                job["skipped_already_mined"] += 1
                continue
            unmined.append(cand)
            if len(unmined) >= BACKFILL_MAX_PER_RUN:
                break
        job["total_candidates"] = len(unmined)

        sem = asyncio.Semaphore(BACKFILL_CONCURRENCY)

        async def process(cand: dict) -> None:
            async with sem:
                try:
                    created = await extract_memories_from_turn(
                        user_email=job["user_email"],
                        session_id=cand["session_id"],
                        user_message=cand["user_msg_content"],
                        assistant_reply=cand["assistant_reply_content"] or "(no recorded reply)",
                        user_message_id=cand["user_msg_id"],
                    )
                    job["atoms_created"] += len(created)
                except Exception as exc:  # pragma: no cover
                    print(f"backfill: per-message extract failed: {exc}")
                finally:
                    job["processed"] += 1
                    await asyncio.sleep(BACKFILL_RATE_LIMIT_SLEEP_S)

        await asyncio.gather(*(process(c) for c in unmined))
        job["status"] = "completed"
    except Exception as exc:  # pragma: no cover
        job["status"] = "failed"
        job["error"] = str(exc)
        print(f"backfill: job {job_id} failed: {exc}")
    finally:
        job["finished_at"] = time.time()


def schedule_full_backfill(user_email: str) -> dict:
    """Kick off a full per-user backfill. Returns the job dict immediately
    so the UI can poll. Skips if a job is already running for this user."""
    existing = get_active_job_for(user_email)
    if existing:
        return existing
    job_id = _new_job(user_email, scope="user")
    asyncio.create_task(_run_job(job_id, session_id=None))
    return _jobs[job_id]


def schedule_session_backfill(user_email: str, session_id: str) -> dict:
    """Targeted: only mine messages in one session. Used by the auto-trigger
    on session-load. Idempotent — if there's nothing unmined it's a no-op."""
    existing = get_active_job_for(user_email)
    if existing:
        return existing
    job_id = _new_job(user_email, scope=f"session:{session_id}")
    asyncio.create_task(_run_job(job_id, session_id=session_id))
    return _jobs[job_id]
