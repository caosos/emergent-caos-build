import uuid
from datetime import datetime, timezone

from emergentintegrations.llm.chat import LlmChat, UserMessage

from app.db import collection
from app.schemas.caos import (
    ChatRequest,
    ChatResponse,
    MessageRecord,
    SeedRecord,
    SummaryRecord,
    UserProfileRecord,
)
from app.services.artifact_builder import build_receipt_record, build_seed_record, build_summary_record
from app.services.continuity_service import build_continuity_packet, derive_subject_bins
from app.services.context_engine import (
    build_context_receipt,
    compress_history,
    enforce_history_token_budget,
    rank_memories,
    sanitize_history,
)
from app.services.global_info_service import select_global_info_entries, upsert_global_info_entry
from app.services.memory_worker_service import derive_lane, list_lane_workers, rebuild_lane_workers
from app.services.prompt_builder import build_prompt_sections, build_system_prompt_from_sections
from app.services.runtime_service import resolve_chat_runtime
from app.services.token_meter import build_token_receipt
from app.services.thread_title_service import build_auto_thread_title, is_generic_session_title


async def run_chat_turn(payload: ChatRequest) -> ChatResponse:
    session = await collection("sessions").find_one({"session_id": payload.session_id}, {"_id": 0})
    if not session:
        raise ValueError("Session not found")

    profile_doc = await collection("user_profiles").find_one({"user_email": payload.user_email}, {"_id": 0})
    if not profile_doc:
        profile = UserProfileRecord(user_email=payload.user_email)
        doc = profile.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        doc["updated_at"] = doc["updated_at"].isoformat()
        doc["structured_memory"] = []
        await collection("user_profiles").insert_one(doc)
    else:
        profile = UserProfileRecord(**profile_doc)

    user_message = MessageRecord(session_id=payload.session_id, role="user", content=payload.content)
    user_doc = user_message.model_dump()
    user_doc["timestamp"] = user_doc["timestamp"].isoformat()
    await collection("messages").insert_one(user_doc)

    docs = await collection("messages").find({"session_id": payload.session_id}, {"_id": 0}).sort("timestamp", 1).to_list(1000)
    messages = [MessageRecord(**doc) for doc in docs]
    history_messages = messages[:-1] if messages and messages[-1].id == user_message.id else messages
    runtime = resolve_chat_runtime(profile, payload.provider, payload.model)
    sanitized, stats = sanitize_history(history_messages)
    compressed = compress_history(sanitized, payload.hot_head, payload.hot_tail)
    compressed, budget_stats = enforce_history_token_budget(compressed, runtime["model"], payload.history_token_budget)
    stats.update(budget_stats)
    memories = list(profile.structured_memory)
    subject_bins = derive_subject_bins(payload.content, compressed)
    session_lane = derive_lane(subject_bins, session.get("title"), session.get("lane"))
    injected_memories, retrieval_terms = rank_memories(payload.content, compressed, memories, payload.memory_limit, subject_bins)
    subject_bins = derive_subject_bins(payload.content, compressed, injected_memories)
    user_session_docs = await collection("sessions").find({"user_email": payload.user_email}, {"_id": 0}).to_list(200)
    session_ids = [doc["session_id"] for doc in user_session_docs]
    summary_docs = await collection("thread_summaries").find({"session_id": {"$in": session_ids}}, {"_id": 0}).sort("created_at", -1).to_list(120)
    seed_docs = await collection("context_seeds").find({"session_id": {"$in": session_ids}}, {"_id": 0}).sort("created_at", -1).to_list(120)
    workers = await list_lane_workers(payload.user_email)
    if not workers:
        workers = await rebuild_lane_workers(payload.user_email)
    continuity_packet = build_continuity_packet(
        payload.content,
        subject_bins,
        [SummaryRecord(**doc) for doc in summary_docs],
        [SeedRecord(**doc) for doc in seed_docs],
        workers=workers,
        lane=session_lane,
        session_id=payload.session_id,
    )
    global_info_entries = await select_global_info_entries(payload.user_email, payload.content, subject_bins, session_lane)
    receipt = build_context_receipt(
        stats,
        history_messages,
        compressed,
        injected_memories,
        retrieval_terms,
        subject_bins,
        continuity_packet,
        global_info_entries,
    )
    prompt_sections = build_prompt_sections(profile, compressed, injected_memories, continuity_packet, [entry.model_dump() for entry in global_info_entries])
    system_prompt = build_system_prompt_from_sections(prompt_sections)

    chat = LlmChat(
        api_key=runtime["api_key"],
        session_id=f"{payload.session_id}-{uuid.uuid4()}",
        system_message=system_prompt,
    ).with_model(runtime["provider"], runtime["model"])
    pending_messages = await chat.get_messages()
    await chat._add_user_message(pending_messages, UserMessage(text=payload.content))
    llm_response = await chat._execute_completion(pending_messages)
    reply = await chat._extract_response_text(llm_response)
    await chat._add_assistant_message(pending_messages, reply)

    assistant_message = MessageRecord(
        session_id=payload.session_id,
        role="assistant",
        content=reply,
        inference_provider=f"{runtime['provider']}:{runtime['model']}",
        metadata_tags=["SESSION_MEMORY", "SANITIZED_CONTEXT"],
    )
    assistant_doc = assistant_message.model_dump()
    assistant_doc["timestamp"] = assistant_doc["timestamp"].isoformat()
    await collection("messages").insert_one(assistant_doc)
    title_updates = {
        "lane": session_lane,
        "last_message_preview": reply[:140],
        "summary": reply[:220],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    user_turn_count = sum(1 for message in messages if message.role == "user")
    if user_turn_count <= 3 and (session.get("title_source") == "auto" or is_generic_session_title(session.get("title"))):
        title_updates["title"] = build_auto_thread_title(messages, session_lane)
        title_updates["title_source"] = "auto"
    wcw_budget = 200000
    prior_receipts = await collection(
        "receipts"
    ).find({"session_id": payload.session_id}, {"_id": 0, "prompt_tokens": 1, "completion_tokens": 1}).to_list(500)
    token_receipt = build_token_receipt(
        runtime["model"],
        prompt_sections,
        system_prompt,
        payload.content,
        reply,
        llm_response,
        prior_prompt_total=sum(item.get("prompt_tokens", 0) for item in prior_receipts),
        prior_completion_total=sum(item.get("completion_tokens", 0) for item in prior_receipts),
    )
    receipt.update(token_receipt)
    receipt["wcw_budget"] = wcw_budget
    wcw_used_estimate = token_receipt["active_context_tokens"]
    previous_receipt = await collection("receipts").find_one({"session_id": payload.session_id}, {"_id": 0}, sort=[("created_at", -1)])
    previous_summary = await collection("thread_summaries").find_one({"session_id": payload.session_id}, {"_id": 0}, sort=[("created_at", -1)])
    previous_seed = await collection("context_seeds").find_one({"session_id": payload.session_id}, {"_id": 0}, sort=[("created_at", -1)])
    lineage_depth = max(
        previous_receipt.get("lineage_depth", 0) if previous_receipt else 0,
        previous_summary.get("lineage_depth", 0) if previous_summary else 0,
        previous_seed.get("lineage_depth", 0) if previous_seed else 0,
    ) + 1
    source_message_ids = [user_message.id, assistant_message.id]
    await collection("receipts").insert_one(
        build_receipt_record(
            payload.session_id,
            assistant_message.id,
            source_message_ids,
            runtime["provider"],
            runtime["model"],
            receipt,
            wcw_used_estimate,
            wcw_budget,
            previous_receipt_id=previous_receipt["id"] if previous_receipt else None,
            previous_summary_id=previous_summary["id"] if previous_summary else None,
            previous_seed_id=previous_seed["id"] if previous_seed else None,
            lineage_depth=lineage_depth,
        )
    )
    await collection("thread_summaries").insert_one(
        build_summary_record(
            payload.session_id,
            payload.content,
            reply,
            session_lane,
            subject_bins,
            source_message_ids,
            previous_summary_id=previous_summary["id"] if previous_summary else None,
            lineage_depth=lineage_depth,
        )
    )
    await collection("context_seeds").insert_one(
        build_seed_record(
            payload.session_id,
            receipt,
            payload.content,
            reply,
            session_lane,
            subject_bins,
            source_message_ids,
            previous_seed_id=previous_seed["id"] if previous_seed else None,
            previous_summary_id=previous_summary["id"] if previous_summary else None,
            lineage_depth=lineage_depth,
        )
    )
    await collection("sessions").update_one(
        {"session_id": payload.session_id},
        {"$set": title_updates},
    )
    await upsert_global_info_entry(
        payload.user_email,
        payload.session_id,
        assistant_message.id,
        session_lane,
        subject_bins,
        retrieval_terms,
        reply,
    )
    await rebuild_lane_workers(payload.user_email)

    return ChatResponse(
        session_id=payload.session_id,
        reply=reply,
        assistant_message=assistant_message,
        sanitized_history=compressed,
        injected_memories=injected_memories,
        receipt=receipt,
        provider=runtime["provider"],
        model=runtime["model"],
        lane=session_lane,
        subject_bins=subject_bins,
        wcw_used_estimate=wcw_used_estimate,
        wcw_budget=wcw_budget,
    )