from __future__ import annotations

from datetime import datetime, timezone
import uuid

from app.services.agent_secret_redaction import redact_secrets


def build_runtime_receipt(*, session_id: str, module: str, action: str, status: str, input_summary: str = "", output_summary: str = "", approval_required: bool = False, error_details: dict | None = None, duration_ms: int | None = None) -> dict:
    return redact_secrets({
        "receipt_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "module": module,
        "action": action,
        "input_summary": input_summary,
        "output_summary": output_summary,
        "status": status,
        "approval_required": approval_required,
        "error_details": error_details or {},
        "duration_ms": duration_ms,
    })
