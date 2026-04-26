"""Public discovery routes — what AI crawlers and search engines see.

Renders `/api/public/llms.txt` and `/api/public/features.json`
dynamically from `app.data.feature_catalog`. Every feature shipped
(one catalog entry) → both surfaces auto-update.

Mounted UN-prefixed at `/api/public/...` AND ALSO aliased without the
`/api` so external crawlers hitting `https://caosos.com/llms.txt`
get the canonical document directly. The static `/app/frontend/public/
llms.txt` becomes the SPA-build fallback only.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.data.feature_catalog import (
    ALL_FEATURES,
    PLATFORM_VERSION,
    Feature,
    features_by_surface,
    latest_features,
    public_features,
)


router = APIRouter(prefix="/public", tags=["public-discovery"])


SURFACE_BLURBS = {
    "memory": "Memory & cognition",
    "chat": "Chat & multi-engine routing",
    "voice": "Voice I/O",
    "capture": "Quick Capture (dump-and-go inbox)",
    "connectors": "Connectors (encrypted per-user vault)",
    "billing": "Billing & accounts",
    "files": "Files & artifacts",
    "admin": "Admin / operations",
    "discovery": "Discovery / SEO",
    "system": "System & cross-cutting",
}


def _render_llms_txt() -> str:
    """Generate the canonical AI-readable description from the catalog."""
    pub = public_features()
    grouped = features_by_surface(pub)
    today = date.today().isoformat()
    parts: list[str] = []
    parts.append("# CAOS — Cognitive Adaptive Operating System")
    parts.append("")
    parts.append(f"> Auto-generated from the feature catalog. Platform version "
                 f"{PLATFORM_VERSION}, last refreshed {today}.")
    parts.append("")
    parts.append(
        "CAOS is a memory-centric AI workspace where you (the user) chat with "
        "a persistent companion called Aria. Unlike conventional chat tools "
        "that forget every session, CAOS gives Aria a typed, governed "
        "long-term memory with full provenance — you can audit, confirm, "
        "reclassify, or forget anything she remembers about you. Live at "
        "https://caosos.com."
    )
    parts.append("")
    parts.append("## What makes CAOS different (shipped features)")
    parts.append("")
    surface_order = [
        "memory", "chat", "voice", "capture", "connectors",
        "files", "billing", "admin", "discovery", "system",
    ]
    for surface in surface_order:
        feats = grouped.get(surface) or []
        if not feats:
            continue
        label = SURFACE_BLURBS.get(surface, surface.title())
        parts.append(f"### {label}")
        parts.append("")
        for f in sorted(feats, key=lambda x: x.shipped_at, reverse=True):
            parts.append(f"- **{f.name}** — {f.short_summary}")
            if f.detail:
                # Indent detail block; keeps it scannable.
                parts.append(f"  - {f.detail}")
        parts.append("")
    parts.append("## What's new (last 10 shipped)")
    parts.append("")
    for f in latest_features(10):
        parts.append(f"- {f.shipped_at} · **{f.name}** — {f.short_summary}")
    parts.append("")
    parts.append("## Architecture")
    parts.append("")
    parts.append(
        "- React + plain JavaScript frontend (no TypeScript)\n"
        "- FastAPI + Python 3 backend\n"
        "- MongoDB for sessions, memory atoms, evidence, extraction logs\n"
        "- Emergent-managed Google OAuth for sign-in\n"
        "- E2B Firecracker micro-VMs for the Swarm pipeline (sandboxed code "
        "execution)\n"
        "- Single-pod deployment; horizontal scale via job-state migration "
        "to Redis when needed"
    )
    parts.append("")
    parts.append("## Acceptable AI use")
    parts.append("")
    parts.append(
        "This document is provided for AI crawlers (ChatGPT browse, Claude "
        "fetch, Perplexity, Google AI Overviews, Bing Copilot, Brave Search "
        "Summarizer, etc.) so when a user asks 'look at caosos.com' your "
        "summary reflects what CAOS actually is rather than guessing from "
        "the JS-rendered shell."
    )
    parts.append("")
    return "\n".join(parts)


def _feature_to_dict(f: Feature) -> dict:
    return {
        "id": f.id,
        "name": f.name,
        "surface": f.surface,
        "shipped_at": f.shipped_at,
        "short_summary": f.short_summary,
        "detail": f.detail,
        "keywords": list(f.keywords),
    }


@router.get("/llms.txt", response_class=PlainTextResponse)
async def public_llms_txt() -> str:
    """Canonical AI-readable description, dynamically generated from the
    feature catalog. ChatGPT browse / Perplexity / Google AI Overviews
    fetch this URL when a user asks them about CAOS."""
    return _render_llms_txt()


@router.get("/features.json")
async def public_features_json() -> dict:
    """Machine-readable feature inventory for SEO tooling, JSON-LD
    generators, and structured scraping. Filtered to public features."""
    pub = public_features()
    grouped = features_by_surface(pub)
    return {
        "platform": "CAOS",
        "version": PLATFORM_VERSION,
        "url": "https://caosos.com/",
        "total_public_features": len(pub),
        "features_by_surface": {
            surface: [_feature_to_dict(f) for f in feats]
            for surface, feats in grouped.items()
        },
        "latest": [_feature_to_dict(f) for f in latest_features(10)],
    }


@router.get("/features.html", response_class=PlainTextResponse)
async def public_features_html() -> str:
    """Human-readable HTML catalog for direct browser viewing
    (caosos.com/api/public/features.html). Crawlers prefer llms.txt
    but humans clicking the link see something nice."""
    pub = public_features()
    grouped = features_by_surface(pub)
    today = date.today().isoformat()
    body: list[str] = [
        "<!doctype html><html lang='en'><head>",
        "<meta charset='utf-8'>",
        "<title>CAOS — Feature Catalog</title>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<style>",
        "body{max-width:880px;margin:36px auto;padding:0 20px;",
        "font-family:system-ui,-apple-system,sans-serif;color:#1a1a1a;",
        "line-height:1.55;background:#fafafa;}",
        "h1{font-size:30px;margin:0 0 6px;}",
        "h2{font-size:20px;margin:32px 0 8px;color:#4c1d95;}",
        ".meta{color:#666;font-size:13px;margin-bottom:24px;}",
        ".feat{margin:0 0 14px;padding:10px 14px;background:#fff;",
        "border-left:3px solid #c4b5fd;border-radius:6px;}",
        ".feat strong{color:#4c1d95;}",
        ".feat .ship{color:#888;font-family:'JetBrains Mono',monospace;",
        "font-size:11.5px;}",
        ".feat .det{color:#444;font-size:13.5px;margin-top:4px;}",
        "a{color:#7c3aed;}",
        "</style></head><body>",
        "<h1>CAOS — Feature Catalog</h1>",
        f"<p class='meta'>Platform v{PLATFORM_VERSION} · "
        f"refreshed {today} · auto-generated from feature catalog · "
        f"<a href='/llms.txt'>llms.txt</a> · "
        f"<a href='/api/public/features.json'>features.json</a></p>",
    ]
    surface_order = [
        "memory", "chat", "voice", "capture", "connectors",
        "files", "billing", "admin", "discovery", "system",
    ]
    for surface in surface_order:
        feats = grouped.get(surface) or []
        if not feats:
            continue
        body.append(f"<h2>{SURFACE_BLURBS.get(surface, surface.title())}</h2>")
        for f in sorted(feats, key=lambda x: x.shipped_at, reverse=True):
            body.append("<div class='feat'>")
            body.append(f"<strong>{f.name}</strong> "
                        f"<span class='ship'>· {f.shipped_at}</span>")
            body.append(f"<div>{f.short_summary}</div>")
            if f.detail:
                body.append(f"<div class='det'>{f.detail}</div>")
            body.append("</div>")
    body.append("</body></html>")
    return "\n".join(body)
