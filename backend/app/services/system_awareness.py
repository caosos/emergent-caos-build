"""System awareness helper — gives Aria a compact snapshot of system health
and the user's outstanding support tickets so she can mention issues honestly.

Cached for 60s so we don't hammer Mongo / the LLM proxy on every chat turn.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from app.db import collection
from app.routes.health import (
    _check_emergent_llm,
    _check_mongo,
    _check_openai_voice,
    _check_swarm,
)
from app.services.object_storage import is_storage_ready

_CACHE: dict[str, Any] = {"t": 0.0, "data": None}
_TTL_SECONDS = 60.0


async def _refresh_health() -> dict:
    # Run all 4 health probes in parallel — was 4 sequential httpx calls
    # (up to 24s if all timed out). Now bounded by the slowest single probe
    # (max 6s timeout). Saves ~300ms-2s on every cache miss in healthy state.
    mongo, llm, voice, swarm = await asyncio.gather(
        _check_mongo(), _check_emergent_llm(), _check_openai_voice(), _check_swarm(),
        return_exceptions=True,
    )
    storage_ok = is_storage_ready()
    def _ok(result):
        return isinstance(result, dict) and bool(result.get("ok", False))
    return {
        "mongo": _ok(mongo),
        "llm_proxy": _ok(llm),
        "openai_voice": _ok(voice),
        "e2b_swarm": _ok(swarm),
        "object_storage": storage_ok,
    }


async def _cached_health() -> dict:
    now = time.monotonic()
    if _CACHE["data"] is None or now - _CACHE["t"] > _TTL_SECONDS:
        try:
            _CACHE["data"] = await _refresh_health()
            _CACHE["t"] = now
        except Exception as error:  # never block a chat turn on health probes
            _CACHE["data"] = {"error": str(error)[:120]}
            _CACHE["t"] = now
    return _CACHE["data"] or {}


async def build_awareness_block(user_email: str) -> str:
    """Return a compact multiline system-status block for the prompt."""
    health = await _cached_health()
    bits: list[str] = []
    bits.append("System health (live snapshot, cached 60s):")
    for name, ok in health.items():
        bits.append(f"- {name}: {'OK' if ok else 'DEGRADED'}")
    try:
        open_count = await collection("support_tickets").count_documents({
            "user_email": user_email,
            "status": {"$in": ["open", "in_progress"]},
        })
    except Exception:
        open_count = 0
    bits.append(f"User's open support tickets: {open_count}")
    return "\n".join(bits)
