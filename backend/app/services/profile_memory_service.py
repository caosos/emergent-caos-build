from datetime import datetime, timezone

from app.db import collection
from app.schemas.caos import MemoryDeleteResponse, MemoryEntry, MemorySaveRequest, MemoryUpdateRequest, UserProfileRecord
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
    return MemoryDeleteResponse(deleted_id=memory_id)