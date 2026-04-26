"""Memory Console routes (Phase 1 Read-only + Phase 2 Edit/Confirm).

Owner-gated endpoints for the typed memory atom store. The legacy
`/api/caos/memory` namespace (MemoryEntry CRUD) lives in `memory_profile.py`
and is preserved untouched; this router lives at `/api/caos/memory/atoms`
so frontend code can adopt it incrementally.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.schemas.memory import (
    BIN_REGISTRY,
    MemoryAtomListResponse,
    MemoryEvidenceCreateRequest,
    MemoryEvidenceListResponse,
)
from app.services.auth_service import require_user
from app.services.memory_backfill_service import (
    count_unmined_for_user,
    get_active_job_for,
    get_job,
    schedule_full_backfill,
    schedule_session_backfill,
)
from app.services.profile_memory_service import (
    add_evidence_for_atom,
    confirm_memory_atom,
    count_atoms_by_bin,
    delete_profile_memory,
    list_evidence_for_atom,
    list_memory_atoms,
    update_memory_atom,
)


router = APIRouter(prefix="/caos/memory/atoms", tags=["caos-memory-atoms"])


def _ensure_owner(requested_email: str, user: dict) -> None:
    """Cross-check that the caller is asking about THEIR own memory only."""
    if (requested_email or "").strip().lower() != (user.get("email") or "").strip().lower():
        raise HTTPException(status_code=403, detail="Not your memory")


@router.get("", response_model=MemoryAtomListResponse)
async def get_memory_atoms(
    user_email: str,
    bin_name: str | None = None,
    user: dict = Depends(require_user),
):
    _ensure_owner(user_email, user)
    atoms = await list_memory_atoms(user_email, bin_name=bin_name)
    # Bin counts always reflect the FULL atom set, not the filtered view.
    if bin_name:
        all_atoms = await list_memory_atoms(user_email)
        bin_counts = count_atoms_by_bin(all_atoms)
        total = len(all_atoms)
    else:
        bin_counts = count_atoms_by_bin(atoms)
        total = len(atoms)
    return MemoryAtomListResponse(
        user_email=user_email,
        atoms=atoms,
        bin_counts=bin_counts,
        bin_registry=BIN_REGISTRY,
        total=total,
    )


@router.get("/{atom_id}/evidence", response_model=MemoryEvidenceListResponse)
async def get_memory_atom_evidence(
    atom_id: str,
    user_email: str,
    user: dict = Depends(require_user),
):
    _ensure_owner(user_email, user)
    evidence = await list_evidence_for_atom(user_email, atom_id)
    return MemoryEvidenceListResponse(atom_id=atom_id, evidence=evidence)


@router.post("/{atom_id}/evidence")
async def post_memory_atom_evidence(
    atom_id: str,
    payload: MemoryEvidenceCreateRequest,
    user: dict = Depends(require_user),
):
    _ensure_owner(payload.user_email, user)
    evidence = await add_evidence_for_atom(
        payload.user_email,
        atom_id=atom_id,
        source_type=payload.source_type.value,
        source_ref=payload.source_ref,
        quote_or_anchor=payload.quote_or_anchor,
        precision=payload.precision,
        evidence_strength=payload.evidence_strength,
    )
    return evidence


class MemoryAtomPatchRequest(BaseModel):
    user_email: str
    bin_name: str | None = None
    content: str | None = None
    priority: int | None = Field(default=None, ge=0, le=100)


@router.patch("/{atom_id}")
async def patch_memory_atom(
    atom_id: str,
    payload: MemoryAtomPatchRequest,
    user: dict = Depends(require_user),
):
    _ensure_owner(payload.user_email, user)
    try:
        atom = await update_memory_atom(
            payload.user_email,
            atom_id,
            bin_name=payload.bin_name,
            content=payload.content,
            priority=payload.priority,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return atom


class MemoryAtomConfirmRequest(BaseModel):
    user_email: str


@router.post("/{atom_id}/confirm")
async def confirm_memory_atom_route(
    atom_id: str,
    payload: MemoryAtomConfirmRequest,
    user: dict = Depends(require_user),
):
    _ensure_owner(payload.user_email, user)
    try:
        atom = await confirm_memory_atom(payload.user_email, atom_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return atom


@router.delete("/{atom_id}")
async def delete_memory_atom(
    atom_id: str,
    user_email: str,
    user: dict = Depends(require_user),
):
    _ensure_owner(user_email, user)
    try:
        return await delete_profile_memory(user_email, atom_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---- Backfill: mine past conversations into typed bins -------------------

class MemoryBackfillStartRequest(BaseModel):
    user_email: str
    session_id: str | None = None  # None = global per-user backfill


@router.get("/backfill/unmined-count")
async def get_unmined_count(
    user_email: str,
    session_id: str | None = None,
    user: dict = Depends(require_user),
):
    """Returns the count of past user messages that haven't been mined.
    Used by the Memory Console UI to label the 'Mine past conversations'
    button (e.g. 'Mine past conversations · 47 unmined')."""
    _ensure_owner(user_email, user)
    count = await count_unmined_for_user(user_email, session_id=session_id)
    active = get_active_job_for(user_email)
    return {
        "unmined": count,
        "active_job_id": active["job_id"] if active else None,
    }


@router.post("/backfill")
async def start_backfill(
    payload: MemoryBackfillStartRequest,
    user: dict = Depends(require_user),
):
    """Kick off a backfill job. Returns immediately with the job dict so
    the UI can poll `/backfill/status/{job_id}`."""
    _ensure_owner(payload.user_email, user)
    if payload.session_id:
        return schedule_session_backfill(payload.user_email, payload.session_id)
    return schedule_full_backfill(payload.user_email)


@router.get("/backfill/status/{job_id}")
async def backfill_status(
    job_id: str,
    user_email: str,
    user: dict = Depends(require_user),
):
    """Poll progress of a backfill job."""
    _ensure_owner(user_email, user)
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["user_email"] != user_email:
        raise HTTPException(status_code=403, detail="Not your job")
    return job
