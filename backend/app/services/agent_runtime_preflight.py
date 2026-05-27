from __future__ import annotations

from app.schemas.agent_runtime import AgentPreflightResult
from app.services.agent_permission_classifier import classify_request_intent
from app.services.agent_runtime_flags import load_agent_runtime_flags, runtime_applies
from app.services.agent_runtime_receipts import build_runtime_receipt


def can_fallback_to_legacy(*, is_side_effect: bool, is_read_only: bool, classification_known: bool) -> bool:
    if not classification_known:
        return False
    if is_side_effect:
        return False
    return is_read_only


async def run_agent_preflight(*, user_text: str, is_admin_user: bool, session_id: str = "") -> AgentPreflightResult:
    flags = load_agent_runtime_flags()
    if not runtime_applies(is_admin_user, flags):
        return AgentPreflightResult(
            allow_execute=True,
            is_side_effect=False,
            fallback_allowed=False,
            reason="runtime_not_applicable",
            receipt_fragment=build_runtime_receipt(session_id=session_id or "n/a", module="agent_runtime_preflight", action="skip", status="disabled"),
        )

    decision = classify_request_intent(user_text)
    classification_known = decision.action_type != "unknown"
    is_side_effect = bool(decision.approval_required)

    if is_side_effect:
        return AgentPreflightResult(
            allow_execute=False,
            requires_approval=True,
            is_side_effect=True,
            fallback_allowed=False,
            classification_known=classification_known,
            reason=decision.reason,
            receipt_fragment=build_runtime_receipt(
                session_id=session_id or "n/a",
                module="agent_runtime_preflight",
                action="permission_scan",
                status="awaiting_approval",
                input_summary=user_text[:180],
                output_summary=decision.action_type,
                approval_required=True,
            ),
        )

    return AgentPreflightResult(
        allow_execute=True,
        requires_approval=False,
        is_side_effect=False,
        fallback_allowed=can_fallback_to_legacy(
            is_side_effect=is_side_effect,
            is_read_only=decision.is_read_only,
            classification_known=classification_known,
        ),
        classification_known=classification_known,
        reason=decision.reason,
        receipt_fragment=build_runtime_receipt(
            session_id=session_id or "n/a",
            module="agent_runtime_preflight",
            action="permission_scan",
            status="allowed",
            input_summary=user_text[:180],
            output_summary=decision.action_type,
        ),
    )
