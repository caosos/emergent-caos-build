from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.db import collection
from app.schemas.caos import (
    ChatRequest,
    ChatResponse,
    ContextPrepareRequest,
    ContextPrepareResponse,
    ContextStats,
    MemoryEntry,
    MemorySaveRequest,
    MessageCreate,
    MessageRecord,
    SessionCreate,
    SessionRecord,
    UserProfileRecord,
    UserProfileUpsertRequest,
)
from app.services.chat_pipeline import run_chat_turn
from app.services.context_engine import (
    build_context_receipt,
    compress_history,
    extract_tags,
    rank_memories,
    sanitize_history,
)


router = APIRouter(prefix="/caos", tags=["caos"])


@router.post("/sessions", response_model=SessionRecord)
async def create_session(input: SessionCreate):
    session = SessionRecord(user_email=input.user_email, title=input.title)
    doc = session.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    await collection("sessions").insert_one(doc)
    return session


@router.get("/sessions", response_model=list[SessionRecord])
async def list_sessions(user_email: str):
    docs = await collection("sessions").find({"user_email": user_email}, {"_id": 0}).sort("updated_at", -1).to_list(200)
    return [SessionRecord(**doc) for doc in docs]


@router.post("/messages", response_model=MessageRecord)
async def create_message(input: MessageCreate):
    session = await collection("sessions").find_one({"session_id": input.session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    message = MessageRecord(**input.model_dump())
    doc = message.model_dump()
    doc["timestamp"] = doc["timestamp"].isoformat()
    await collection("messages").insert_one(doc)
    await collection("sessions").update_one(
        {"session_id": input.session_id},
        {"$set": {
            "last_message_preview": input.content[:140],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return message


@router.get("/sessions/{session_id}/messages", response_model=list[MessageRecord])
async def get_session_messages(session_id: str):
    docs = await collection("messages").find({"session_id": session_id}, {"_id": 0}).sort("timestamp", 1).to_list(1000)
    return [MessageRecord(**doc) for doc in docs]


@router.post("/profile/upsert", response_model=UserProfileRecord)
async def upsert_profile(input: UserProfileUpsertRequest):
    existing = await collection("user_profiles").find_one({"user_email": input.user_email}, {"_id": 0})
    if existing:
        updated = {
            **existing,
            **input.model_dump(exclude_none=True),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await collection("user_profiles").update_one({"user_email": input.user_email}, {"$set": updated})
        return UserProfileRecord(**updated)
    profile = UserProfileRecord(**input.model_dump())
    doc = profile.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    doc["structured_memory"] = []
    await collection("user_profiles").insert_one(doc)
    return profile


@router.post("/memory/save", response_model=MemoryEntry)
async def save_memory(input: MemorySaveRequest):
    profile = await collection("user_profiles").find_one({"user_email": input.user_email}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    memory = MemoryEntry(content=input.content, tags=input.tags or extract_tags(input.content))
    updated_memory = [*profile.get("structured_memory", []), {
        **memory.model_dump(),
        "created_at": memory.created_at.isoformat(),
    }]
    await collection("user_profiles").update_one(
        {"user_email": input.user_email},
        {"$set": {"structured_memory": updated_memory, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return memory


@router.post("/context/prepare", response_model=ContextPrepareResponse)
async def prepare_context(input: ContextPrepareRequest):
    profile = await collection("user_profiles").find_one({"user_email": input.user_email}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    docs = await collection("messages").find({"session_id": input.session_id}, {"_id": 0}).sort("timestamp", 1).to_list(1000)
    messages = [MessageRecord(**doc) for doc in docs]
    sanitized, stats = sanitize_history(messages)
    compressed = compress_history(sanitized, input.hot_head, input.hot_tail)
    memories = [MemoryEntry(**entry) for entry in profile.get("structured_memory", [])]
    injected_memories, retrieval_terms = rank_memories(input.query, compressed, memories, input.memory_limit)
    receipt = build_context_receipt(stats, messages, compressed, injected_memories, retrieval_terms)
    stats_payload = ContextStats(
        total_messages=stats["total_messages"],
        removed_duplicates=stats["removed_duplicates"],
        removed_low_signal=stats["removed_low_signal"],
        final_messages=len(compressed),
        estimated_chars_before=receipt["estimated_chars_before"],
        estimated_chars_after=receipt["estimated_chars_after"],
        reduction_ratio=receipt["reduction_ratio"],
    )
    return ContextPrepareResponse(
        session_id=input.session_id,
        query=input.query,
        sanitized_history=compressed,
        injected_memories=injected_memories,
        stats=stats_payload,
        receipt=receipt,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(input: ChatRequest):
    try:
        return await run_chat_turn(input)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error