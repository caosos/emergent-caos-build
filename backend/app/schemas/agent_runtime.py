from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AgentRuntimeFlags:
    enabled: bool = False
    admin_only: bool = False
    permission_gates_enabled: bool = False
    session_ledger_enabled: bool = False
    skill_registry_enabled: bool = False


@dataclass
class AgentPreflightResult:
    allow_execute: bool = True
    requires_approval: bool = False
    is_side_effect: bool = False
    fallback_allowed: bool = False
    classification_known: bool = True
    reason: str = ""
    receipt_fragment: dict = field(default_factory=dict)


@dataclass
class AgentSessionLedgerRecord:
    session_id: str
    user_email: str
    chat_session_id: str
    user_request: str
    user_id: str | None = None
    interpreted_intent: str = ""
    selected_skill_ids: list[str] = field(default_factory=list)
    plan: dict = field(default_factory=dict)
    permission_gates: list[dict] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)
    receipts: list[dict] = field(default_factory=list)
    final_response: str | None = None
    status: str = "planning"
    error: dict | None = None
    approval_required: bool = False
    approval_status: str = "not_required"
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def model_dump(self) -> dict:
        return asdict(self)
