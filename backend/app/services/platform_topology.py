"""Canonical CAOS platform topology — the system Aria lives in.

Renders dynamically from `app.data.feature_catalog.ALL_FEATURES` so any
feature shipped (one entry in the catalog) is automatically known to
Aria on the very next chat turn — no separate edit here.

Token-bounded: the per-bin descriptors come from `BIN_REGISTRY` directly,
and feature lines are filtered by `aria_priority >= 2` so prompt size
stays manageable even as the catalog grows.
"""
from __future__ import annotations

from app.data.feature_catalog import (
    PLATFORM_VERSION,
    aria_features,
    features_by_surface,
)
from app.schemas.memory import BIN_REGISTRY, MemoryBin


SURFACE_LABELS = {
    "memory": "Memory & cognition",
    "chat": "Chat / cognition core",
    "voice": "Voice",
    "capture": "Quick Capture",
    "connectors": "Connectors",
    "billing": "Billing & accounts",
    "files": "Files & artifacts",
    "admin": "Admin / ops",
    "discovery": "Discovery / SEO",
    "system": "System",
}


def _bin_inventory() -> str:
    """One-line descriptor per bin so Aria can speak about them by name."""
    lines: list[str] = []
    for bin_id, info in BIN_REGISTRY.items():
        if bin_id == MemoryBin.GENERAL.value:
            continue
        prio = info.get("default_priority", 50)
        lines.append(f"  - **{bin_id}** (P{prio}): {info.get('description', '')}")
    return "\n".join(lines)


def _feature_inventory() -> str:
    """Render the catalog's high-priority features grouped by surface."""
    grouped = features_by_surface(aria_features(min_priority=2))
    blocks: list[str] = []
    # Render in a stable surface order so prompt diffs are minimal.
    surface_order = [
        "memory", "chat", "voice", "capture", "connectors",
        "files", "billing", "admin", "discovery", "system",
    ]
    for surface in surface_order:
        feats = grouped.get(surface) or []
        if not feats:
            continue
        label = SURFACE_LABELS.get(surface, surface.title())
        rows = "\n".join(
            f"  - **{f.name}** — {f.short_summary}" for f in feats
        )
        blocks.append(f"### {label}\n{rows}")
    return "\n\n".join(blocks)


def build_platform_topology() -> str:
    """Return the canonical CAOS topology block. Cheap to compute (no I/O)."""
    return f"""
PLATFORM TOPOLOGY (CAOS v{PLATFORM_VERSION} — your house; know it cold):

CAOS = Cognitive Adaptive Operating System. A memory-centric AI workspace where you (the assistant) live alongside the user, with continuity, governed memory, and explicit provenance. Custom domain: caosos.com.

The 13 typed memory bins:
{_bin_inventory()}

# Shipped features (auto-synced from the feature catalog)

{_feature_inventory()}

# Behavior contract for you (Aria) — platform-aware speaking
- When the user references a CAOS surface by name ("Memory Console", "Connectors", "WCW meter", "Pricing", "the Counter bin", "Quick Capture", "Swarm"), DO NOT guess — answer from this topology. You know it cold.
- If the user asks "where do I [do thing]?" — point them at the right surface using the names above (e.g. "Open Account menu → Memory Console").
- If they ask about a connector that's not in the list above, say "that connector isn't wired yet" rather than improvising.
- If they ask about an admin/billing/support flow, surface the right path (Admin Dashboard, Pricing, Support Tickets) instead of speculating.
- This topology auto-syncs from `/app/backend/app/data/feature_catalog.py` — when an engineer ships a new feature, your awareness updates on the next turn.
""".strip()
