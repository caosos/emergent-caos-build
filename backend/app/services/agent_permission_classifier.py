from __future__ import annotations

import re

from app.schemas.agent_permissions import PermissionClassification
from app.services.agent_secret_redaction import redact_secrets_text

_SIDE_EFFECT_RULES: list[tuple[str, str, str, str]] = [
    ("modify_memory", r"\b(save memory|write memory|remember this|store this)\b", "high", "memory"),
    ("send_email_or_message", r"\b(send email|email .* to |send message|text .* to|dm .* to)\b", "high", "communications"),
    ("calendar_change", r"\b(create calendar|update calendar|delete calendar|schedule meeting)\b", "high", "calendar"),
    ("file_repo_write", r"\b(write file|delete file|edit file|modify repo|change code|edit code|delete code)\b", "high", "files/repo"),
    ("push_or_pr", r"\b(push commit|create pr|open pull request|merge pr)\b", "critical", "repository"),
    ("credential_sensitive", r"\b(use api key|use credential|use token|login as|authenticate with)\b", "high", "credentials"),
    ("system_config", r"\b(change system config|restart service|reboot|edit env)\b", "critical", "system"),
    ("outside_contact", r"\b(contact customer|contact user|reach out to|notify .* externally)\b", "high", "external users"),
    ("purchase_payment", r"\b(buy|purchase|pay\b|charge card|invoice payment)\b", "critical", "payments"),
]

_READ_ONLY_RX = re.compile(r"\b(check|inspect|review|analy[sz]e|report|tell me what needs attention|read-only|status)\b", re.I)


def classify_request_intent(user_text: str) -> PermissionClassification:
    text = (user_text or "").strip().lower()
    if not text:
        return PermissionClassification(
            action_type="unknown",
            risk_level="medium",
            reason="empty_request",
            approval_required=True,
            is_read_only=False,
            confidence=0.0,
        )

    for action_type, pattern, risk, resource in _SIDE_EFFECT_RULES:
        if re.search(pattern, text, re.I):
            return PermissionClassification(
                action_type=action_type,
                risk_level=risk,
                reason=f"matched:{action_type}",
                proposed_change=redact_secrets_text(text[:220]),
                affected_resource=resource,
                approval_required=True,
                approval_prompt=f"Approve {action_type} affecting {resource}?",
                is_read_only=False,
                confidence=0.9,
            )

    if _READ_ONLY_RX.search(text):
        return PermissionClassification(
            action_type="read_only",
            risk_level="low",
            reason="inspection_or_reporting_request",
            proposed_change="",
            affected_resource="",
            approval_required=False,
            approval_prompt="",
            is_read_only=True,
            confidence=0.85,
        )

    return PermissionClassification(
        action_type="unknown",
        risk_level="medium",
        reason="no_rule_match",
        approval_required=True,
        is_read_only=False,
        confidence=0.2,
    )
