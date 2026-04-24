import os
import time
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
from app.services.runtime_service import resolve_chat_runtime, supports_temperature_param
from app.services.token_meter import build_token_receipt
from app.services.token_quota import check_and_deduct_tokens, record_token_usage
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
        is_admin_user = False
    else:
        profile = UserProfileRecord(**profile_doc)
        is_admin_user = bool(profile_doc.get("is_admin") is True or profile_doc.get("role") == "admin")

    # Check token quota (freemium model) - prevents abuse
    estimated_tokens = 2000  # Average request tokens
    quota_check = await check_and_deduct_tokens(payload.user_email, estimated_tokens)
    
    if not quota_check["allowed"]:
        # Return quota exceeded response
        error_message = quota_check["message"]
        return ChatResponse(
            session_id=payload.session_id,
            content=f"⚠️ **Daily Token Limit Reached**\n\n{error_message}\n\n💡 **Upgrade to Pro** for 500k tokens/day or **Unlimited** for no limits!",
            role="assistant",
            provider=payload.provider or "system",
            model=payload.model or "system",
            token_receipt={"error": "quota_exceeded", "tokens_remaining": quota_check["tokens_remaining"]},
            context_stats={},
            lane=None,
            subject_bins=[],
            continuity_packet=None,
        )

    user_message = MessageRecord(session_id=payload.session_id, role="user", content=payload.content)
    user_doc = user_message.model_dump()
    user_doc["timestamp"] = user_doc["timestamp"].isoformat()
    await collection("messages").insert_one(user_doc)

    # Optimized: Limit message fetch to last 1000 (prevents memory issues on huge threads)
    # Older messages beyond 1000 are auto-compressed anyway, so no need to load them
    docs = await collection("messages").find(
        {"session_id": payload.session_id}, 
        {"_id": 0}
    ).sort("timestamp", -1).limit(1000).to_list(1000)
    # Reverse to chronological order after limiting to recent 1000
    docs.reverse()
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
    # Fetch uploaded files for this thread — text file names go into the system prompt,
    # images (and PDFs) are attached to the UserMessage as file_contents so Claude/GPT/Gemini
    # can actually see them via emergentintegrations vision support.
    attachment_docs = await collection("user_files").find(
        {"user_email": payload.user_email, "session_id": payload.session_id},
        {"_id": 0},
    ).sort("created_at", -1).to_list(20)
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
    prompt_sections = build_prompt_sections(
        profile, compressed, injected_memories, continuity_packet,
        [entry.model_dump() for entry in global_info_entries],
        attachments=attachment_docs,
        provider=runtime["provider"],
    )
    # Admin-only: tool-inspection rules are only taught to admin users. Regular
    # users never see the [TOOL: ...] marker syntax in their system prompt, so
    # even if they try to copy it from somewhere, the LLM won't know what to do.
    prompt_sections["admin_tools_allowed"] = is_admin_user
    try:
        from app.services.system_awareness import build_awareness_block
        prompt_sections["awareness_block"] = await build_awareness_block(payload.user_email)
    except Exception as awareness_error:
        prompt_sections["awareness_block"] = f"awareness unavailable ({str(awareness_error)[:80]})"
    system_prompt = build_system_prompt_from_sections(prompt_sections)

    # Build file_contents for UserMessage — only attach actual files (skip links),
    # cap to 10, skip files missing on disk. NOTE: emergentintegrations currently
    # only supports file attachments for Gemini (Claude/GPT route attachments via
    # a different API surface). For non-Gemini providers we rely on the system
    # prompt's attachments block to let the AI know files exist by name/type.
    from pathlib import Path as _Path
    from emergentintegrations.llm.chat import FileContentWithMimeType
    file_contents: list = []
    if runtime["provider"] == "gemini":
        for doc in attachment_docs[:10]:
            storage_path = doc.get("storage_path")
            if not storage_path or doc.get("kind") == "link":
                continue
            if not _Path(storage_path).exists():
                continue
            try:
                file_contents.append(FileContentWithMimeType(
                    mime_type=doc.get("mime_type") or "application/octet-stream",
                    file_path=storage_path,
                ))
            except Exception as attach_error:
                print(f"CAOS attachment skipped {doc.get('name')}: {attach_error}")

    _mode_temp = {"fact": 0.1, "balanced": 0.3, "creative": 0.7}
    _temp = _mode_temp.get(getattr(profile, "chat_mode", "balanced"), 0.3)
    # Env var still wins if explicitly set (ops override).
    _env_temp = os.environ.get("CAOS_CHAT_TEMPERATURE")
    if _env_temp:
        try:
            _temp = float(_env_temp)
        except ValueError:
            pass
    chat = LlmChat(
        api_key=runtime["api_key"],
        session_id=f"{payload.session_id}-{uuid.uuid4()}",
        system_message=system_prompt,
    ).with_model(runtime["provider"], runtime["model"])
    if supports_temperature_param(runtime["provider"], runtime["model"]):
        chat = chat.with_params(temperature=_temp)
    pending_messages = await chat.get_messages()
    await chat._add_user_message(
        pending_messages,
        UserMessage(text=payload.content, file_contents=file_contents or None),
    )
    _llm_start = time.perf_counter()
    llm_response = await chat._execute_completion(pending_messages)
    reply = await chat._extract_response_text(llm_response)
    # Agent loop: let Aria call read-only inspection tools up to 3 times.
    # ADMIN ONLY — non-admin users never get tool access (their prompt doesn't
    # even teach them the syntax, and even if they found it, we short-circuit
    # here as defense-in-depth).
    # Tool access now open to all authenticated users (freemium model).
    from app.services.aria_tools import extract_and_run_next_tool
    from app.routes.connectors import get_github_token_for
    _tool_context = {"github_token": await get_github_token_for(payload.user_email)}
    tool_iterations = 0
    tools_used: list[str] = []
    _TOOL_NAME_RX = __import__("re").compile(r"\[TOOL:\s*(\w+)")
    while tool_iterations < 3:
        marker, result = extract_and_run_next_tool(reply, context=_tool_context)
        if not marker or result is None:
            break
        tool_iterations += 1
        name_match = _TOOL_NAME_RX.search(marker)
        if name_match:
            tools_used.append(name_match.group(1))
        # Persist Aria's partial (tool-requesting) reply into the chat history
        # so the next turn has context of what she asked for.
        await chat._add_assistant_message(pending_messages, reply)
        await chat._add_user_message(
            pending_messages,
            UserMessage(text=f"[TOOL_RESULT for {marker}]\n{result[:60000]}"),
        )
        llm_response = await chat._execute_completion(pending_messages)
        reply = await chat._extract_response_text(llm_response)
    latency_ms = int((time.perf_counter() - _llm_start) * 1000)
    # Parse Aria's FILE_TICKET marker and create a ticket, stripping it from the
    # user-facing reply. Format: [FILE_TICKET: category=..., title=..., description=...]
    try:
        import re as _re
        marker_pattern = _re.compile(r"\[FILE_TICKET:\s*(.*?)\]", _re.DOTALL)
        match = marker_pattern.search(reply)
        if match:
            body = match.group(1)
            fields: dict = {}
            for part in _re.split(r",\s*(?=category=|title=|description=)", body):
                if "=" in part:
                    k, v = part.split("=", 1)
                    fields[k.strip().lower()] = v.strip()
            cat = (fields.get("category") or "other").lower()
            if cat not in {"bug", "feature", "ux", "other"}:
                cat = "other"
            from app.routes.support import _insert_ticket
            ticket_record = await _insert_ticket(
                user_email=payload.user_email,
                session_id=payload.session_id,
                category=cat,
                title=fields.get("title") or "Issue filed by Aria",
                description=fields.get("description") or payload.content[:500],
                source="aria_filed",
            )
            ticket_info = {"id": ticket_record.id, "category": ticket_record.category, "title": ticket_record.title}  # noqa: F841
            _ = ticket_info  # reserved for future response enrichment
            reply = marker_pattern.sub("", reply).strip()
            # Append a small confirmation line so the user sees the ticket was filed.
            reply = f"{reply}\n\n✅ Support ticket filed: **{ticket_record.title}** (ID `{ticket_record.id[:8]}` · {ticket_record.category})."
    except Exception as ticket_error:
        print(f"CAOS ticket marker parse failed: {ticket_error}")
    await chat._add_assistant_message(pending_messages, reply)

    assistant_message = MessageRecord(
        session_id=payload.session_id,
        role="assistant",
        content=reply,
        inference_provider=f"{runtime['provider']}:{runtime['model']}",
        latency_ms=latency_ms,
        tools_used=tools_used,
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
    # WCW budget tracks the model's actual context window (not a hard-coded
    # 200 k). Claude Sonnet 4.5 and Gemini 3 are 1 M; GPT-5.2 is 400 k; etc.
    from app.services.model_catalog import context_window_for, compute_cost_usd
    wcw_budget = context_window_for(f"{runtime['provider']}:{runtime['model']}")
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
    receipt["latency_ms"] = latency_ms

    # Persist per-turn spend in a dedicated collection so the dashboard can
    # answer "how much did I spend on Claude this week?" cheaply.
    try:
        cost_usd = compute_cost_usd(
            f"{runtime['provider']}:{runtime['model']}",
            token_receipt.get("prompt_tokens", 0),
            token_receipt.get("completion_tokens", 0),
        )
        await collection("engine_usage").insert_one({
            "id": f"usage_{assistant_message.id}",
            "session_id": payload.session_id,
            "message_id": assistant_message.id,
            "user_email": payload.user_email,
            "provider": runtime["provider"],
            "model": runtime["model"],
            "prompt_tokens": token_receipt.get("prompt_tokens", 0),
            "completion_tokens": token_receipt.get("completion_tokens", 0),
            "total_tokens": token_receipt.get("total_tokens", 0),
            "cost_usd": cost_usd,
            "latency_ms": latency_ms,
            "tools_used": tools_used,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as usage_err:  # pragma: no cover
        print(f"CAOS engine_usage persist failed: {usage_err}")
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
            source_started_at=user_message.timestamp.isoformat(),
            source_ended_at=assistant_message.timestamp.isoformat(),
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
            source_started_at=user_message.timestamp.isoformat(),
            source_ended_at=assistant_message.timestamp.isoformat(),
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