from __future__ import annotations

from datetime import datetime, timezone
import uuid

from app.db import collection
from app.services.agent_secret_redaction import redact_secrets


async def create_approval_item(session_id: str, user_email: str, action_type: str, prompt: str, resource: str = "") -> dict:
    now = datetime.now(timezone.utc).isoformat()
    doc = redact_secrets({
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "user_email": user_email,
        "action_type": action_type,
        "prompt": prompt,
        "resource": resource,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    })
    await collection("agent_approvals").insert_one(doc)
    return doc
