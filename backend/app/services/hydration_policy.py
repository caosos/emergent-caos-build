"""Turn-level hydration policy for CAOS chat.

The model context window is capacity, not a fill target. This module decides
which standby departments are allowed into the active prompt for a single turn:
history budget, cross-thread continuity, lane workers, global cache, and tools.

Keep this file pure: no DB calls, no provider calls, no side effects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


@dataclass(frozen=True)
class HydrationDecision:
    mode: str = "fast"
    history_token_budget: int = 12_000
    use_cross_thread: bool = False
    use_lane_workers: bool = False
    use_global_info: bool = False
    use_tool_prompt: bool = False
    use_connector_tools: bool = False
    reasons: list[str] = field(default_factory=list)

    def as_receipt(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "history_token_budget": self.history_token_budget,
            "use_cross_thread": self.use_cross_thread,
            "use_lane_workers": self.use_lane_workers,
            "use_global_info": self.use_global_info,
            "use_tool_prompt": self.use_tool_prompt,
            "use_connector_tools": self.use_connector_tools,
            "reasons": list(self.reasons),
        }


_CONTINUITY_RX = re.compile(
    r"\b(remember|previous|earlier|last time|continue|where were we|what did we decide|"
    r"thread|summary|seed|lane|worker|memory|memories|blueprint|contract|handoff|"
    r"caos|caos care|project|architecture|audit|repo|repository)\b",
    re.I,
)

_TOOL_RX = re.compile(
    r"\b(code|repo|repository|github|file|inspect|audit|debug|bug|error|exception|"
    r"stack trace|traceback|latency|bottleneck|receipt|profile_session|query_receipts|"
    r"route|endpoint|api|database|mongo|db|deploy|branch|pr|pull request|merge|"
    r"fix|patch|write|save|report|look up|lookup|find|open|read|check|verify)\b",
    re.I,
)

_DEEP_RX = re.compile(
    r"\b(deep audit|full audit|entire thread|full context|all context|everything|"
    r"whole repo|all files|complete review|system-wide|end-to-end)\b",
    re.I,
)

_CONNECTOR_RX = re.compile(
    r"\b(gmail|google|drive|docs|sheets|slides|slack|obsidian|telegram|sms|twilio|"
    r"mcp|connector|calendar|contacts)\b",
    re.I,
)

_GLOBAL_RX = re.compile(
    r"\b(latest|current|today|news|web|source|citation|public|internet|search|"
    r"price|pricing|schedule|law|regulation|weather|stock|market)\b",
    re.I,
)


def _cap_budget(selected: int, model_context_window: int) -> int:
    """Keep active history compact while respecting smaller models.

    The WCW meter should still show the true model capacity elsewhere. This cap
    only limits the history truck-load for this turn.
    """
    if model_context_window <= 0:
        return selected
    # Never spend more than 30% of model capacity on history by policy, and do
    # not exceed the explicit selected tier.
    return max(4_000, min(selected, int(model_context_window * 0.30)))


def build_hydration_decision(
    user_message: str,
    *,
    model_context_window: int,
    session: dict | None = None,
    is_admin: bool = False,
) -> HydrationDecision:
    """Classify a turn into a bounded hydration mode.

    Capability is not gated here. This only decides which manuals/standby
    departments are injected up front. If a turn smells actionable, tools and
    connector checks stay available so Aria remains proactive.
    """
    text = (user_message or "").strip()
    lowered = text.lower()
    reasons: list[str] = []

    continuity = bool(_CONTINUITY_RX.search(lowered))
    tools = bool(_TOOL_RX.search(lowered))
    deep = bool(_DEEP_RX.search(lowered))
    connectors = bool(_CONNECTOR_RX.search(lowered))
    global_info = bool(_GLOBAL_RX.search(lowered))
    proactive_connector = tools or connectors or global_info

    # A non-general lane is a weak continuity hint, but not enough to force
    # heavyweight workers unless the user message also asks for continuity.
    active_lane = str((session or {}).get("lane") or "general").strip().lower()
    lane_hint = active_lane and active_lane != "general"

    if deep:
        reasons.append("deep_signal")
        if proactive_connector:
            reasons.append("proactive_connector_signal")
        return HydrationDecision(
            mode="deep",
            history_token_budget=_cap_budget(120_000, model_context_window),
            use_cross_thread=True,
            use_lane_workers=True,
            use_global_info=True,
            use_tool_prompt=True,
            use_connector_tools=proactive_connector,
            reasons=reasons,
        )

    if tools:
        reasons.append("tool_or_diagnostic_signal")
        if continuity:
            reasons.append("continuity_signal")
        if connectors:
            reasons.append("connector_signal")
        if global_info:
            reasons.append("global_info_signal")
        return HydrationDecision(
            mode="tool",
            history_token_budget=_cap_budget(48_000 if continuity else 32_000, model_context_window),
            use_cross_thread=continuity,
            use_lane_workers=continuity,
            use_global_info=global_info,
            use_tool_prompt=True,
            # Tool mode should be proactive: if the user asks to inspect/check/find,
            # the connector department may be needed even if they did not name it.
            use_connector_tools=True,
            reasons=reasons,
        )

    if continuity:
        reasons.append("continuity_signal")
        if lane_hint:
            reasons.append("active_lane_hint")
        if proactive_connector:
            reasons.append("proactive_connector_signal")
        return HydrationDecision(
            mode="continuity",
            history_token_budget=_cap_budget(32_000, model_context_window),
            use_cross_thread=True,
            use_lane_workers=True,
            use_global_info=global_info,
            use_tool_prompt=False,
            use_connector_tools=proactive_connector,
            reasons=reasons,
        )

    if global_info:
        reasons.append("global_info_signal")
        return HydrationDecision(
            mode="global",
            history_token_budget=_cap_budget(16_000, model_context_window),
            use_cross_thread=False,
            use_lane_workers=False,
            use_global_info=True,
            use_tool_prompt=True,
            use_connector_tools=True,
            reasons=reasons,
        )

    if connectors:
        reasons.append("connector_signal")
        return HydrationDecision(
            mode="connector",
            history_token_budget=_cap_budget(20_000, model_context_window),
            use_cross_thread=False,
            use_lane_workers=False,
            use_global_info=False,
            use_tool_prompt=True,
            use_connector_tools=True,
            reasons=reasons,
        )

    reasons.append("fast_path_default")
    return HydrationDecision(
        mode="fast",
        history_token_budget=_cap_budget(12_000, model_context_window),
        use_cross_thread=False,
        use_lane_workers=False,
        use_global_info=False,
        use_tool_prompt=False,
        use_connector_tools=False,
        reasons=reasons,
    )
