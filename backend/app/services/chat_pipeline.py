import asyncio
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
    _t_start = time.perf_counter()
    step_timings: dict[str, int] = {}
    def _mark(name: str) -> None:
        step_timings[name] = int((time.perf_counter() - _t_start) * 1000)

    session, profile_doc = await asyncio.gather(
        collection("sessions").find_one({"session_id": payload.session_id}, {"_id": 0}),
        collection("user_profiles").find_one({"user_email": payload.user_email}, {"_id": 0}),
    )
    if not session:
        raise ValueError("Session not found")

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
    _mark("setup")

    # Check token quota (freemium model) - prevents abuse. Admin users get unlimited.
    estimated_tokens = 2000  # Average request tokens
    if not is_admin_user:
        quota_check = await check_and_deduct_tokens(payload.user_email, estimated_tokens)
    else:
        quota_check = {"allowed": True, "tokens_remaining": 999999, "message": ""}

    if not quota_check["allowed"]:
        # Return quota exceeded response — use the REAL ChatResponse schema fields
        # (reply / assistant_message / sanitized_history / etc.). The previous
        # implementation used wrong field names, producing 8 Pydantic validation
        # errors instead of the friendly quota-reached message.
        from app.schemas.caos import MessageRecord as _MR
        error_message = quota_check["message"]
        quota_text = f"⚠️ **Daily Token Limit Reached**\n\n{error_message}\n\n💡 **Upgrade to Pro** for 5M tokens/day, or wait for the daily reset."
        quota_msg = _MR(
            session_id=payload.session_id,
            role="assistant",
            content=quota_text,
            metadata_tags=["QUOTA_BLOCKED"],
        )
        return ChatResponse(
            session_id=payload.session_id,
            reply=quota_text,
            assistant_message=quota_msg,
            sanitized_history=[],
            injected_memories=[],
            receipt={"error": "quota_exceeded", "tokens_remaining": quota_check["tokens_remaining"]},
            provider=payload.provider or "system",
            model=payload.model or "system",
            lane="general",
            subject_bins=[],
            wcw_used_estimate=0,
            wcw_budget=0,
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
    _mark("fetch_history")
    runtime = resolve_chat_runtime(profile, payload.provider, payload.model)
    # Dynamic history budget — Aria flagged the hardcoded ~2200 token cap
    # contradicting the 1M context-window UI claim. Now scales with the actual
    # model's context window: ~70% goes to history, leaving headroom for
    # system prompt + memories + the new user message + reply.
    from app.services.model_catalog import context_window_for
    model_ctx = context_window_for(f"{runtime['provider']}:{runtime['model']}")
    dynamic_history_budget = max(payload.history_token_budget, int(model_ctx * 0.70))
    sanitized, stats = sanitize_history(history_messages)
    compressed = compress_history(sanitized, payload.hot_head, payload.hot_tail)
    compressed, budget_stats = enforce_history_token_budget(compressed, runtime["model"], dynamic_history_budget)
    stats.update(budget_stats)
    _mark("history_compress")
    memories = list(profile.structured_memory)
    subject_bins = derive_subject_bins(payload.content, compressed)
    session_lane = derive_lane(subject_bins, session.get("title"), session.get("lane"))
    injected_memories, retrieval_terms = rank_memories(payload.content, compressed, memories, payload.memory_limit, subject_bins)
    subject_bins = derive_subject_bins(payload.content, compressed, injected_memories)
    _mark("memory_rank")
    # Parallelize ALL independent pre-LLM fetches: sessions list + attachments +
    # lane workers + global_info + awareness block + 6 connector flags.
    # Cuts pre-LLM round-trips from ~10 sequential awaits to 2 parallel batches.
    from app.routes.connectors import (
        get_github_token_for, is_google_connected, is_obsidian_connected,
        is_slack_connected, is_messaging_connected,
    )
    from app.services.mcp_client import (
        get_active_servers, render_mcp_prompt, dispatch_mcp_call, McpError,
    )
    from app.services.system_awareness import build_awareness_block as _awareness_fn

    async def _safe_awareness(email):
        try:
            return await _awareness_fn(email)
        except Exception as exc:
            return f"awareness unavailable ({str(exc)[:80]})"

    (user_session_docs, attachment_docs, workers, global_info_entries,
     awareness_block, google_connected, obsidian_connected, slack_connected,
     messaging_state, mcp_servers, github_token) = await asyncio.gather(
        collection("sessions").find({"user_email": payload.user_email}, {"_id": 0}).to_list(200),
        collection("user_files").find({"user_email": payload.user_email, "session_id": payload.session_id}, {"_id": 0}).sort("created_at", -1).to_list(20),
        list_lane_workers(payload.user_email),
        select_global_info_entries(payload.user_email, payload.content, subject_bins, session_lane),
        _safe_awareness(payload.user_email),
        is_google_connected(payload.user_email),
        is_obsidian_connected(payload.user_email),
        is_slack_connected(payload.user_email),
        is_messaging_connected(payload.user_email),
        get_active_servers(payload.user_email),
        get_github_token_for(payload.user_email),
    )
    session_ids = [doc["session_id"] for doc in user_session_docs]
    if not workers:
        workers = await rebuild_lane_workers(payload.user_email)
    summary_docs, seed_docs = await asyncio.gather(
        collection("thread_summaries").find({"session_id": {"$in": session_ids}}, {"_id": 0}).sort("created_at", -1).to_list(120),
        collection("context_seeds").find({"session_id": {"$in": session_ids}}, {"_id": 0}).sort("created_at", -1).to_list(120),
    )
    # Filter attachments to ONLY those uploaded since the previous user
    # message. Without this, every photo/PDF/text file ever attached to the
    # session gets base64-encoded and re-sent to the LLM on every turn — a
    # 7-screenshot thread costs ~2-3 SECONDS of extra latency per turn AND
    # burns the corresponding context tokens. Files referenced in old turns
    # are still in history-summary form, so the LLM remembers them; if the
    # user wants the LLM to re-see the binary they re-attach.
    prev_user_msgs = [m for m in history_messages if m.role == "user"]
    if prev_user_msgs:
        cutoff_iso = prev_user_msgs[-1].timestamp.isoformat()
        attachment_docs = [a for a in attachment_docs if a.get("created_at", "") > cutoff_iso]
    continuity_packet = build_continuity_packet(
        payload.content,
        subject_bins,
        [SummaryRecord(**doc) for doc in summary_docs],
        [SeedRecord(**doc) for doc in seed_docs],
        workers=workers,
        lane=session_lane,
        session_id=payload.session_id,
    )
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
    prompt_sections["awareness_block"] = awareness_block
    system_prompt = build_system_prompt_from_sections(prompt_sections)

    _tool_context = {"github_token": github_token, "user_email": payload.user_email}
    connector_tool_chunks: list[str] = []
    if google_connected:
        from app.services.aria_tools_google import GOOGLE_TOOL_PROMPT
        connector_tool_chunks.append(GOOGLE_TOOL_PROMPT)
    if obsidian_connected:
        from app.services.aria_tools_obsidian import OBSIDIAN_TOOL_PROMPT
        connector_tool_chunks.append(OBSIDIAN_TOOL_PROMPT)
    if slack_connected:
        from app.services.aria_tools_slack import SLACK_TOOL_PROMPT
        connector_tool_chunks.append(SLACK_TOOL_PROMPT)
    if messaging_state["twilio"] or messaging_state["telegram"]:
        from app.services.aria_tools_messaging import MESSAGING_TOOL_PROMPT
        msg_prompt = MESSAGING_TOOL_PROMPT
        if not messaging_state["twilio"]:
            msg_prompt = "\n".join(line for line in msg_prompt.splitlines() if "sms_" not in line)
        if not messaging_state["telegram"]:
            msg_prompt = "\n".join(line for line in msg_prompt.splitlines() if "telegram_" not in line)
        connector_tool_chunks.append(msg_prompt)
    if mcp_servers:
        mcp_section = render_mcp_prompt(mcp_servers)
        if mcp_section:
            connector_tool_chunks.append(mcp_section)
    if connector_tool_chunks:
        system_prompt = system_prompt + "\n\nConnector tools available this turn:\n" + "\n\n".join(connector_tool_chunks)
    _mark("pre_llm_ready")

    # Build file_contents for UserMessage. emergentintegrations supports two
    # attachment shapes:
    #   - FileContentWithMimeType(file_path=..., mime_type=...)  → Gemini ONLY
    #     (handles images + PDFs + arbitrary files via Google's File API)
    #   - ImageContent(image_base64=...)  → OpenAI + Gemini (and we treat it
    #     as best-effort for Claude — emergentintegrations routes it through
    #     Claude's vision API; degrades gracefully if unsupported)
    # We pick the right shape per provider so OpenAI/Claude actually SEE the
    # pixels instead of getting a text description.
    from pathlib import Path as _Path
    import base64 as _b64
    from emergentintegrations.llm.chat import FileContentWithMimeType, ImageContent

    _IMAGE_MIMES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}
    _VISION_MAX_PER_TURN = 5  # don't blow up the prompt
    _VISION_MAX_BYTES = 8 * 1024 * 1024  # 8 MB per image — OpenAI/Claude cap

    file_contents: list = []
    if runtime["provider"] == "gemini":
        # Gemini path: file_path attachment supports any file type.
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
    elif runtime["provider"] in {"openai", "anthropic"}:
        # OpenAI / Claude path: only IMAGE files via base64 ImageContent.
        # Non-image files (PDFs, etc.) still appear in the system-prompt
        # `attachments_block` so Aria knows they exist by name.
        attached = 0
        for doc in attachment_docs:
            if attached >= _VISION_MAX_PER_TURN:
                break
            mime = (doc.get("mime_type") or "").lower()
            if mime not in _IMAGE_MIMES:
                continue
            storage_path = doc.get("storage_path")
            if not storage_path or doc.get("kind") == "link":
                continue
            try:
                # For object-storage uploads, storage_path may be a key, not a
                # local file. Fetch via the storage layer if not on disk.
                path_obj = _Path(storage_path)
                if path_obj.exists():
                    raw = path_obj.read_bytes()
                else:
                    from app.services.object_storage import get_object as _get_obj
                    raw = _get_obj(storage_path)
                if len(raw) > _VISION_MAX_BYTES:
                    print(f"CAOS vision: skipping {doc.get('name')} — {len(raw)/1024/1024:.1f}MB > cap")
                    continue
                b64 = _b64.b64encode(raw).decode("ascii")
                file_contents.append(ImageContent(image_base64=b64))
                attached += 1
            except Exception as attach_error:
                # Non-fatal — let the chat proceed without this image rather
                # than crashing the whole turn. The attachments_block in the
                # system prompt still tells Aria the file exists.
                print(f"CAOS vision attach failed {doc.get('name')}: {attach_error}")

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
    # Tool access now open to all authenticated users (freemium model).
    from app.services.aria_tools import extract_and_run_next_tool_async
    tool_iterations = 0
    tools_used: list[str] = []
    _TOOL_NAME_RX = __import__("re").compile(r"\[TOOL:\s*(\w+)")
    _MCP_CALL_RX = __import__("re").compile(
        r"\[MCP_CALL:\s*([\w-]+):([\w\.\-]+)\s+(\{.*?\})\s*\]",
        __import__("re").DOTALL,
    )
    while tool_iterations < 4:
        # First pass: a built-in [TOOL:...] marker.
        marker, result = await extract_and_run_next_tool_async(reply, context=_tool_context)
        if marker and result is not None:
            tool_iterations += 1
            name_match = _TOOL_NAME_RX.search(marker)
            if name_match:
                tools_used.append(name_match.group(1))
            await chat._add_assistant_message(pending_messages, reply)
            await chat._add_user_message(
                pending_messages,
                UserMessage(text=f"[TOOL_RESULT for {marker}]\n{result[:60000]}"),
            )
            llm_response = await chat._execute_completion(pending_messages)
            reply = await chat._extract_response_text(llm_response)
            continue
        # Second pass: an [MCP_CALL: server_id:tool_name {json}] marker.
        mcp_match = _MCP_CALL_RX.search(reply) if mcp_servers else None
        if mcp_match:
            tool_iterations += 1
            server_id, tool_name, args_json = mcp_match.group(1), mcp_match.group(2), mcp_match.group(3)
            try:
                import json as _json
                parsed_args = _json.loads(args_json)
            except Exception as parse_err:
                mcp_result = f"ERROR: MCP_CALL args not valid JSON — {str(parse_err)[:120]}"
            else:
                try:
                    mcp_result = await dispatch_mcp_call(payload.user_email, server_id, tool_name, parsed_args)
                except McpError as me:
                    mcp_result = f"ERROR: MCP — {str(me)[:200]}"
            tools_used.append(f"mcp:{tool_name}")
            await chat._add_assistant_message(pending_messages, reply)
            await chat._add_user_message(
                pending_messages,
                UserMessage(text=f"[MCP_RESULT for {server_id}:{tool_name}]\n{mcp_result[:60000]}"),
            )
            llm_response = await chat._execute_completion(pending_messages)
            reply = await chat._extract_response_text(llm_response)
            continue
        break
    latency_ms = int((time.perf_counter() - _llm_start) * 1000)
    _mark("llm_done")
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

    # Parallelize all 4 read queries needed to compute the receipt + lineage.
    # Was 4 sequential awaits costing ~80-200ms; now 1 round-trip.
    prior_receipts, previous_receipt, previous_summary, previous_seed = await asyncio.gather(
        collection("receipts").find({"session_id": payload.session_id}, {"_id": 0, "prompt_tokens": 1, "completion_tokens": 1}).to_list(500),
        collection("receipts").find_one({"session_id": payload.session_id}, {"_id": 0}, sort=[("created_at", -1)]),
        collection("thread_summaries").find_one({"session_id": payload.session_id}, {"_id": 0}, sort=[("created_at", -1)]),
        collection("context_seeds").find_one({"session_id": payload.session_id}, {"_id": 0}, sort=[("created_at", -1)]),
    )
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
    wcw_used_estimate = token_receipt["active_context_tokens"]
    _mark("post_llm_compute")

    lineage_depth = max(
        previous_receipt.get("lineage_depth", 0) if previous_receipt else 0,
        previous_summary.get("lineage_depth", 0) if previous_summary else 0,
        previous_seed.get("lineage_depth", 0) if previous_seed else 0,
    ) + 1
    source_message_ids = [user_message.id, assistant_message.id]

    # Build all records (CPU only, fast) — these go to the background persist task.
    receipt_record = build_receipt_record(
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
    summary_record = build_summary_record(
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
    seed_record = build_seed_record(
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

    # Engine usage doc (best-effort cost compute).
    engine_usage_doc = None
    try:
        cost_usd = compute_cost_usd(
            f"{runtime['provider']}:{runtime['model']}",
            token_receipt.get("prompt_tokens", 0),
            token_receipt.get("completion_tokens", 0),
        )
        engine_usage_doc = {
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
        }
    except Exception as usage_err:  # pragma: no cover
        print(f"CAOS engine_usage compute failed: {usage_err}")

    # BACKGROUND: All persistence runs in parallel AFTER the response goes back
    # to the user. Cuts perceived turn latency by 1.5–3 seconds because the UI
    # no longer waits for receipts/summaries/seeds/lane_workers/global_info to
    # write. If any write fails it logs but does NOT roll back the chat reply.
    user_email_local = payload.user_email
    session_id_local = payload.session_id
    asst_id_local = assistant_message.id
    retrieval_terms_local = retrieval_terms
    reply_local = reply
    subject_bins_local = list(subject_bins)
    session_lane_local = session_lane

    async def _persist_aftermath():
        try:
            ops = [
                collection("receipts").insert_one(receipt_record),
                collection("thread_summaries").insert_one(summary_record),
                collection("context_seeds").insert_one(seed_record),
                collection("sessions").update_one({"session_id": session_id_local}, {"$set": title_updates}),
                upsert_global_info_entry(user_email_local, session_id_local, asst_id_local, session_lane_local, subject_bins_local, retrieval_terms_local, reply_local),
                rebuild_lane_workers(user_email_local),
            ]
            if engine_usage_doc is not None:
                ops.append(collection("engine_usage").insert_one(engine_usage_doc))
            await asyncio.gather(*ops, return_exceptions=True)
        except Exception as exc:  # pragma: no cover
            print(f"CAOS turn aftermath failed: {exc}")

    asyncio.create_task(_persist_aftermath())
    _mark("handler_done")
    receipt["step_timings"] = step_timings

    # Phase 2: Autonomous Memory Extraction (already fire-and-forget).
    try:
        from app.services.memory_extractor import schedule_extraction
        schedule_extraction(
            user_email=payload.user_email,
            session_id=payload.session_id,
            user_message=payload.content,
            assistant_reply=reply,
            user_message_id=user_message.id,
        )
    except Exception as extractor_err:  # pragma: no cover
        print(f"CAOS extractor scheduling failed: {extractor_err}")

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