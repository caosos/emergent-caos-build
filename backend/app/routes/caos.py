from pathlib import Path

from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.db import collection
from app.schemas.caos import (
    ChatRequest,
    ChatResponse,
    ContinuityResponse,
    ContextPrepareRequest,
    ContextPrepareResponse,
    ContextStats,
    MemoryEntry,
    MemorySaveRequest,
    MessageCreate,
    MessageRecord,
    ReceiptRecord,
    SeedRecord,
    SessionCreate,
    SessionArtifactsResponse,
    SessionRecord,
    SummaryRecord,
    RuntimePreferences,
    RuntimeSettingsResponse,
    RuntimeSettingsUpsertRequest,
    RuntimeProviderRecord,
    TTSRequest,
    TTSResponse,
    TranscriptionResponse,
    VoicePreferences,
    VoiceSettingsResponse,
    VoiceSettingsUpsertRequest,
    LinkCreateRequest,
    UserFileRecord,
    UserProfileRecord,
    UserProfileUpsertRequest,
)
from app.services.file_storage import build_link_record, save_upload_to_disk
from app.services.chat_pipeline import run_chat_turn
from app.services.context_engine import (
    build_context_receipt,
    compress_history,
    extract_tags,
    rank_memories,
    sanitize_history,
)
from app.services.runtime_service import build_runtime_settings_response, get_provider_catalog
from app.services.thread_title_service import is_generic_session_title
from app.services.voice_service import generate_tts_base64, transcribe_upload


router = APIRouter(prefix="/caos", tags=["caos"])


@router.post("/sessions", response_model=SessionRecord)
async def create_session(input: SessionCreate):
    session = SessionRecord(
        user_email=input.user_email,
        title=input.title,
        title_source="auto" if is_generic_session_title(input.title) else "user",
        lane=input.lane,
    )
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


@router.get("/sessions/{session_id}/artifacts", response_model=SessionArtifactsResponse)
async def get_session_artifacts(session_id: str):
    receipt_docs = await collection("receipts").find({"session_id": session_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    summary_docs = await collection("thread_summaries").find({"session_id": session_id}, {"_id": 0}).sort("created_at", -1).to_list(25)
    seed_docs = await collection("context_seeds").find({"session_id": session_id}, {"_id": 0}).sort("created_at", -1).to_list(25)
    return SessionArtifactsResponse(
        receipts=[ReceiptRecord(**doc) for doc in receipt_docs],
        summaries=[SummaryRecord(**doc) for doc in summary_docs],
        seeds=[SeedRecord(**doc) for doc in seed_docs],
    )


@router.get("/sessions/{session_id}/continuity", response_model=ContinuityResponse)
async def get_session_continuity(session_id: str):
    latest_receipt_doc = await collection("receipts").find_one({"session_id": session_id}, {"_id": 0}, sort=[("created_at", -1)])
    latest_summary_doc = await collection("thread_summaries").find_one({"session_id": session_id}, {"_id": 0}, sort=[("created_at", -1)])
    latest_seed_doc = await collection("context_seeds").find_one({"session_id": session_id}, {"_id": 0}, sort=[("created_at", -1)])
    lineage_depth = max(
        latest_receipt_doc.get("lineage_depth", 0) if latest_receipt_doc else 0,
        latest_summary_doc.get("lineage_depth", 0) if latest_summary_doc else 0,
        latest_seed_doc.get("lineage_depth", 0) if latest_seed_doc else 0,
    )
    return ContinuityResponse(
        session_id=session_id,
        latest_summary=SummaryRecord(**latest_summary_doc) if latest_summary_doc else None,
        latest_seed=SeedRecord(**latest_seed_doc) if latest_seed_doc else None,
        latest_receipt=ReceiptRecord(**latest_receipt_doc) if latest_receipt_doc else None,
        lineage_depth=lineage_depth,
    )


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


@router.get("/profile/{user_email}", response_model=UserProfileRecord)
async def get_profile(user_email: str):
    profile = await collection("user_profiles").find_one({"user_email": user_email}, {"_id": 0})
    if not profile:
        return UserProfileRecord(user_email=user_email)
    return UserProfileRecord(**profile)


@router.get("/runtime/catalog", response_model=list[RuntimeProviderRecord])
async def get_runtime_catalog():
    return get_provider_catalog()


@router.get("/runtime/settings/{user_email}", response_model=RuntimeSettingsResponse)
async def get_runtime_settings(user_email: str):
    profile = await collection("user_profiles").find_one({"user_email": user_email}, {"_id": 0})
    preferences = RuntimePreferences(**(profile or {}).get("runtime_preferences", {}))
    return build_runtime_settings_response(user_email, preferences)


@router.post("/runtime/settings", response_model=RuntimeSettingsResponse)
async def upsert_runtime_settings(input: RuntimeSettingsUpsertRequest):
    existing = await collection("user_profiles").find_one({"user_email": input.user_email}, {"_id": 0})
    preferences = RuntimePreferences(
        key_source=input.key_source,
        default_provider=input.default_provider,
        default_model=input.default_model,
        enabled_providers=input.enabled_providers,
    )
    if existing:
        await collection("user_profiles").update_one(
            {"user_email": input.user_email},
            {"$set": {"runtime_preferences": preferences.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
    else:
        profile = UserProfileRecord(user_email=input.user_email, runtime_preferences=preferences)
        doc = profile.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        doc["updated_at"] = doc["updated_at"].isoformat()
        doc["structured_memory"] = []
        doc["runtime_preferences"] = preferences.model_dump()
        await collection("user_profiles").insert_one(doc)
    return build_runtime_settings_response(input.user_email, preferences)


@router.get("/voice/settings/{user_email}", response_model=VoiceSettingsResponse)
async def get_voice_settings(user_email: str):
    profile = await collection("user_profiles").find_one({"user_email": user_email}, {"_id": 0})
    preferences = VoicePreferences(**(profile or {}).get("voice_preferences", {}))
    return VoiceSettingsResponse(user_email=user_email, voice_preferences=preferences)


@router.post("/voice/settings", response_model=VoiceSettingsResponse)
async def upsert_voice_settings(input: VoiceSettingsUpsertRequest):
    preferences = VoicePreferences(**input.model_dump(exclude={"user_email"}))
    existing = await collection("user_profiles").find_one({"user_email": input.user_email}, {"_id": 0})
    if existing:
        await collection("user_profiles").update_one(
            {"user_email": input.user_email},
            {"$set": {"voice_preferences": preferences.model_dump(), "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
    else:
        profile = UserProfileRecord(user_email=input.user_email, voice_preferences=preferences)
        doc = profile.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        doc["updated_at"] = doc["updated_at"].isoformat()
        doc["structured_memory"] = []
        doc["runtime_preferences"] = profile.runtime_preferences.model_dump()
        doc["voice_preferences"] = preferences.model_dump()
        await collection("user_profiles").insert_one(doc)
    return VoiceSettingsResponse(user_email=input.user_email, voice_preferences=preferences)


@router.get("/files", response_model=list[UserFileRecord])
async def list_files(user_email: str, kind: str | None = None, session_id: str | None = None):
    query = {"user_email": user_email}
    if kind:
        query["kind"] = kind
    if session_id:
        query["session_id"] = session_id
    docs = await collection("user_files").find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return [UserFileRecord(**doc) for doc in docs]


@router.post("/files/upload", response_model=UserFileRecord)
async def upload_file(
    user_email: str = Form(...),
    session_id: str | None = Form(default=None),
    file: UploadFile = File(...),
):
    metadata = save_upload_to_disk(file, user_email, session_id)
    metadata["url"] = f"/api/caos/files/{metadata['id']}/download"
    await collection("user_files").insert_one(metadata)
    return UserFileRecord(**metadata)


@router.post("/files/link", response_model=UserFileRecord)
async def save_link(input: LinkCreateRequest):
    record = build_link_record(input.user_email, input.url, input.label, input.session_id)
    await collection("user_files").insert_one(record)
    return UserFileRecord(**record)


@router.get("/files/{file_id}/download")
async def download_file(file_id: str):
    record = await collection("user_files").find_one({"id": file_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    if record.get("kind") == "link":
        raise HTTPException(status_code=400, detail="Links do not have downloadable files")
    file_path = Path(record["storage_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Stored file is missing")
    return FileResponse(path=file_path, media_type=record.get("mime_type"), filename=record.get("name"))


@router.post("/memory/save", response_model=MemoryEntry)
async def save_memory(input: MemorySaveRequest):
    profile = await collection("user_profiles").find_one({"user_email": input.user_email}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    tags = input.tags or extract_tags(input.content)
    memory = MemoryEntry(content=input.content, tags=tags, bin_name=tags[0] if tags else "general")
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
        print(f"CAOS chat pipeline error: {error}")
        raise HTTPException(status_code=500, detail="CAOS chat pipeline failed") from error


@router.post("/voice/tts", response_model=TTSResponse)
async def text_to_speech(input: TTSRequest):
    return TTSResponse(**(await generate_tts_base64(input.text, input.voice, input.speed, input.model)))


@router.post("/voice/transcribe", response_model=TranscriptionResponse)
async def speech_to_text(
    file: UploadFile = File(...),
    user_email: str | None = Form(default=None),
    model: str = Form(default="gpt-4o-transcribe"),
    fallback_model: str = Form(default="whisper-1"),
    language: str | None = Form(default="en"),
    prompt: str | None = Form(default=None),
):
    profile = None
    if user_email:
        profile = await collection("user_profiles").find_one({"user_email": user_email}, {"_id": 0})
    preferences = VoicePreferences(**(profile or {}).get("voice_preferences", {}))
    data = await transcribe_upload(
        file,
        model=model or preferences.stt_primary_model,
        fallback_model=fallback_model or preferences.stt_fallback_model,
        language=language or preferences.stt_language,
        prompt=prompt,
    )
    return TranscriptionResponse(
        text=data["text"],
        model_used=data["model_used"],
        fallback_used=data["fallback_used"],
    )