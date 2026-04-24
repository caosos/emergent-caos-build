"""Structured error logging — everything unexpected that happens in the chat
pipeline (or any other wrapped service call) ends up as a row in `error_log`
so admins can see real backend failures, not just user-filed bug tickets.
"""
from __future__ import annotations

import logging
import traceback
from datetime import datetime, timezone
from typing import Any

from app.db import collection

logger = logging.getLogger(__name__)

# Soft cap to avoid runaway collection growth. If we exceed this we'd need
# a TTL index; tracked in PRD.
MAX_LOG_ROWS = 50_000


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _classify(error: Exception) -> str:
    """Rough bucket for the 'Error Types Breakdown' chart."""
    name = type(error).__name__.lower()
    if "timeout" in name:
        return "timeout"
    if "valid" in name or "pydantic" in name:
        return "validation"
    if "auth" in name or "forbidden" in name or "unauthorized" in name:
        return "auth"
    if "connection" in name or "network" in name or "httpx" in name or "httperror" in name:
        return "network"
    if "key" in name and "error" in name:
        return "missing_key"
    if "rate" in name:
        return "rate_limited"
    return "server_error"


async def log_error(
    *,
    source: str,
    error: Exception,
    context: dict[str, Any] | None = None,
    user_email: str | None = None,
) -> None:
    """Persist an error row. Never raises — logging must not mask the real
    problem. Call from within a general try/except inside critical handlers.
    """
    try:
        doc = {
            "id": f"err_{_now_iso()}_{hash((source, str(error))) & 0xFFFF:04x}",
            "source": source,                   # e.g. "chat_pipeline", "voice_transcribe"
            "error_type": _classify(error),
            "error_message": str(error)[:600],
            "error_class": type(error).__name__,
            "traceback": traceback.format_exc()[:3000],
            "context": context or {},
            "user_email": user_email,
            "created_at": _now_iso(),
        }
        await collection("error_log").insert_one(doc)
    except Exception as persist_err:  # pragma: no cover — best-effort
        logger.exception("error_log persist failed: %s", persist_err)


async def get_error_stats() -> dict[str, Any]:
    """Aggregate counts for the admin dashboard Errors tab."""
    from datetime import timedelta
    col = collection("error_log")
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc).isoformat()
    week_cutoff = (now - timedelta(days=7)).isoformat()
    total = await col.count_documents({})
    this_week = await col.count_documents({"created_at": {"$gte": week_cutoff}})
    today = await col.count_documents({"created_at": {"$gte": today_start}})
    by_type_rows = await col.aggregate([
        {"$group": {"_id": "$error_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 12},
    ]).to_list(12)
    by_type = {row["_id"] or "unknown": row["count"] for row in by_type_rows}
    return {
        "total_logged": total,
        "this_week": this_week,
        "today": today,
        "by_type": by_type,
    }


async def list_recent_errors(limit: int = 50) -> list[dict[str, Any]]:
    """Recent errors for a future 'detail' view. Excludes tracebacks by default."""
    cursor = collection("error_log").find(
        {},
        {"_id": 0, "traceback": 0},
    ).sort("created_at", -1).limit(limit)
    return await cursor.to_list(limit)
