from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PermissionClassification:
    action_type: str
    risk_level: str = "low"
    reason: str = ""
    proposed_change: str = ""
    affected_resource: str = ""
    approval_required: bool = False
    approval_prompt: str = ""
    is_read_only: bool = True
    confidence: float = 0.0
