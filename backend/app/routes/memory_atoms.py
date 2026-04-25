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
