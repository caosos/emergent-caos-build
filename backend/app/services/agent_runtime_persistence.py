from __future__ import annotations

from app.schemas.agent_runtime import AgentPreflightResult, AgentRuntimeFlags, AgentSessionLedgerRecord
from app.services.agent_approval_queue import create_approval_item
from app.services.agent_secret_redaction import redact_secrets
from app.services.agent_session_ledger import create_agent_session, update_agent_session


def _status_for(preflight: AgentPreflightResult) -> str:
    if preflight.allow_execute and preflight.classification_known:
        return "allowed"
    if not preflight.classification_known:
        return "blocked_unknown"
    if preflight.requires_approval or preflight.is_side_effect or (not preflight.allow_execute):
        return "blocked_approval_required"
    return "blocked"


def _action_type_for(preflight: AgentPreflightResult) -> str:
    fragment = preflight.receipt_fragment or {}
    action = fragment.get("output_summary")
    if action and isinstance(action, str):
        return action
    if not preflight.classification_known:
        return "unknown"
    return "read_only"


async def persist_runtime_preflight_outcome(*, flags: AgentRuntimeFlags, preflight: AgentPreflightResult, payload_session_id: str, chat_session_id: str, user_email: str, user_id: str | None, user_request: str) -> None:
    if not flags.enabled or not flags.session_ledger_enabled:
        return

    receipt_fragment = redact_secrets(preflight.receipt_fragment or {})
    record = AgentSessionLedgerRecord(
        session_id=payload_session_id,
        chat_session_id=chat_session_id,
        user_email=user_email,
        user_id=user_id,
        user_request=user_request,
        interpreted_intent=str(receipt_fragment.get("output_summary") or ""),
        status=_status_for(preflight),
        approval_required=bool(preflight.requires_approval or not preflight.classification_known or preflight.is_side_effect or (not preflight.allow_execute)),
        approval_status="pending" if (preflight.requires_approval or not preflight.classification_known or preflight.is_side_effect or (not preflight.allow_execute)) else "not_required",
    )
    await create_agent_session(record)

    if flags.runtime_receipts_enabled and receipt_fragment:
        await update_agent_session(payload_session_id, {"receipts": [receipt_fragment]})

    if (preflight.requires_approval or not preflight.classification_known or preflight.is_side_effect or (not preflight.allow_execute)) and flags.approval_persistence_enabled:
        await create_approval_item(
            session_id=payload_session_id,
            user_email=user_email,
            action_type=_action_type_for(preflight),
            prompt=user_request,
            resource="",
        )


async def persist_runtime_preflight_error(*, flags: AgentRuntimeFlags, payload_session_id: str, chat_session_id: str, user_email: str, user_id: str | None, user_request: str, error_detail: str) -> None:
    if not flags.enabled or not flags.session_ledger_enabled:
        return

    receipt = redact_secrets({"error": "agent_runtime_preflight_failed", "detail": str(error_detail)[:200]})
    record = AgentSessionLedgerRecord(
        session_id=payload_session_id,
        chat_session_id=chat_session_id,
        user_email=user_email,
        user_id=user_id,
        user_request=user_request,
        interpreted_intent="runtime_error",
        status="error",
        error=receipt,
        approval_required=True,
        approval_status="error",
    )
    await create_agent_session(record)

    if flags.runtime_receipts_enabled:
        await update_agent_session(payload_session_id, {"receipts": [receipt]})
