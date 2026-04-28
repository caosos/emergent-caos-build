"""CAOS proactivity policy.

This is the small frontal-lobe decision layer: it classifies the user's current
message into an operational intent and names which CAOS surfaces/departments
should wake first. It stays pure and receipt-friendly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from app.services.surface_registry import build_surface_context


@dataclass(frozen=True)
class ProactivityDecision:
    primary_intent: str = "casual_or_direct"
    confidence: float = 0.50
    wake_departments: list[str] = field(default_factory=list)
    matched_surfaces: list[dict[str, Any]] = field(default_factory=list)
    display_hints: list[str] = field(default_factory=list)
    first_action: str | None = None
    diagnose_before_ticket: bool = False
    allow_tools: bool = False
    allow_connectors: bool = False
    reasons: list[str] = field(default_factory=list)

    def as_receipt(self) -> dict[str, Any]:
        return {
            "primary_intent": self.primary_intent,
            "confidence": self.confidence,
            "wake_departments": list(self.wake_departments),
            "matched_surfaces": list(self.matched_surfaces),
            "display_hints": list(self.display_hints),
            "first_action": self.first_action,
            "diagnose_before_ticket": self.diagnose_before_ticket,
            "allow_tools": self.allow_tools,
            "allow_connectors": self.allow_connectors,
            "reasons": list(self.reasons),
        }


_LATENCY_RX = re.compile(r"\b(slow|latency|lag|delay|timeout|timed out|hang|hanging|expensive|cost|tokens|bloated|context window|wcw|takes forever|dragging)\b", re.I)
_BUG_RX = re.compile(r"\b(broken|bug|error|exception|traceback|doesn't work|not working|failed|failure|stuck|glitch|issue|problem)\b", re.I)
_CODE_RX = re.compile(r"\b(code|repo|repository|github|file|function|route|endpoint|api|database|mongo|db|inspect|audit|patch|fix|branch|pr|merge|deploy|redeploy)\b", re.I)
_MEMORY_RX = re.compile(r"\b(remember|memory|memories|forgot|forget|previous|earlier|last time|where were we|what did we decide|thread|summary|seed|continuity)\b", re.I)
_CONNECTOR_RX = re.compile(r"\b(gmail|google drive|drive|docs|sheets|slides|calendar|contacts|slack|obsidian|telegram|sms|twilio|mcp|connector)\b", re.I)
_FILE_RX = re.compile(r"\b(file|photo|image|screenshot|pdf|attachment|upload|link|read this|look at this)\b", re.I)
_DISPLAY_RX = re.compile(r"\b(chart|graph|table|carousel|diagram|mindmap|timeline|visualize|show me|compare)\b", re.I)
_SEARCH_RX = re.compile(r"\b(search|look up|lookup|find|verify|check|current|latest|web|internet|source|citation)\b", re.I)
_TICKET_RX = re.compile(r"\b(ticket|support ticket|file this|report this|log this)\b", re.I)


def _dedupe(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item and item not in out:
            out.append(item)
    return out


def build_proactivity_decision(user_message: str, *, is_admin: bool = False) -> ProactivityDecision:
    text = (user_message or "").strip()
    reasons: list[str] = []
    surface_context = build_surface_context(text, is_admin=is_admin)
    wake_departments = list(surface_context["wake_departments"])
    display_hints = list(surface_context["display_hints"])
    first_actions = list(surface_context["first_actions"])

    latency = bool(_LATENCY_RX.search(text))
    bug = bool(_BUG_RX.search(text))
    code = bool(_CODE_RX.search(text))
    memory = bool(_MEMORY_RX.search(text))
    connector = bool(_CONNECTOR_RX.search(text))
    file_ref = bool(_FILE_RX.search(text))
    display = bool(_DISPLAY_RX.search(text))
    search = bool(_SEARCH_RX.search(text))
    ticket = bool(_TICKET_RX.search(text))

    if latency:
        reasons.append("latency_or_context_signal")
        wake_departments += ["receipts", "engine_usage", "diagnostics", "token_meter"]
        display_hints += ["diagnostic_card"]
        return ProactivityDecision(
            primary_intent="diagnostic_latency",
            confidence=0.94,
            wake_departments=_dedupe(wake_departments),
            matched_surfaces=surface_context["matched_surfaces"],
            display_hints=_dedupe(display_hints),
            first_action="profile_session",
            diagnose_before_ticket=True,
            allow_tools=True,
            allow_connectors=True,
            reasons=reasons,
        )

    if bug:
        reasons.append("bug_or_problem_signal")
        wake_departments += ["diagnostics", "receipts", "support_ticketing"]
        display_hints += ["diagnostic_card"]
        return ProactivityDecision(
            primary_intent="bug_diagnostic",
            confidence=0.88,
            wake_departments=_dedupe(wake_departments),
            matched_surfaces=surface_context["matched_surfaces"],
            display_hints=_dedupe(display_hints),
            first_action="query_receipts",
            diagnose_before_ticket=True,
            allow_tools=True,
            allow_connectors=True,
            reasons=reasons,
        )

    if code:
        reasons.append("code_or_deployment_signal")
        wake_departments += ["repo_tools", "diagnostics"]
        return ProactivityDecision(
            primary_intent="code_or_deployment",
            confidence=0.90,
            wake_departments=_dedupe(wake_departments),
            matched_surfaces=surface_context["matched_surfaces"],
            display_hints=_dedupe(display_hints),
            first_action="inspect_repo",
            diagnose_before_ticket=False,
            allow_tools=True,
            allow_connectors=True,
            reasons=reasons,
        )

    if memory:
        reasons.append("memory_or_continuity_signal")
        wake_departments += ["structured_memory", "thread_summaries", "context_seeds", "lane_workers"]
        display_hints += ["memory_panel"]
        return ProactivityDecision(
            primary_intent="memory_continuity",
            confidence=0.90,
            wake_departments=_dedupe(wake_departments),
            matched_surfaces=surface_context["matched_surfaces"],
            display_hints=_dedupe(display_hints),
            first_action=None,
            diagnose_before_ticket=False,
            allow_tools=False,
            allow_connectors=connector,
            reasons=reasons,
        )

    if connector or file_ref or search:
        reasons.append("retrieval_or_connector_signal")
        wake_departments += ["connectors", "files", "search"]
        if file_ref:
            display_hints += ["file_drawer"]
        return ProactivityDecision(
            primary_intent="retrieval_or_connector",
            confidence=0.86,
            wake_departments=_dedupe(wake_departments),
            matched_surfaces=surface_context["matched_surfaces"],
            display_hints=_dedupe(display_hints),
            first_action="retrieve_or_search",
            diagnose_before_ticket=False,
            allow_tools=True,
            allow_connectors=True,
            reasons=reasons,
        )

    if display:
        reasons.append("display_request_signal")
        wake_departments += ["display_planner", "artifacts"]
        display_hints += ["visual_artifact"]
        return ProactivityDecision(
            primary_intent="display_or_artifact",
            confidence=0.82,
            wake_departments=_dedupe(wake_departments),
            matched_surfaces=surface_context["matched_surfaces"],
            display_hints=_dedupe(display_hints),
            first_action=None,
            diagnose_before_ticket=False,
            allow_tools=False,
            allow_connectors=False,
            reasons=reasons,
        )

    if ticket:
        reasons.append("ticket_signal")
        wake_departments += ["support_ticketing"]
        return ProactivityDecision(
            primary_intent="support_ticket_request",
            confidence=0.84,
            wake_departments=_dedupe(wake_departments),
            matched_surfaces=surface_context["matched_surfaces"],
            display_hints=_dedupe(display_hints),
            first_action="file_ticket_if_confirmed",
            diagnose_before_ticket=False,
            allow_tools=False,
            allow_connectors=False,
            reasons=reasons,
        )

    if surface_context["matched_surfaces"]:
        reasons.append("surface_registry_match")
        return ProactivityDecision(
            primary_intent="surface_navigation",
            confidence=0.76,
            wake_departments=_dedupe(wake_departments),
            matched_surfaces=surface_context["matched_surfaces"],
            display_hints=_dedupe(display_hints),
            first_action=first_actions[0] if first_actions else None,
            diagnose_before_ticket="diagnose_before_ticket" in first_actions,
            allow_tools=False,
            allow_connectors=False,
            reasons=reasons,
        )

    reasons.append("casual_or_direct_default")
    return ProactivityDecision(
        primary_intent="casual_or_direct",
        confidence=0.62,
        wake_departments=[],
        matched_surfaces=[],
        display_hints=[],
        first_action=None,
        diagnose_before_ticket=False,
        allow_tools=False,
        allow_connectors=False,
        reasons=reasons,
    )
