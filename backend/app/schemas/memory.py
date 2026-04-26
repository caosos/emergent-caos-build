"""Memory taxonomy + Pydantic schemas for the CAOS Memory Provenance Layer.

Per the user's blueprint (`docs/MEMORY_BLUEPRINT.md` — full text in chat
history). Phase 1 ships:
  - 13 typed memory bins (the Bin enum)
  - MemoryAtom (extends the legacy `MemoryEntry` shape — fields are
    additive, no breaking changes for already-stored rows)
  - MemoryEvidence (separate collection, links atoms to source anchors)

NOT in Phase 1 (deferred to later phases):
  - MemoryReceipt (per-turn audit log)             → Phase 2
  - MemoryCandidate (review queue items)            → Phase 4
  - MemoryInjectionPolicy / MemoryPackBuilder       → Phase 3
  - Counterevidence linking + Derived-trait engine  → Phase 5
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    from datetime import timezone
    return datetime.now(timezone.utc)


class MemoryBin(str, Enum):
    """The 13 typed memory bins from the user's blueprint.

    The bin is the *category* of a memory atom — separate from `priority`
    (numeric weight) and `tags` (free-form labels). The bin determines:
      - default injection priority during prompt build
      - whether the atom is allowed to be inferred (vs requires explicit
        user confirmation)
      - default sensitivity (some bins like RISK_SIGNAL are gated)

    Legacy values (`general`, anything not listed) are auto-classified by
    `migrate_legacy_bin` below so existing user_profiles continue to work.
    """
    IDENTITY_FACT = "IDENTITY_FACT"
    ACTIVE_PROJECT = "ACTIVE_PROJECT"
    OPERATING_PREFERENCE = "OPERATING_PREFERENCE"
    GOVERNANCE_RULE = "GOVERNANCE_RULE"
    BEHAVIORAL_PATTERN = "BEHAVIORAL_PATTERN"
    DERIVED_TRAIT = "DERIVED_TRAIT"
    DOMAIN_CONTEXT = "DOMAIN_CONTEXT"
    TECHNICAL_STATE = "TECHNICAL_STATE"
    REAL_WORLD_CONTEXT = "REAL_WORLD_CONTEXT"
    LEARNING_PROFILE = "LEARNING_PROFILE"
    RELATIONSHIP_BOUNDARY = "RELATIONSHIP_BOUNDARY"
    RISK_SIGNAL = "RISK_SIGNAL"
    COUNTEREVIDENCE = "COUNTEREVIDENCE"
    GENERAL = "GENERAL"  # fallback for unclassified atoms


# Per the blueprint: each bin has a default injection priority + governance.
BIN_REGISTRY: dict[str, dict] = {
    MemoryBin.IDENTITY_FACT.value: {
        "default_priority": 95, "allows_inference": False,
        "requires_user_confirmation": True, "sensitivity": "normal",
        "description": "Stable facts explicitly provided by the user (name, project, role).",
    },
    MemoryBin.ACTIVE_PROJECT.value: {
        "default_priority": 90, "allows_inference": False,
        "requires_user_confirmation": True, "sensitivity": "normal",
        "description": "Live workstreams or products the user is actively building.",
    },
    MemoryBin.OPERATING_PREFERENCE.value: {
        "default_priority": 95, "allows_inference": False,
        "requires_user_confirmation": True, "sensitivity": "normal",
        "description": "How the user wants the system to behave (truth-first, evidence-first, etc.).",
    },
    MemoryBin.GOVERNANCE_RULE.value: {
        "default_priority": 100, "allows_inference": False,
        "requires_user_confirmation": True, "sensitivity": "normal",
        "description": "Hard procedural rules (inspect-before-write, blueprint-first, receipts required).",
    },
    MemoryBin.BEHAVIORAL_PATTERN.value: {
        "default_priority": 70, "allows_inference": True,
        "requires_user_confirmation": False, "sensitivity": "normal",
        "description": "Repeated observed user behavior. NOT identity — observation only.",
    },
    MemoryBin.DERIVED_TRAIT.value: {
        "default_priority": 55, "allows_inference": True,
        "requires_user_confirmation": False, "sensitivity": "medium",
        "description": "Higher-order interpretation derived from multiple behavioral patterns. Inject with qualified language only.",
    },
    MemoryBin.DOMAIN_CONTEXT.value: {
        "default_priority": 75, "allows_inference": True,
        "requires_user_confirmation": False, "sensitivity": "normal",
        "description": "Recurring knowledge domains the user works in (React, elder care, observability, etc.).",
    },
    MemoryBin.TECHNICAL_STATE.value: {
        "default_priority": 75, "allows_inference": True,
        "requires_user_confirmation": False, "sensitivity": "normal",
        "description": "Current/recent system state. Has expiry and revalidation.",
    },
    MemoryBin.REAL_WORLD_CONTEXT.value: {
        "default_priority": 50, "allows_inference": True,
        "requires_user_confirmation": False, "sensitivity": "normal",
        "description": "Non-sensitive real-world operating context (workplace, hands-on background, etc.).",
    },
    MemoryBin.LEARNING_PROFILE.value: {
        "default_priority": 60, "allows_inference": True,
        "requires_user_confirmation": False, "sensitivity": "normal",
        "description": "How the user learns and collaborates.",
    },
    MemoryBin.RELATIONSHIP_BOUNDARY.value: {
        "default_priority": 90, "allows_inference": False,
        "requires_user_confirmation": True, "sensitivity": "high",
        "description": "Declared relationship model with AI. Important for safe personalization.",
    },
    MemoryBin.RISK_SIGNAL.value: {
        "default_priority": 40, "allows_inference": True,
        "requires_user_confirmation": False, "sensitivity": "high",
        "description": "Caution flags — never a diagnosis. Gated; requires counterevidence pairing.",
    },
    MemoryBin.COUNTEREVIDENCE.value: {
        "default_priority": 60, "allows_inference": False,
        "requires_user_confirmation": False, "sensitivity": "normal",
        "description": "Evidence that limits or corrects another atom. Critical for honest memory.",
    },
    MemoryBin.GENERAL.value: {
        "default_priority": 50, "allows_inference": True,
        "requires_user_confirmation": False, "sensitivity": "normal",
        "description": "Unclassified — should be migrated into a typed bin during review.",
    },
}


# ---- Source modes ----------------------------------------------------------

class SourceMode(str, Enum):
    """How the atom got into memory. The user-facing 4-level claim taxonomy:

      - USER_EXPLICIT  → user said it directly ("I'm Michael")
      - OBSERVED       → repeated user behavior across turns
      - DERIVED        → higher-order inference from multiple atoms
      - SYSTEM         → CAOS itself produced this (e.g. governance rules)

    Maps 1:1 to the blueprint's "USER-STATED / OBSERVED-PATTERN /
    DERIVED-INFERENCE / UNVERIFIED" labels surfaced in the receipt UI.
    """
    USER_EXPLICIT = "USER_EXPLICIT"
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    SYSTEM = "SYSTEM"


class MutationPolicy(str, Enum):
    """When the atom can be modified.

      - explicit_only       → only with user confirmation (governance, identity)
      - candidate_review    → can be auto-suggested, user must approve
      - auto_evidence_only  → may have evidence appended/confidence updated
                              automatically, but the summary cannot be
                              rewritten without review
    """
    EXPLICIT_ONLY = "explicit_only"
    CANDIDATE_REVIEW = "candidate_review"
    AUTO_EVIDENCE_ONLY = "auto_evidence_only"


# ---- MemoryEvidence (separate collection) ---------------------------------

class EvidenceSourceType(str, Enum):
    CURRENT_TURN = "current_turn"
    CONVERSATION_SUMMARY = "conversation_summary"
    SAVED_MEMORY = "saved_memory"
    UPLOADED_FILE = "uploaded_file"
    DRIVE_DOC = "drive_doc"
    GITHUB_FILE = "github_file"
    MANUAL_USER_CONFIRMATION = "manual_user_confirmation"
    SYSTEM_OBSERVATION = "system_observation"


class MemoryEvidence(BaseModel):
    """One evidence anchor for a memory atom.

    Stored separately from the atom (in `memory_evidence` collection) so a
    single atom can accumulate evidence over time without bloating the
    user_profile document.
    """
    id: str = Field(default_factory=lambda: f"ev_{uuid.uuid4().hex[:12]}")
    atom_id: str
    user_email: str
    source_type: EvidenceSourceType
    source_ref: str  # session_id, file_path, message_id, etc.
    quote_or_anchor: str  # exact quote OR human-readable summary anchor
    precision: str = "summary_anchor"  # exact_quote | summary_anchor
    evidence_strength: float = 0.7  # 0..1
    created_at: datetime = Field(default_factory=_utc_now)
    # ---- Provenance enrichment (read-side only — populated by
    # `list_evidence_for_atom` via JOINs against sessions/messages, never
    # written directly). Lets the UI show "From: 'Marketing chat' on Apr 22"
    # instead of just an opaque message_id.
    source_session_id: Optional[str] = None
    source_session_title: Optional[str] = None
    source_message_timestamp: Optional[str] = None
    source_message_role: Optional[str] = None


# ---- Atom shape (extended MemoryEntry — keeps wire compat) ----------------
#
# Phase 1 strategy: instead of breaking the existing `MemoryEntry` model
# (which is embedded in user_profile.structured_memory across users), we
# layer the Memory Provenance Layer fields ON TOP. Old rows are read with
# the new fields defaulted; `migrate_legacy_bin` snaps `bin_name` strings
# onto the typed enum on read.

class MemoryAtom(BaseModel):
    """Atomic memory unit — superset of the legacy MemoryEntry fields.

    Backward compatible with `MemoryEntry`: id/content/tags/bin_name/scope
    /source/priority/created_at/updated_at are kept exactly. New fields
    are additive with safe defaults so existing rows in `user_profiles
    .structured_memory` parse cleanly without migration writes.
    """
    # Legacy fields (kept identical to MemoryEntry for read-compat).
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    tags: list[str] = Field(default_factory=list)
    bin_name: str = MemoryBin.GENERAL.value
    scope: str = "profile"
    source: str = "user_trigger"
    priority: int = 50
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)
    # Phase 1 additions.
    summary: Optional[str] = None  # one-line label, distinct from full content
    label: Optional[str] = None    # short canonical name (lowercase_underscored)
    confidence: float = 1.0
    user_confirmed: bool = True
    source_mode: SourceMode = SourceMode.USER_EXPLICIT
    sensitivity: str = "normal"
    mutation_policy: MutationPolicy = MutationPolicy.EXPLICIT_ONLY
    evidence_count: int = 0
    last_validated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    requires_revalidation: bool = False
    counters: list[str] = Field(default_factory=list)  # ids of atoms this counters
    derived_from: list[str] = Field(default_factory=list)  # ids of atoms this was derived from
    injection_scope: list[str] = Field(default_factory=list)
    status: str = "active"  # active | candidate | expired | archived


# ---- Migration helpers ----------------------------------------------------

# Legacy bin names → typed bins. Best-effort classification used at read time
# (and once during the explicit migration pass) so existing memory survives.
LEGACY_BIN_REMAP = {
    "general":              MemoryBin.GENERAL.value,
    "preferences":          MemoryBin.OPERATING_PREFERENCE.value,
    "preference":           MemoryBin.OPERATING_PREFERENCE.value,
    "project":              MemoryBin.ACTIVE_PROJECT.value,
    "active_project":       MemoryBin.ACTIVE_PROJECT.value,
    "identity":             MemoryBin.IDENTITY_FACT.value,
    "fact":                 MemoryBin.IDENTITY_FACT.value,
    "rule":                 MemoryBin.GOVERNANCE_RULE.value,
    "rules":                MemoryBin.GOVERNANCE_RULE.value,
    "governance":           MemoryBin.GOVERNANCE_RULE.value,
    "behavior":             MemoryBin.BEHAVIORAL_PATTERN.value,
    "pattern":              MemoryBin.BEHAVIORAL_PATTERN.value,
    "domain":               MemoryBin.DOMAIN_CONTEXT.value,
    "tech":                 MemoryBin.TECHNICAL_STATE.value,
    "technical":            MemoryBin.TECHNICAL_STATE.value,
}


def migrate_legacy_bin(bin_name: str | None) -> str:
    """Snap any legacy bin_name onto the typed enum. Returns the enum string."""
    if not bin_name:
        return MemoryBin.GENERAL.value
    if bin_name in {b.value for b in MemoryBin}:
        return bin_name
    return LEGACY_BIN_REMAP.get(bin_name.lower(), MemoryBin.GENERAL.value)


def migrate_legacy_source(legacy_source: str | None) -> SourceMode:
    """Map the legacy `source` string onto the typed SourceMode enum."""
    if not legacy_source:
        return SourceMode.USER_EXPLICIT
    legacy = legacy_source.lower()
    if legacy in {"user_saved", "user_trigger", "manual_user_confirmation"}:
        return SourceMode.USER_EXPLICIT
    if legacy in {"observed", "behavioral_pattern"}:
        return SourceMode.OBSERVED
    if legacy in {"derived", "inferred"}:
        return SourceMode.DERIVED
    return SourceMode.SYSTEM


def hydrate_atom(raw: dict) -> MemoryAtom:
    """Read a raw user_profile.structured_memory row into a MemoryAtom.

    Adds defaults for any missing Phase-1 fields so old rows parse cleanly.
    """
    raw = dict(raw or {})
    raw["bin_name"] = migrate_legacy_bin(raw.get("bin_name"))
    raw.setdefault("source_mode", migrate_legacy_source(raw.get("source")).value)
    raw.setdefault("user_confirmed", True)
    raw.setdefault("confidence", 1.0)
    raw.setdefault("status", "active")
    raw.setdefault("mutation_policy", MutationPolicy.EXPLICIT_ONLY.value)
    return MemoryAtom(**raw)


# ---- Request/response shapes for new routes -------------------------------

class MemoryAtomListResponse(BaseModel):
    user_email: str
    atoms: list[MemoryAtom] = Field(default_factory=list)
    bin_counts: dict[str, int] = Field(default_factory=dict)
    bin_registry: dict[str, dict] = Field(default_factory=lambda: BIN_REGISTRY)
    total: int = 0


class MemoryAtomCreateRequest(BaseModel):
    user_email: str
    content: str
    bin_name: str
    summary: Optional[str] = None
    label: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    priority: Optional[int] = None
    source_mode: SourceMode = SourceMode.USER_EXPLICIT
    user_confirmed: bool = True
    confidence: float = 1.0
    sensitivity: str = "normal"
    mutation_policy: MutationPolicy = MutationPolicy.EXPLICIT_ONLY
    injection_scope: list[str] = Field(default_factory=list)


class MemoryEvidenceCreateRequest(BaseModel):
    atom_id: str
    user_email: str
    source_type: EvidenceSourceType = EvidenceSourceType.MANUAL_USER_CONFIRMATION
    source_ref: str
    quote_or_anchor: str
    precision: str = "summary_anchor"
    evidence_strength: float = 0.7


class MemoryEvidenceListResponse(BaseModel):
    atom_id: str
    evidence: list[MemoryEvidence] = Field(default_factory=list)
