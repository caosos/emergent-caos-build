from __future__ import annotations

from datetime import datetime, timezone

from app.db import collection
from app.schemas.agent_runtime import AgentSessionLedgerRecord
from app.services.agent_secret_redaction import redact_secrets


async def create_agent_session(record: AgentSessionLedgerRecord) -> dict:
    doc = redact_secrets(record.model_dump())
    await collection("agent_sessions").insert_one(doc)
    return doc


async def update_agent_session(session_id: str, changes: dict) -> None:
    safe_changes = redact_secrets(changes)
    safe_changes["updated_at"] = datetime.now(timezone.utc).isoformat()
    await collection("agent_sessions").update_one({"session_id": session_id}, {"$set": safe_changes})
