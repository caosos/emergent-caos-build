"""TurnTrace v1 — per-turn forensic latency ledger.

Step timings tell us where the turn ended. TurnTrace tells us what added time,
when it added it, and why the department was awake.

Keep this module pure: no DB calls, no provider calls, no side effects besides
local monotonic timing inside the active request.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any


@dataclass
class TraceEvent:
    event: str
    phase: str
    at_ms: int
    category: str = "general"
    duration_ms: int | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def as_receipt(self) -> dict[str, Any]:
        doc = {
            "event": self.event,
            "phase": self.phase,
            "at_ms": self.at_ms,
            "category": self.category,
        }
        if self.duration_ms is not None:
            doc["duration_ms"] = self.duration_ms
        if self.meta:
            doc["meta"] = self.meta
        return doc


class TurnTrace:
    """Small request-local timing ledger.

    Usage:
        trace = TurnTrace()
        trace.start("fetch_history", category="db")
        ...work...
        trace.end("fetch_history", meta={"limit": 1000})

    For one-off decisions that do not have duration, use instant().
    """

    def __init__(self) -> None:
        self._start = time.perf_counter()
        self._open: dict[str, tuple[int, str, dict[str, Any]]] = {}
        self._events: list[TraceEvent] = []

    def now_ms(self) -> int:
        return int((time.perf_counter() - self._start) * 1000)

    def start(self, event: str, *, category: str = "general", meta: dict[str, Any] | None = None) -> None:
        at = self.now_ms()
        payload = dict(meta or {})
        self._open[event] = (at, category, payload)
        self._events.append(TraceEvent(event=event, phase="start", at_ms=at, category=category, meta=payload))

    def end(self, event: str, *, category: str | None = None, meta: dict[str, Any] | None = None) -> int:
        at = self.now_ms()
        started_at, started_category, started_meta = self._open.pop(event, (at, category or "general", {}))
        final_category = category or started_category
        payload = {**started_meta, **dict(meta or {})}
        duration = max(0, at - started_at)
        self._events.append(
            TraceEvent(
                event=event,
                phase="end",
                at_ms=at,
                category=final_category,
                duration_ms=duration,
                meta=payload,
            )
        )
        return duration

    def instant(self, event: str, *, category: str = "general", meta: dict[str, Any] | None = None) -> None:
        self._events.append(
            TraceEvent(
                event=event,
                phase="instant",
                at_ms=self.now_ms(),
                category=category,
                meta=dict(meta or {}),
            )
        )

    def receipt(self) -> list[dict[str, Any]]:
        return [event.as_receipt() for event in self._events]

    def phase_timings(self) -> dict[str, int]:
        """Return end-event durations keyed by event name.

        If the same event happens repeatedly, suffix later entries with #N.
        Example: llm_recall, llm_recall#2.
        """
        out: dict[str, int] = {}
        counts: dict[str, int] = {}
        for event in self._events:
            if event.phase != "end" or event.duration_ms is None:
                continue
            counts[event.event] = counts.get(event.event, 0) + 1
            key = event.event if counts[event.event] == 1 else f"{event.event}#{counts[event.event]}"
            out[key] = event.duration_ms
        return out

    def totals_by_category(self) -> dict[str, int]:
        totals: dict[str, int] = {}
        for event in self._events:
            if event.phase != "end" or event.duration_ms is None:
                continue
            totals[event.category] = totals.get(event.category, 0) + event.duration_ms
        return totals


def classify_latency_budget(*, total_ms: int, tool_iterations: int, active_context_tokens: int) -> dict[str, Any]:
    """Classify whether a turn exceeded its rough latency budget.

    This is deliberately simple and receipt-safe. It is not a throttle; it is an
    explanation flag for Aria/admin diagnostics.
    """
    if tool_iterations <= 0:
        target = 10_000
        lane = "fast_or_single_llm"
    elif tool_iterations <= 1:
        target = 15_000
        lane = "single_tool"
    else:
        target = 20_000 + ((tool_iterations - 2) * 5_000)
        lane = "multi_tool"

    context_pressure = "normal"
    if active_context_tokens >= 80_000:
        context_pressure = "high"
    elif active_context_tokens >= 40_000:
        context_pressure = "medium"

    return {
        "lane": lane,
        "target_ms": target,
        "actual_ms": total_ms,
        "exceeded": total_ms > target,
        "over_by_ms": max(0, total_ms - target),
        "tool_iterations": tool_iterations,
        "active_context_tokens": active_context_tokens,
        "context_pressure": context_pressure,
    }
