"""CAOS cockpit surface registry.

This module gives Aria a compact, explicit map of the product surfaces she lives
inside. It is intentionally static/pure: no DB calls, no tool calls, no side
effects. The proactivity policy can use it to decide which department should
wake up without injecting every surface description into every prompt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


@dataclass(frozen=True)
class SurfaceDefinition:
    id: str
    name: str
    access: str
    purpose: str
    wake_patterns: tuple[str, ...] = ()
    departments: tuple[str, ...] = ()
    display_hint: str | None = None
    first_action: str | None = None

    def as_receipt(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "access": self.access,
            "purpose": self.purpose,
            "departments": list(self.departments),
            "display_hint": self.display_hint,
            "first_action": self.first_action,
        }


SURFACES: tuple[SurfaceDefinition, ...] = (
    SurfaceDefinition(
        id="memory_console",
        name="Memory Console",
        access="user",
        purpose="View, confirm, reclassify, or forget memory atoms across CAOS memory bins.",
        wake_patterns=("memory", "remember", "forgot", "forget", "reclassify", "preference", "fact"),
        departments=("structured_memory", "memory_bins"),
        display_hint="memory_panel",
    ),
    SurfaceDefinition(
        id="support_tickets",
        name="Support Tickets",
        access="admin",
        purpose="Track user-reported bugs, UX issues, feature requests, and operational complaints.",
        wake_patterns=("broken", "bug", "issue", "ticket", "problem", "doesn't work", "not working"),
        departments=("support_ticketing", "diagnostics"),
        display_hint="ticket_panel",
        first_action="diagnose_before_ticket",
    ),
    SurfaceDefinition(
        id="admin_dashboard",
        name="Admin Dashboard",
        access="admin",
        purpose="Monitor users, sessions, spend, errors, engine timelines, usage, and system health.",
        wake_patterns=("admin", "dashboard", "usage", "spend", "cost", "errors", "latency", "slow", "engine"),
        departments=("receipts", "engine_usage", "diagnostics"),
        display_hint="admin_dashboard",
        first_action="profile_session",
    ),
    SurfaceDefinition(
        id="admin_docs",
        name="Admin Docs",
        access="admin",
        purpose="Built-in project blueprints, playbooks, PRDs, roadmaps, checklists, and troubleshooting notes.",
        wake_patterns=("blueprint", "roadmap", "prd", "playbook", "docs", "checklist", "troubleshooting"),
        departments=("project_docs", "admin_docs"),
        display_hint="docs_viewer",
    ),
    SurfaceDefinition(
        id="artifacts",
        name="Artifacts",
        access="user",
        purpose="Stored files, photos, links, receipts, summaries, seeds, and memory artifacts.",
        wake_patterns=("artifact", "receipt", "summary", "seed", "saved", "stored", "attachment"),
        departments=("artifacts", "receipts", "summaries", "seeds"),
        display_hint="artifact_drawer",
    ),
    SurfaceDefinition(
        id="files_photos_links",
        name="Files / Photos / Links",
        access="user",
        purpose="Upload, inspect, search, and manage user files, screenshots, photos, and saved links.",
        wake_patterns=("file", "photo", "image", "screenshot", "pdf", "link", "upload", "read this"),
        departments=("files", "photos", "links", "vision"),
        display_hint="file_drawer",
    ),
    SurfaceDefinition(
        id="engine_selector",
        name="Engine Selector",
        access="user",
        purpose="Switch or compare inference engines such as OpenAI, Claude, Gemini, and other configured providers.",
        wake_patterns=("engine", "model", "openai", "claude", "gemini", "provider", "compare engines"),
        departments=("runtime", "engine_usage"),
        display_hint="engine_panel",
    ),
    SurfaceDefinition(
        id="agent_swarm",
        name="Agent Swarm",
        access="user",
        purpose="Coordinate multi-agent or E2B-backed work where a single assistant turn is not enough.",
        wake_patterns=("swarm", "multi-agent", "agent", "e2b", "campaign", "autonomous", "parallel"),
        departments=("agent_swarm", "tool_planner"),
        display_hint="swarm_panel",
    ),
    SurfaceDefinition(
        id="voice_settings",
        name="Voice / Speech",
        access="user",
        purpose="Control STT/TTS, voice, read-aloud, microphone, speed, and voice-first behavior.",
        wake_patterns=("voice", "speech", "stt", "tts", "mic", "microphone", "read aloud", "transcribe"),
        departments=("voice", "stt", "tts"),
        display_hint="voice_settings",
    ),
    SurfaceDefinition(
        id="thread_search",
        name="Thread Search",
        access="user",
        purpose="Search current or previous conversations and locate prior context.",
        wake_patterns=("search this thread", "previous thread", "find in thread", "where did we say"),
        departments=("thread_search", "conversation_history"),
        display_hint="thread_search",
    ),
    SurfaceDefinition(
        id="wcw_meter",
        name="Working Context Window Meter",
        access="user",
        purpose="Show active context load versus selected model context capacity.",
        wake_patterns=("context window", "wcw", "tokens", "active context", "context meter", "bloat"),
        departments=("token_meter", "receipts"),
        display_hint="wcw_meter",
    ),
    SurfaceDefinition(
        id="quick_capture",
        name="Quick Capture",
        access="user",
        purpose="Capture notes, ideas, reminders, and raw thoughts without disrupting the active thread.",
        wake_patterns=("quick capture", "capture this", "note this", "save this thought", "reminder"),
        departments=("notes", "capture"),
        display_hint="quick_capture",
    ),
)


def match_surfaces(text: str, *, is_admin: bool = False) -> list[SurfaceDefinition]:
    lowered = (text or "").lower()
    matches: list[SurfaceDefinition] = []
    for surface in SURFACES:
        if surface.access == "admin" and not is_admin:
            continue
        for pattern in surface.wake_patterns:
            if re.search(r"\b" + re.escape(pattern.lower()) + r"\b", lowered):
                matches.append(surface)
                break
    return matches


def build_surface_context(text: str, *, is_admin: bool = False) -> dict[str, Any]:
    matched = match_surfaces(text, is_admin=is_admin)
    departments: list[str] = []
    display_hints: list[str] = []
    first_actions: list[str] = []
    for surface in matched:
        for dept in surface.departments:
            if dept not in departments:
                departments.append(dept)
        if surface.display_hint and surface.display_hint not in display_hints:
            display_hints.append(surface.display_hint)
        if surface.first_action and surface.first_action not in first_actions:
            first_actions.append(surface.first_action)
    return {
        "matched_surfaces": [surface.as_receipt() for surface in matched],
        "wake_departments": departments,
        "display_hints": display_hints,
        "first_actions": first_actions,
    }
