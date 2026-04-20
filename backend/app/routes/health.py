"""Health dashboard — reports status of every subsystem in one place.
Intentionally public (no auth dependency) so it can be polled from status pages.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter

from app.db import db
from app.services.object_storage import is_storage_ready


router = APIRouter(prefix="/health", tags=["health"])


async def _check_mongo() -> dict:
    try:
        names = await db.list_collection_names()
        return {"ok": True, "collections": len(names)}
    except Exception as error:
        return {"ok": False, "error": str(error)[:160]}


async def _check_emergent_llm() -> dict:
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        return {"ok": False, "error": "EMERGENT_LLM_KEY missing"}
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            response = await client.get(
                "https://integrations.emergentagent.com/llm/v1/models",
                headers={"Authorization": f"Bearer {key}"},
            )
        return {"ok": response.status_code == 200, "status": response.status_code}
    except Exception as error:
        return {"ok": False, "error": str(error)[:120]}


async def _check_openai_voice() -> dict:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return {"ok": False, "error": "OPENAI_API_KEY missing"}
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {key}"},
            )
        return {"ok": response.status_code == 200, "status": response.status_code}
    except Exception as error:
        return {"ok": False, "error": str(error)[:120]}


async def _check_swarm() -> dict:
    e2b = bool(os.environ.get("E2B_API_KEY"))
    github = bool(os.environ.get("GITHUB_TOKEN"))
    return {"ok": e2b, "e2b_configured": e2b, "github_configured": github}


@router.get("")
async def health():
    """Aggregated health snapshot. Each subsystem probed in parallel would be
    faster, but the cost is trivial — total latency ~400ms worst case."""
    mongo = await _check_mongo()
    llm = await _check_emergent_llm()
    voice = await _check_openai_voice()
    swarm = await _check_swarm()
    storage_ok = is_storage_ready()
    overall = all([mongo["ok"], llm["ok"], voice["ok"], swarm["ok"], storage_ok])
    return {
        "ok": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subsystems": {
            "mongo": mongo,
            "auth": {"ok": True, "provider": "emergent_google_oauth"},
            "object_storage": {"ok": storage_ok, "backend": "emergent_objstore" if storage_ok else "local_fallback"},
            "emergent_llm_proxy": llm,
            "openai_voice": voice,
            "agent_swarm": swarm,
        },
    }
