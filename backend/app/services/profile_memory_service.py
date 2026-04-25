"""Profile memory service.

Owns the legacy `MemoryEntry` CRUD surface (used by Settings → Permanent
Memories) AND the new Memory Provenance Layer reads (Phase 1 of the Memory
Scaffolding Blueprint).

Legacy CRUD is preserved 1:1 for backwards-compat. The Phase 1 additions:
  - `list_memory_atoms`     → hydrate every profile memory into a `MemoryAtom`
                               (typed bin, source mode, confidence, etc.)
  - `count_atoms_by_bin`    → fast bin-tab counters for the Memory Console
  - `delete_memory_atom`    → user-override delete (re-uses delete_profile_memory)
  - `update_memory_atom`    → user-override edit (bin / content / priority)
  - `insert_extracted_atom` → autonomous-extractor write path (Phase 2)
  - `list_evidence_for_atom`/`add_evidence_for_atom` → memory_evidence ops
"""
from datetime import datetime, timezone

from app.db import collection
from app.schemas.caos import MemoryDeleteResponse, MemoryEntry, MemorySaveRequest, MemoryUpdateRequest, UserProfileRecord
from app.schemas.memory import (
    BIN_REGISTRY,
    MemoryAtom,
    MemoryBin,
    MemoryEvidence,
    MutationPolicy,
    SourceMode,
    hydrate_atom,
    migrate_legacy_bin,
)
from app.services.context_engine import extract_tags


def _memory_doc(memory: MemoryEntry) -> dict:
    doc = memory.model_dump()
    doc["created_at"] = memory.created_at.isoformat()
    doc["updated_at"] = memory.updated_at.isoformat()
    return doc


async def _get_or_create_profile(user_email: str) -> dict:
    profile = await collection("user_profiles").find_one({"user_email": user_email}, {"_id": 0})
    if profile:
        return profile
    record = UserProfileRecord(user_email=user_email)
    doc = record.model_dump()
    doc["created_at"] = record.created_at.isoformat()
    doc["updated_at"] = record.updated_at.isoformat()
    doc["structured_memory"] = []
    await collection("user_profiles").insert_one(doc)
    return doc


# ---- Legacy CRUD (kept 1:1) -----------------------------------------------


async def list_profile_memories(user_email: str, bin_name: str | None = None) -> list[MemoryEntry]:
    profile = await _get_or_create_profile(user_email)
    memories = [MemoryEntry(**entry) for entry in profile.get("structured_memory", [])]
    if bin_name:
        memories = [memory for memory in memories if memory.bin_name == bin_name]
    return memories


async def save_profile_memory(payload: MemorySaveRequest) -> MemoryEntry:
    profile = await _get_or_create_profile(payload.user_email)
    tags = payload.tags or extract_tags(payload.content)
    bin_name = payload.bin_name or (tags[0] if tags else "general")
    memory = MemoryEntry(
        content=payload.content,
        tags=tags,
        bin_name=bin_name,
        priority=payload.priority,
        source="user_saved",
    )
    updated_memory = [*profile.get("structured_memory", []), _memory_doc(memory)]
    await collection("user_profiles").update_one(
        {"user_email": payload.user_email},
        {"$set": {"structured_memory": updated_memory, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return memory


async def update_profile_memory(memory_id: str, payload: MemoryUpdateRequest) -> MemoryEntry:
    profile = await _get_or_create_profile(payload.user_email)
    updated_entries: list[dict] = []
    updated_memory: MemoryEntry | None = None
    for entry in profile.get("structured_memory", []):
        current = MemoryEntry(**entry)
        if current.id != memory_id:
            updated_entries.append(_memory_doc(current))
            continue
        tags = payload.tags if payload.tags is not None else current.tags
        if payload.content and payload.tags is None:
            tags = extract_tags(payload.content)
        updated_memory = MemoryEntry(
            id=current.id,
            content=payload.content or current.content,
            tags=tags,
            bin_name=payload.bin_name or current.bin_name,
            scope=current.scope,
            source=current.source,
            priority=payload.priority if payload.priority is not None else current.priority,
            created_at=current.created_at,
            updated_at=datetime.now(timezone.utc),
        )
        updated_entries.append(_memory_doc(updated_memory))
    if not updated_memory:
        raise ValueError("Memory not found")
    await collection("user_profiles").update_one(
        {"user_email": payload.user_email},
        {"$set": {"structured_memory": updated_entries, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return updated_memory


async def delete_profile_memory(user_email: str, memory_id: str) -> MemoryDeleteResponse:
    profile = await _get_or_create_profile(user_email)
    remaining = [entry for entry in profile.get("structured_memory", []) if entry.get("id") != memory_id]
    if len(remaining) == len(profile.get("structured_memory", [])):
        raise ValueError("Memory not found")
    await collection("user_profiles").update_one(
        {"user_email": user_email},
        {"$set": {"structured_memory": remaining, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    # Cascade evidence cleanup so the receipt UI doesn't surface dangling rows.
    await collection("memory_evidence").delete_many({"atom_id": memory_id, "user_email": user_email})
    return MemoryDeleteResponse(deleted_id=memory_id)


# ---- Phase 1: Memory Console (read-only hydrated view) --------------------


async def list_memory_atoms(user_email: str, bin_name: str | None = None) -> list[MemoryAtom]:
    """Hydrate every profile memory into a typed `MemoryAtom`.

    Old rows missing Phase-1 fields are auto-defaulted via `hydrate_atom`.
    Optional `bin_name` filter.
    """
    profile = await _get_or_create_profile(user_email)
    raw = profile.get("structured_memory", [])
    atoms: list[MemoryAtom] = [hydrate_atom(entry) for entry in raw]
    if bin_name:
        atoms = [a for a in atoms if a.bin_name == bin_name]
    # Sort: highest priority first, then most recently updated.
    atoms.sort(key=lambda a: (a.priority, a.updated_at), reverse=True)
    # Stitch evidence counts so the UI can show "3 evidence anchors" pills.
    if atoms:
        ids = [a.id for a in atoms]
        evidence_rows = await collection("memory_evidence").aggregate([
            {"$match": {"user_email": user_email, "atom_id": {"$in": ids}}},
            {"$group": {"_id": "$atom_id", "count": {"$sum": 1}}},
        ]).to_list(len(ids))
        counts = {row["_id"]: row["count"] for row in evidence_rows}
        for atom in atoms:
            stored = counts.get(atom.id, 0)
            # Take the larger of stored evidence rows or whatever was written
            # inline on the atom (some legacy rows may have higher inline count).
            atom.evidence_count = max(atom.evidence_count, stored)
    return atoms


def count_atoms_by_bin(atoms: list[MemoryAtom]) -> dict[str, int]:
    """Per-bin atom counts; every bin in the registry is keyed (so empty bins
    show as 0 in the UI)."""
    counts = {bin_id: 0 for bin_id in BIN_REGISTRY.keys()}
    for atom in atoms:
        bin_id = migrate_legacy_bin(atom.bin_name)
        counts[bin_id] = counts.get(bin_id, 0) + 1
    return counts


async def update_memory_atom(user_email: str, atom_id: str, *, bin_name: str | None = None,
                             content: str | None = None, priority: int | None = None) -> MemoryAtom:
    """User-override edit. Rewrites the inline structured_memory entry and
    returns the hydrated atom."""
    profile = await _get_or_create_profile(user_email)
    rows = profile.get("structured_memory", [])
    for entry in rows:
        if entry.get("id") != atom_id:
            continue
        if bin_name is not None:
            entry["bin_name"] = migrate_legacy_bin(bin_name)
        if content is not None:
            entry["content"] = content
        if priority is not None:
            entry["priority"] = max(0, min(100, int(priority)))
        entry["updated_at"] = datetime.now(timezone.utc).isoformat()
        await collection("user_profiles").update_one(
            {"user_email": user_email},
            {"$set": {"structured_memory": rows, "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return hydrate_atom(entry)
    raise ValueError("Memory atom not found")


async def confirm_memory_atom(user_email: str, atom_id: str) -> MemoryAtom:
    """Promote a candidate / DERIVED atom to user-confirmed status. Bumps
    confidence to 1.0 and locks mutation policy to EXPLICIT_ONLY."""
    profile = await _get_or_create_profile(user_email)
    rows = profile.get("structured_memory", [])
    for entry in rows:
        if entry.get("id") != atom_id:
            continue
        entry["user_confirmed"] = True
        entry["status"] = "active"
        entry["confidence"] = 1.0
        entry["source_mode"] = SourceMode.USER_EXPLICIT.value
        entry["mutation_policy"] = MutationPolicy.EXPLICIT_ONLY.value
        entry["updated_at"] = datetime.now(timezone.utc).isoformat()
        await collection("user_profiles").update_one(
            {"user_email": user_email},
            {"$set": {"structured_memory": rows, "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return hydrate_atom(entry)
    raise ValueError("Memory atom not found")


# ---- Phase 2: Autonomous extractor write path ------------------------------


async def insert_extracted_atom(user_email: str, *, content: str, bin_name: str,
                                 summary: str | None = None,
                                 source_session_id: str | None = None,
                                 source_message_id: str | None = None,
                                 confidence: float = 0.7,
                                 evidence_quote: str | None = None,
                                 evidence_strength: float = 0.7) -> MemoryAtom | None:
    """Insert an atom proposed by the autonomous extractor.

    De-dupes against the existing structured_memory by exact lower-cased
    content match. Returns the new atom (or None if it was a duplicate).
    Also writes a paired MemoryEvidence row anchoring the atom to the
    source message.
    """
    profile = await _get_or_create_profile(user_email)
    rows = profile.get("structured_memory", [])
    norm = (content or "").strip().lower()
    if not norm:
        return None
    for existing in rows:
        if (existing.get("content") or "").strip().lower() == norm:
            # Bump evidence on the existing atom and skip the insert.
            existing["evidence_count"] = int(existing.get("evidence_count", 0)) + 1
            existing["last_validated_at"] = datetime.now(timezone.utc).isoformat()
            await collection("user_profiles").update_one(
                {"user_email": user_email},
                {"$set": {"structured_memory": rows, "updated_at": datetime.now(timezone.utc).isoformat()}},
            )
            if source_message_id:
                await add_evidence_for_atom(
                    user_email,
                    atom_id=existing.get("id", ""),
                    source_type="current_turn",
                    source_ref=source_message_id,
                    quote_or_anchor=evidence_quote or content[:200],
                    evidence_strength=evidence_strength,
                )
            return None

    atom = MemoryAtom(
        content=content,
        summary=summary or content[:120],
        bin_name=migrate_legacy_bin(bin_name),
        priority=BIN_REGISTRY.get(migrate_legacy_bin(bin_name), {}).get("default_priority", 50),
        source="auto_extract",
        source_mode=SourceMode.DERIVED,
        confidence=max(0.0, min(1.0, float(confidence))),
        user_confirmed=False,
        mutation_policy=MutationPolicy.CANDIDATE_REVIEW,
        status="active",
        evidence_count=1,
    )
    doc = atom.model_dump()
    doc["created_at"] = atom.created_at.isoformat()
    doc["updated_at"] = atom.updated_at.isoformat()
    rows.append(doc)
    await collection("user_profiles").update_one(
        {"user_email": user_email},
        {"$set": {"structured_memory": rows, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    if source_message_id or source_session_id:
        await add_evidence_for_atom(
            user_email,
            atom_id=atom.id,
            source_type="current_turn",
            source_ref=source_message_id or source_session_id or "",
            quote_or_anchor=evidence_quote or content[:200],
            evidence_strength=evidence_strength,
        )
    return atom


# ---- Memory evidence ops --------------------------------------------------


async def list_evidence_for_atom(user_email: str, atom_id: str) -> list[MemoryEvidence]:
    docs = await collection("memory_evidence").find(
        {"user_email": user_email, "atom_id": atom_id},
        {"_id": 0},
    ).sort("created_at", -1).to_list(50)
    return [MemoryEvidence(**doc) for doc in docs]


async def add_evidence_for_atom(user_email: str, *, atom_id: str, source_type: str,
                                 source_ref: str, quote_or_anchor: str,
                                 precision: str = "summary_anchor",
                                 evidence_strength: float = 0.7) -> MemoryEvidence:
    evidence = MemoryEvidence(
        atom_id=atom_id,
        user_email=user_email,
        source_type=source_type,  # type: ignore[arg-type]
        source_ref=source_ref,
        quote_or_anchor=quote_or_anchor[:600],
        precision=precision,
        evidence_strength=max(0.0, min(1.0, float(evidence_strength))),
    )
    doc = evidence.model_dump()
    doc["created_at"] = evidence.created_at.isoformat()
    await collection("memory_evidence").insert_one(doc)
    return evidence
