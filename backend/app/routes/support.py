from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.db import collection
from app.routes.auth import require_user
from app.schemas.caos import (
    SupportTicketCreateRequest,
    SupportTicketRecord,
    SupportTicketUpdateRequest,
)

router = APIRouter(prefix="/caos/support", tags=["support"])


def _is_admin(user: dict) -> bool:
    return bool(user.get("is_admin") is True or user.get("role") == "admin")


async def _insert_ticket(
    user_email: str,
    session_id: str | None,
    category: str,
    title: str,
    description: str,
    source: str,
) -> SupportTicketRecord:
    """Shared writer used by the direct route AND by Aria's marker parser."""
    record = SupportTicketRecord(
        user_email=user_email,
        session_id=session_id,
        category=category,  # type: ignore[arg-type]
        title=title.strip()[:240] or "Untitled ticket",
        description=description.strip()[:6000],
        source=source,  # type: ignore[arg-type]
    )
    doc = record.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    await collection("support_tickets").insert_one(doc)
    return record


@router.post("/tickets", response_model=SupportTicketRecord)
async def create_ticket(payload: SupportTicketCreateRequest, user=Depends(require_user)):
    return await _insert_ticket(
        user_email=user["email"],
        session_id=payload.session_id,
        category=payload.category,
        title=payload.title,
        description=payload.description,
        source=payload.source,
    )


@router.get("/tickets", response_model=list[SupportTicketRecord])
async def list_tickets(user=Depends(require_user)):
    query: dict = {} if _is_admin(user) else {"user_email": user["email"]}
    docs = await collection("support_tickets").find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [SupportTicketRecord(**doc) for doc in docs]


@router.patch("/tickets/{ticket_id}", response_model=SupportTicketRecord)
async def update_ticket(ticket_id: str, payload: SupportTicketUpdateRequest, user=Depends(require_user)):
    existing = await collection("support_tickets").find_one({"id": ticket_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if not _is_admin(user) and existing["user_email"] != user["email"]:
        raise HTTPException(status_code=403, detail="Not your ticket")
    changes = payload.model_dump(exclude_none=True)
    if not changes:
        return SupportTicketRecord(**existing)
    # Non-admin users cannot write admin_notes.
    if not _is_admin(user):
        changes.pop("admin_notes", None)
    changes["updated_at"] = datetime.now(timezone.utc).isoformat()
    await collection("support_tickets").update_one({"id": ticket_id}, {"$set": changes})
    merged = {**existing, **changes}
    return SupportTicketRecord(**merged)
