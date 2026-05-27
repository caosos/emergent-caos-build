from __future__ import annotations

import os

from app.schemas.agent_runtime import AgentRuntimeFlags


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_agent_runtime_flags() -> AgentRuntimeFlags:
    return AgentRuntimeFlags(
        enabled=_as_bool(os.environ.get("CAOS_AGENT_RUNTIME_ENABLED"), False),
        admin_only=_as_bool(os.environ.get("CAOS_AGENT_RUNTIME_ADMIN_ONLY"), False),
        permission_gates_enabled=_as_bool(os.environ.get("CAOS_PERMISSION_GATES_ENABLED"), False),
        session_ledger_enabled=_as_bool(os.environ.get("CAOS_SESSION_LEDGER_ENABLED"), False),
        approval_persistence_enabled=_as_bool(os.environ.get("CAOS_APPROVAL_PERSISTENCE_ENABLED"), False),
        runtime_receipts_enabled=_as_bool(os.environ.get("CAOS_RUNTIME_RECEIPTS_ENABLED"), False),
        skill_registry_enabled=_as_bool(os.environ.get("CAOS_SKILL_REGISTRY_ENABLED"), False),
    )


def runtime_applies(is_admin_user: bool, flags: AgentRuntimeFlags | None = None) -> bool:
    active = flags or load_agent_runtime_flags()
    if not active.enabled:
        return False
    if active.admin_only and not is_admin_user:
        return False
    return True
