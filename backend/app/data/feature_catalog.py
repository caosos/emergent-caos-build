"""Feature catalog — the SINGLE source of truth for what CAOS does.

Every feature shipped to the platform gets one entry here. Two surfaces
read from this catalog:

1. **`platform_topology.build_platform_topology()`** — Aria's system-prompt
   awareness of her own house. When you add an entry here, she knows
   about the feature on the very next chat turn.

2. **`/api/public/llms.txt`** + **`/api/public/features.json`** — the
   public-facing AI/SEO discovery surfaces. ChatGPT browse, Perplexity,
   Google AI Overviews fetch these and reflect what CAOS does to anyone
   asking about it externally.

**Workflow contract for engineers / agents:**
After shipping ANY user-visible change, append/update the relevant
`Feature` here. Both Aria's awareness and the public docs sync
automatically — no separate llms.txt edit, no separate topology edit.

Schema notes:
- `id` — kebab-case, stable, never reused; used as the anchor in URLs/docs
- `surface` — which top-level UI surface this lives in (or "system")
- `aria_priority` — 1..5; controls topology-block ordering. 5 = critical
  (memory, governance, billing). 1 = trivial cosmetic. Anything <2 omitted
  from Aria's topology to save tokens, but still in public docs.
- `public` — set False for internal/admin-only features that shouldn't
  appear in the marketing/SEO surface
- `shipped_at` — YYYY-MM-DD; sorted desc on the public "What's new"
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Feature:
    id: str
    name: str
    surface: str  # "memory" | "connectors" | "voice" | "capture" | "billing" | "admin" | "chat" | "files" | "system" | "discovery"
    aria_priority: int  # 1..5
    public: bool
    shipped_at: str  # YYYY-MM-DD
    short_summary: str  # one-liner, ≤120 chars (used in topology + llms.txt list)
    detail: str = ""  # paragraph; used in long-form public docs only
    keywords: list[str] = field(default_factory=list)


PLATFORM_VERSION = "2026.04.25"


# ---- Memory & cognition ----------------------------------------------------

MEMORY_FEATURES = [
    Feature(
        id="memory-bins-13",
        name="13 typed memory bins",
        surface="memory",
        aria_priority=5,
        public=True,
        shipped_at="2026-04-25",
        short_summary=(
            "Typed governance schema with 13 bins (Identity, Active Project, Governance Rule, "
            "Operating Preference, Relationship Boundary, Domain Context, Technical State, "
            "Behavioral Pattern, Derived Trait, Learning Profile, Real-World Context, Risk "
            "Signal, Counterevidence)."
        ),
        detail=(
            "Every fact CAOS remembers about you is filed into one of 13 typed bins. Each bin "
            "carries a default injection priority and governance rules (allows_inference, "
            "requires_user_confirmation, sensitivity). USER_EXPLICIT facts win over DERIVED "
            "candidates in retrieval ties; GOVERNANCE_RULE atoms ride a high-priority floor so "
            "they're always pulled even on tangential turns."
        ),
        keywords=["memory bins", "typed memory", "governance", "provenance"],
    ),
    Feature(
        id="memory-console",
        name="Memory Console (audit + edit)",
        surface="memory",
        aria_priority=5,
        public=True,
        shipped_at="2026-04-25",
        short_summary=(
            "Per-user audit drawer: see every atom Aria knows about you, source mode, "
            "confidence, evidence count, and Confirm / Reclassify / Forget controls."
        ),
        detail=(
            "Open from Account menu → Memory Console. Bin tabs along the left, atom cards on "
            "the right (USER-STATED green / OBSERVED blue / DERIVED purple / SYSTEM grey "
            "pills). Click evidence pill → side-panel showing the source conversation + date. "
            "All atoms are owner-gated; the autonomous extractor's DERIVED candidates surface "
            "with a yellow border and Confirm button so you stay in charge."
        ),
        keywords=["memory console", "audit", "atom", "confirm", "forget", "reclassify"],
    ),
    Feature(
        id="memory-extractor-autonomous",
        name="Autonomous memory extraction",
        surface="memory",
        aria_priority=5,
        public=True,
        shipped_at="2026-04-25",
        short_summary=(
            "After every chat turn, a background pass classifies new facts into the 13 typed "
            "bins automatically — no manual review queue."
        ),
        detail=(
            "Gemini 3 Flash inspects each (user_message, assistant_reply) exchange and proposes "
            "atoms with bin classification + confidence + evidence quote. Hard-cap of 5 atoms "
            "per turn. Dedup against the last 40 atoms. Non-fatal on failure — never blocks "
            "the chat reply."
        ),
        keywords=["autonomous extraction", "memory pipeline", "gemini flash"],
    ),
    Feature(
        id="memory-backfill",
        name="Past-conversation backfill",
        surface="memory",
        aria_priority=4,
        public=True,
        shipped_at="2026-04-25",
        short_summary=(
            "Mine every prior conversation for memory atoms in one pass. Idempotent — never "
            "re-processes a stamped message."
        ),
        detail=(
            "Backed by a `memory_extraction_log` collection keyed by (user_email, message_id). "
            "Two paths: full per-user backfill (Memory Console button) and auto-incremental on "
            "session-load (silently mines unmined messages whenever you open a thread)."
        ),
        keywords=["backfill", "import history", "idempotent"],
    ),
    Feature(
        id="memory-provenance",
        name="Memory provenance (source attribution)",
        surface="memory",
        aria_priority=4,
        public=True,
        shipped_at="2026-04-25",
        short_summary=(
            "Every evidence anchor shows the source conversation title + original date — "
            "answers 'where did Aria learn this?'"
        ),
        keywords=["provenance", "evidence", "source attribution"],
    ),
    Feature(
        id="memory-pulse",
        name="Memory Pulse toast",
        surface="memory",
        aria_priority=2,
        public=True,
        shipped_at="2026-04-25",
        short_summary=(
            "After each chat turn, if the extractor saved new atoms, a toast surfaces "
            "'Aria saved N new memories' with one-click View → Memory Console."
        ),
        keywords=["memory pulse", "toast", "notification"],
    ),
    Feature(
        id="memory-relevance-ranker",
        name="Bin-aware relevance ranker (Phase 3)",
        surface="memory",
        aria_priority=4,
        public=True,
        shipped_at="2026-04-25",
        short_summary=(
            "Atoms are pulled into each prompt by a weighted score: bin priority + recency + "
            "evidence count + user_confirmed bonus. Not flat term-overlap."
        ),
        keywords=["relevance", "ranker", "injection"],
    ),
    Feature(
        id="memory-why-popover",
        name='"Why did Aria say this?" popover',
        surface="memory",
        aria_priority=3,
        public=True,
        shipped_at="2026-04-25",
        short_summary=(
            "Click the Why? button on any assistant reply to see exactly which atoms fed the "
            "prompt, color-coded by source mode."
        ),
        keywords=["why", "audit", "transparency"],
    ),
]


# ---- Chat / cognition core ------------------------------------------------

CHAT_FEATURES = [
    Feature(
        id="multi-engine-routing",
        name="Multi-engine routing (per-turn)",
        surface="chat",
        aria_priority=5,
        public=True,
        shipped_at="2026-03-15",
        short_summary=(
            "Switch between OpenAI (GPT-5.2 / 4o), Anthropic Claude (Sonnet 4.5), and Google "
            "Gemini (3 Flash / 3 Pro) on a per-turn basis. Engine chip in the footer."
        ),
        keywords=["multi-engine", "openai", "claude", "gemini", "routing"],
    ),
    Feature(
        id="vision-all-engines",
        name="Image vision across ALL engines",
        surface="chat",
        aria_priority=4,
        public=True,
        shipped_at="2026-04-25",
        short_summary=(
            "Photos sent to Aria are visible to OpenAI, Claude, AND Gemini (not just Gemini). "
            "Base64-encoded images via emergentintegrations ImageContent."
        ),
        keywords=["vision", "image", "multimodal"],
    ),
    Feature(
        id="wcw-meter",
        name="Working Context Window meter",
        surface="chat",
        aria_priority=3,
        public=True,
        shipped_at="2026-03-20",
        short_summary=(
            "Live token meter scaled to the active engine's real context limit. Clears on "
            "engine failure to avoid stale readings."
        ),
        keywords=["wcw", "context window", "token meter"],
    ),
    Feature(
        id="continuity-engine",
        name="Continuity engine (sanitization + compression + reinjection)",
        surface="chat",
        aria_priority=4,
        public=True,
        shipped_at="2026-03-01",
        short_summary=(
            "Every turn rebuilds the prompt from a deterministic plan: sanitize history, "
            "compress per lane, reinject memory + continuity packets. Auditable receipts."
        ),
        keywords=["continuity", "sanitization", "compression", "receipts"],
    ),
    Feature(
        id="multi-agent-mode",
        name="Multi-Agent Mode",
        surface="chat",
        aria_priority=3,
        public=True,
        shipped_at="2026-03-25",
        short_summary=(
            "Toggle on the Composer to run the same prompt through multiple engines in "
            "parallel and synthesize their replies."
        ),
        keywords=["multi-agent", "synthesis", "parallel"],
    ),
    Feature(
        id="swarm-supervisor-worker-critic",
        name="Agent Swarm (Supervisor → E2B Worker → Critic)",
        surface="chat",
        aria_priority=4,
        public=True,
        shipped_at="2026-04-01",
        short_summary=(
            "Multi-step task pipeline: Aria plans (Supervisor), an E2B sandbox executes "
            "(Worker), a separate model reviews (Critic). For tasks needing real code/web work."
        ),
        detail=(
            "Triggered from the Swarm panel in the Inspector menu. Each step is logged as an "
            "artifact you can audit. The Worker runs in an isolated E2B Firecracker micro-VM "
            "so it can't touch production. Critic step is gating — a failed review halts the "
            "pipeline."
        ),
        keywords=["swarm", "e2b", "supervisor", "critic", "agent pipeline"],
    ),
    Feature(
        id="aria-tools",
        name="Aria's tool belt",
        surface="chat",
        aria_priority=4,
        public=True,
        shipped_at="2026-03-10",
        short_summary=(
            "Aria can call read_file, list_dir, grep_code, web_fetch, github_fetch, and "
            "[FILE_TICKET]. Hard-cap of 3 tool calls per reply."
        ),
        keywords=["tools", "read_file", "web_fetch", "github_fetch"],
    ),
    Feature(
        id="receipts-audit",
        name="Per-turn context receipts",
        surface="chat",
        aria_priority=3,
        public=True,
        shipped_at="2026-03-08",
        short_summary=(
            "Every assistant reply has a saved receipt: terms, bins, retained / dropped / "
            "compressed message counts, lineage depth, reduction %. Inspectable in the UI."
        ),
        keywords=["receipts", "audit", "lineage"],
    ),
    Feature(
        id="error-bubble",
        name="Pydantic-sanitized error bubbles",
        surface="chat",
        aria_priority=1,
        public=False,
        shipped_at="2026-04-22",
        short_summary="Engine failures show a bounded, non-leaky error UI instead of raw stack traces.",
    ),
]


# ---- Voice ----------------------------------------------------------------

VOICE_FEATURES = [
    Feature(
        id="voice-stt-whisper",
        name="Voice input (Whisper STT)",
        surface="voice",
        aria_priority=3,
        public=True,
        shipped_at="2026-02-15",
        short_summary=(
            "Tap the mic in the Composer, dictate, transcribe via Whisper. Instant "
            "'Processing' indicator on stop."
        ),
        keywords=["voice", "stt", "whisper", "dictation"],
    ),
    Feature(
        id="voice-full-mode",
        name="Full Voice mode (hands-free loop)",
        surface="voice",
        aria_priority=3,
        public=True,
        shipped_at="2026-04-10",
        short_summary=(
            "Hands-free STT + TTS loop with visual rings — talk to Aria like a phone call, "
            "she replies aloud, mic re-arms automatically."
        ),
        keywords=["full voice", "hands-free", "tts"],
    ),
    Feature(
        id="voice-journals",
        name="Voice journals",
        surface="voice",
        aria_priority=2,
        public=True,
        shipped_at="2026-03-05",
        short_summary="Standalone voice notes saved separately from chat threads.",
    ),
    Feature(
        id="ambient-mode",
        name="Ambient mode (low-light theme)",
        surface="voice",
        aria_priority=1,
        public=True,
        shipped_at="2026-04-08",
        short_summary="Low-light theme toggle for late-night / always-visible usage.",
    ),
]


# ---- Quick Capture --------------------------------------------------------

CAPTURE_FEATURES = [
    Feature(
        id="quick-capture-inbox",
        name="Quick Capture inbox",
        surface="capture",
        aria_priority=4,
        public=True,
        shipped_at="2026-04-25",
        short_summary=(
            "Sticky-note inbox for dump-and-go thoughts. Type or dictate, file the thought, "
            "promote to a full chat thread later."
        ),
        keywords=["quick capture", "sticky note", "inbox", "adhd"],
    ),
    Feature(
        id="quick-capture-api-key",
        name="Personal API key for external ingest",
        surface="capture",
        aria_priority=3,
        public=True,
        shipped_at="2026-04-25",
        short_summary=(
            "One-click `caos_xxx` bearer token for Apple Shortcut / Bee pendant / custom "
            "scripts to POST captures from anywhere."
        ),
        keywords=["api key", "apple shortcut", "bee pendant", "ingest"],
    ),
    Feature(
        id="capture-promote-to-chat",
        name="Promote capture → chat thread",
        surface="capture",
        aria_priority=3,
        public=True,
        shipped_at="2026-04-25",
        short_summary=(
            "Any capture becomes a new CAOS thread pre-loaded with the captured text as the "
            "opening user message."
        ),
        keywords=["promote", "capture to chat"],
    ),
]


# ---- Connectors -----------------------------------------------------------

CONNECTOR_FEATURES = [
    Feature(
        id="connectors-hub",
        name="Connectors Hub (encrypted vault)",
        surface="connectors",
        aria_priority=4,
        public=True,
        shipped_at="2026-04-15",
        short_summary=(
            "Per-user OAuth/PAT vault encrypted with Fernet. Add/remove/rotate provider "
            "credentials from one drawer."
        ),
        keywords=["connectors", "oauth", "fernet", "vault"],
    ),
    Feature(
        id="connector-google-workspace",
        name="Google Workspace (Gmail / Drive / Calendar)",
        surface="connectors",
        aria_priority=3,
        public=True,
        shipped_at="2026-04-15",
        short_summary=(
            "OAuth 2.0 read-only access — Aria can search inbox, read Drive files, list "
            "calendar events. Send/compose intentionally NOT shipped."
        ),
        keywords=["gmail", "drive", "calendar", "google"],
    ),
    Feature(
        id="connector-github",
        name="GitHub PAT integration",
        surface="connectors",
        aria_priority=2,
        public=True,
        shipped_at="2026-04-12",
        short_summary=(
            "Personal Access Token in Settings → Aria has a `github_fetch` tool against "
            "your authenticated repos."
        ),
        keywords=["github", "pat", "github_fetch"],
    ),
    Feature(
        id="connector-mcp",
        name="MCP (Model Context Protocol) client",
        surface="connectors",
        aria_priority=3,
        public=True,
        shipped_at="2026-04-18",
        short_summary=(
            "Generic JSON-RPC client for any MCP server — Aria can talk to external tools "
            "and data sources without per-vendor glue code."
        ),
        keywords=["mcp", "model context protocol", "tools"],
    ),
    Feature(
        id="connector-obsidian",
        name="Obsidian vault search + backlinks",
        surface="connectors",
        aria_priority=2,
        public=True,
        shipped_at="2026-04-19",
        short_summary="Index your Obsidian vault for in-chat search and backlink resolution.",
    ),
    Feature(
        id="connector-slack",
        name="Slack outbound notifications",
        surface="connectors",
        aria_priority=2,
        public=True,
        shipped_at="2026-04-22",
        short_summary="Send messages to Slack channels via your token.",
    ),
    Feature(
        id="connector-twilio",
        name="Twilio SMS notifications",
        surface="connectors",
        aria_priority=2,
        public=True,
        shipped_at="2026-04-22",
        short_summary="Outbound SMS via Twilio.",
    ),
    Feature(
        id="connector-telegram",
        name="Telegram outbound notifications",
        surface="connectors",
        aria_priority=2,
        public=True,
        shipped_at="2026-04-22",
        short_summary="Outbound messages via Telegram bot tokens.",
    ),
]


# ---- Billing & accounts ---------------------------------------------------

BILLING_FEATURES = [
    Feature(
        id="pricing-tiers",
        name="Token-based freemium tiers",
        surface="billing",
        aria_priority=3,
        public=True,
        shipped_at="2026-04-22",
        short_summary="Free / Pro / Pro+ tiers with token quota tracking and per-engine spend.",
        keywords=["pricing", "freemium", "stripe"],
    ),
    Feature(
        id="stripe-checkout",
        name="Stripe billing checkout",
        surface="billing",
        aria_priority=3,
        public=True,
        shipped_at="2026-04-22",
        short_summary="In-app upgrade flow via Stripe Checkout sessions.",
    ),
    Feature(
        id="logout-per-device",
        name="Per-device logout",
        surface="system",
        aria_priority=1,
        public=False,
        shipped_at="2026-04-25",
        short_summary="Log out only the current browser; other devices stay signed in.",
    ),
    Feature(
        id="emergent-google-oauth",
        name="Emergent-managed Google sign-in",
        surface="system",
        aria_priority=2,
        public=True,
        shipped_at="2026-02-01",
        short_summary="One-tap Google sign-in via Emergent's OAuth handoff.",
    ),
]


# ---- Files & artifacts ----------------------------------------------------

FILE_FEATURES = [
    Feature(
        id="files-upload",
        name="File / photo upload",
        surface="files",
        aria_priority=3,
        public=True,
        shipped_at="2026-03-10",
        short_summary="Upload images, PDFs, txts, code files. Stored in object storage.",
    ),
    Feature(
        id="heic-auto-transcode",
        name="HEIC → JPEG auto-transcode",
        surface="files",
        aria_priority=2,
        public=True,
        shipped_at="2026-04-25",
        short_summary=(
            "iPhone photos uploaded as HEIC are auto-transcoded server-side to JPEG so "
            "browsers can render them inline."
        ),
        keywords=["heic", "heif", "iphone", "transcode"],
    ),
    Feature(
        id="image-lightbox-portal",
        name="Full-viewport image lightbox",
        surface="files",
        aria_priority=1,
        public=False,
        shipped_at="2026-04-25",
        short_summary=(
            "Lightbox renders via React Portal so the backdrop covers the full viewport "
            "regardless of ancestor stacking contexts."
        ),
    ),
]


# ---- Admin / ops ----------------------------------------------------------

ADMIN_FEATURES = [
    Feature(
        id="admin-dashboard",
        name="Admin Dashboard",
        surface="admin",
        aria_priority=1,
        public=False,
        shipped_at="2026-04-05",
        short_summary="Live spend tracking per engine, token usage charts, error log drill-down.",
    ),
    Feature(
        id="admin-docs",
        name="Admin documentation drawer",
        surface="admin",
        aria_priority=1,
        public=False,
        shipped_at="2026-04-08",
        short_summary="Internal docs viewer for admins.",
    ),
    Feature(
        id="support-tickets",
        name="Support ticket filing",
        surface="admin",
        aria_priority=2,
        public=True,
        shipped_at="2026-04-09",
        short_summary="In-app ticket form, emailed to ops via Resend.",
    ),
]


# ---- Discovery / SEO -----------------------------------------------------

DISCOVERY_FEATURES = [
    Feature(
        id="platform-topology-system-prompt",
        name="Platform topology in system prompt",
        surface="system",
        aria_priority=2,
        public=False,
        shipped_at="2026-04-25",
        short_summary=(
            "Aria's system prompt includes the full inventory of CAOS surfaces, bins, "
            "tools, and pipeline behaviors so she answers from facts, not guesses."
        ),
    ),
    Feature(
        id="llms-txt",
        name="llms.txt + JSON-LD structured data",
        surface="discovery",
        aria_priority=1,
        public=True,
        shipped_at="2026-04-25",
        short_summary=(
            "Public AI-readable description at /llms.txt + SoftwareApplication JSON-LD in "
            "<head> so ChatGPT, Perplexity, and Google AI Overviews understand CAOS "
            "correctly."
        ),
    ),
    Feature(
        id="feature-catalog-auto-sync",
        name="Auto-sync feature catalog",
        surface="system",
        aria_priority=2,
        public=False,
        shipped_at="2026-04-26",
        short_summary=(
            "Single source of truth (this file) feeds Aria's topology AND the public "
            "llms.txt — every shipped feature gets one entry, both surfaces auto-update."
        ),
    ),
]


# ---- Aggregator -----------------------------------------------------------

ALL_FEATURES: list[Feature] = (
    MEMORY_FEATURES
    + CHAT_FEATURES
    + VOICE_FEATURES
    + CAPTURE_FEATURES
    + CONNECTOR_FEATURES
    + BILLING_FEATURES
    + FILE_FEATURES
    + ADMIN_FEATURES
    + DISCOVERY_FEATURES
)


def public_features() -> list[Feature]:
    """Subset that should appear in the public llms.txt / JSON-LD."""
    return [f for f in ALL_FEATURES if f.public]


def aria_features(min_priority: int = 2) -> list[Feature]:
    """Subset that goes into Aria's system-prompt topology block.
    Filtered by priority to keep the prompt cost bounded."""
    return sorted(
        [f for f in ALL_FEATURES if f.aria_priority >= min_priority],
        key=lambda f: (-f.aria_priority, f.surface, f.id),
    )


def features_by_surface(features: list[Feature] | None = None) -> dict[str, list[Feature]]:
    """Group features by surface for nicer rendering."""
    rows = features if features is not None else ALL_FEATURES
    out: dict[str, list[Feature]] = {}
    for f in rows:
        out.setdefault(f.surface, []).append(f)
    for v in out.values():
        v.sort(key=lambda x: x.shipped_at, reverse=True)
    return out


def latest_features(n: int = 10) -> list[Feature]:
    """Most-recently-shipped features for the public 'What's new' section."""
    return sorted(ALL_FEATURES, key=lambda f: f.shipped_at, reverse=True)[:n]
