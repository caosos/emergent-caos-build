import asyncio
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path as _Path
import base64 as _b64
import re as _re

from emergentintegrations.llm.chat import (
    FileContentWithMimeType,
    ImageContent,
    LlmChat,
    UserMessage,
)

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
from app.services.hydration_policy import build_hydration_decision
from app.services.memory_worker_service import derive_lane, list_lane_workers, rebuild_lane_workers
from app.services.proactivity_policy import build_proactivity_decision
from app.services.prompt_builder import build_prompt_sections, build_system_prompt_from_sections
from app.services.runtime_service import resolve_chat_runtime, supports_temperature_param
from app.services.token_meter import build_token_receipt
from app.services.token_quota import check_and_deduct_tokens
from app.services.thread_title_service import build_auto_thread_title, is_generic_session_title
from app.services.turn_trace import TurnTrace, classify_latency_budget

_IMAGE_MIMES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}
_VISION_MAX_PER_TURN = 5
_VISION_MAX_BYTES = 8 * 1024 * 1024
_TOOL_NAME_RX = _re.compile(r"\[TOOL:\s*(\w+)")
_MCP_CALL_RX = _re.compile(
    r"\[MCP_CALL:\s*([\w-]+):([\w\.\-]+)\s+(\{.*?\})\s*\]",
    _re.DOTALL,
)


async def _safe_awareness(email: str) -> str:
    try:
        from app.services.system_awareness import build_awareness_block
        return await build_awareness_block(email)
    except Exception as exc:  # pragma: no cover
        return f"awareness unavailable ({str(exc)[:80]})"


async def _empty(value=None):
    return value


def _serialize_message_doc(message: MessageRecord) -> dict:
    doc = message.model_dump()
    doc["timestamp"] = doc["timestamp"].isoformat()
    return doc


def _build_file_contents(runtime_provider: str, attachment_docs: list[dict]) -> list:
    file_contents: list = []
    if runtime_provider == "gemini":
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
        return file_contents

    if runtime_provider not in {"openai", "anthropic"}:
        return file_contents

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
            path_obj = _Path(storage_path)
            if path_obj.exists():
                raw = path_obj.read_bytes()
            else:
                from app.services.object_storage import get_object as _get_obj
                raw = _get_obj(storage_path)
            if len(raw) > _VISION_MAX_BYTES:
                print(f"CAOS vision: skipping {doc.get('name')} — {len(raw)/1024/1024:.1f}MB > cap")
                continue
            file_contents.append(ImageContent(image_base64=_b64.b64encode(raw).decode("ascii")))
            attached += 1
        except Exception as attach_error:
            print(f"CAOS vision attach failed {doc.get('name')}: {attach_error}")
    return file_contents


async def run_chat_turn(payload: ChatRequest) -> ChatResponse:
    _t_start = time.perf_counter()
    trace = TurnTrace()
    trace.instant("turn_start", category="request", meta={"session_id": payload.session_id})
    step_timings: dict[str, int] = {}

    def _mark(name: str) -> None:
        step_timings[name] = int((time.perf_counter() - _t_start) * 1000)

    trace.start("setup", category="db", meta={"collections": ["sessions", "user_profiles"]})
    session, profile_doc = await asyncio.gather(
        collection("sessions").find_one({"session_id": payload.session_id}, {"_id": 0}),
        collection("user_profiles").find_one({"user_email": payload.user_email}, {"_id": 0}),
    )
    if not session:
        trace.end("setup", category="db", meta={"error": "session_not_found"})
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
    trace.end("setup", category="db", meta={"is_admin": is_admin_user, "profile_created": not bool(profile_doc)})
    _mark("setup")

    estimated_tokens = 2000
    trace.start("quota_check", category="quota", meta={"estimated_tokens": estimated_tokens, "admin_bypass": is_admin_user})
    quota_check = {"allowed": True, "tokens_remaining": 999999, "message": ""} if is_admin_user else await check_and_deduct_tokens(payload.user_email, estimated_tokens)
    trace.end("quota_check", category="quota", meta={"allowed": bool(quota_check.get("allowed"))})
    if not quota_check["allowed"]:
        error_message = quota_check["message"]
        quota_text = f"⚠️ **Daily Token Limit Reached**\n\n{error_message}\n\n💡 **Upgrade to Pro** for 5M tokens/day, or wait for the daily reset."
        quota_msg = MessageRecord(
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
            receipt={"error": "quota_exceeded", "tokens_remaining": quota_check["tokens_remaining"], "latency_trace": trace.receipt()},
            provider=payload.provider or "system",
            model=payload.model or "system",
            lane="general",
            subject_bins=[],
            wcw_used_estimate=0,
            wcw_budget=0,
        )

    trace.start("save_user_message", category="db")
    user_message = MessageRecord(session_id=payload.session_id, role="user", content=payload.content)
    await collection("messages").insert_one(_serialize_message_doc(user_message))
    trace.end("save_user_message", category="db")

    trace.start("fetch_history", category="db", meta={"limit": 1000})
    docs = await collection("messages").find(
        {"session_id": payload.session_id},
        {"_id": 0},
    ).sort("timestamp", -1).limit(1000).to_list(1000)
    docs.reverse()
    messages = [MessageRecord(**doc) for doc in docs]
    history_messages = messages[:-1] if messages and messages[-1].id == user_message.id else messages
    trace.end("fetch_history", category="db", meta={"message_count": len(messages), "history_count": len(history_messages)})
    _mark("fetch_history")

    trace.start("policy_runtime", category="policy")
    runtime = resolve_chat_runtime(profile, payload.provider, payload.model)
    from app.services.model_catalog import context_window_for, compute_cost_usd
    model_ctx = context_window_for(f"{runtime['provider']}:{runtime['model']}")
    proactivity = build_proactivity_decision(payload.content, is_admin=is_admin_user)
    hydration = build_hydration_decision(
        payload.content,
        model_context_window=model_ctx,
        session=session,
        is_admin=is_admin_user,
    )
    dynamic_history_budget = max(payload.history_token_budget, hydration.history_token_budget)
    trace.end(
        "policy_runtime",
        category="policy",
        meta={
            "provider": runtime["provider"],
            "model": runtime["model"],
            "model_ctx": model_ctx,
            "hydration_mode": hydration.mode,
            "proactivity_intent": proactivity.primary_intent,
            "history_budget": dynamic_history_budget,
        },
    )

    trace.start("history_compress", category="history", meta={"history_budget": dynamic_history_budget})
    sanitized, stats = sanitize_history(history_messages)
    compressed = compress_history(sanitized, payload.hot_head, payload.hot_tail)
    compressed, budget_stats = enforce_history_token_budget(compressed, runtime["model"], dynamic_history_budget)
    stats.update(budget_stats)
    stats["hydration_policy"] = hydration.as_receipt()
    stats["proactivity_policy"] = proactivity.as_receipt()
    trace.end(
        "history_compress",
        category="history",
        meta={
            "sanitized_count": len(sanitized),
            "compressed_count": len(compressed),
            "history_tokens_after_budget": budget_stats.get("history_tokens_after_budget", 0),
        },
    )
    _mark("history_compress")

    trace.start("memory_rank", category="memory")
    memories = list(profile.structured_memory)
    subject_bins = derive_subject_bins(payload.content, compressed)
    session_lane = derive_lane(subject_bins, session.get("title"), session.get("lane"))
    injected_memories, retrieval_terms = rank_memories(payload.content, compressed, memories, payload.memory_limit, subject_bins)
    subject_bins = derive_subject_bins(payload.content, compressed, injected_memories)
    trace.end(
        "memory_rank",
        category="memory",
        meta={"available_memories": len(memories), "injected_memories": len(injected_memories), "lane": session_lane},
    )
    _mark("memory_rank")

    from app.routes.connectors import (
        get_github_token_for, is_google_connected, is_obsidian_connected,
        is_slack_connected, is_messaging_connected,
    )
    from app.services.mcp_client import get_active_servers, render_mcp_prompt, dispatch_mcp_call, McpError

    tools_allowed = is_admin_user or hydration.use_tool_prompt or proactivity.allow_tools
    connector_tools_allowed = hydration.use_connector_tools or proactivity.allow_connectors or (is_admin_user and hydration.use_tool_prompt)
    need_sessions = hydration.use_cross_thread or hydration.use_lane_workers or ("thread_summaries" in proactivity.wake_departments) or ("context_seeds" in proactivity.wake_departments)
    need_connectors = connector_tools_allowed
    need_github_token = tools_allowed or connector_tools_allowed
    trace.instant(
        "department_gates",
        category="policy",
        meta={
            "tools_allowed": tools_allowed,
            "connector_tools_allowed": connector_tools_allowed,
            "need_sessions": need_sessions,
            "need_connectors": need_connectors,
            "need_github_token": need_github_token,
            "wake_departments": proactivity.wake_departments,
        },
    )

    trace.start("pre_llm_gather", category="db_connector")
    (
        user_session_docs,
        attachment_docs,
        workers,
        global_info_entries,
        awareness_block,
        google_connected,
        obsidian_connected,
        slack_connected,
        messaging_state,
        mcp_servers,
        github_token,
    ) = await asyncio.gather(
        collection("sessions").find({"user_email": payload.user_email}, {"_id": 0}).to_list(200) if need_sessions else _empty([]),
        collection("user_files").find({"user_email": payload.user_email, "session_id": payload.session_id}, {"_id": 0}).sort("created_at", -1).to_list(20),
        list_lane_workers(payload.user_email) if (hydration.use_lane_workers or "lane_workers" in proactivity.wake_departments) else _empty([]),
        select_global_info_entries(payload.user_email, payload.content, subject_bins, session_lane) if (hydration.use_global_info or "search" in proactivity.wake_departments) else _empty([]),
        _safe_awareness(payload.user_email),
        is_google_connected(payload.user_email) if need_connectors else _empty(False),
        is_obsidian_connected(payload.user_email) if need_connectors else _empty(False),
        is_slack_connected(payload.user_email) if need_connectors else _empty(False),
        is_messaging_connected(payload.user_email) if need_connectors else _empty({"twilio": False, "telegram": False}),
        get_active_servers(payload.user_email) if (tools_allowed or connector_tools_allowed) else _empty([]),
        get_github_token_for(payload.user_email) if need_github_token else _empty(None),
    )
    trace.end(
        "pre_llm_gather",
        category="db_connector",
        meta={
            "sessions_loaded": len(user_session_docs),
            "attachments_loaded": len(attachment_docs),
            "workers_loaded": len(workers),
            "global_info_loaded": len(global_info_entries),
            "google_connected": bool(google_connected),
            "obsidian_connected": bool(obsidian_connected),
            "slack_connected": bool(slack_connected),
            "mcp_server_count": len(mcp_servers),
            "github_token_present": bool(github_token),
        },
    )

    trace.start("continuity_build", category="continuity")
    session_ids = [doc["session_id"] for doc in user_session_docs]
    summary_docs: list[dict] = []
    seed_docs: list[dict] = []
    if (hydration.use_cross_thread or "thread_summaries" in proactivity.wake_departments or "context_seeds" in proactivity.wake_departments) and session_ids:
        summary_docs, seed_docs = await asyncio.gather(
            collection("thread_summaries").find({"session_id": {"$in": session_ids}}, {"_id": 0}).sort("created_at", -1).to_list(120),
            collection("context_seeds").find({"session_id": {"$in": session_ids}}, {"_id": 0}).sort("created_at", -1).to_list(120),
        )

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
    trace.end(
        "continuity_build",
        category="continuity",
        meta={"summary_docs": len(summary_docs), "seed_docs": len(seed_docs), "workers": len(workers)},
    )

    trace.start("prompt_build", category="prompt")
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
    receipt["proactivity_policy"] = proactivity.as_receipt()
    receipt["hydration_policy"] = hydration.as_receipt()
    receipt["tools_allowed"] = tools_allowed
    receipt["connector_tools_allowed"] = connector_tools_allowed

    prompt_sections = build_prompt_sections(
        profile,
        compressed,
        injected_memories,
        continuity_packet,
        [entry.model_dump() for entry in global_info_entries],
        attachments=attachment_docs,
        provider=runtime["provider"],
        session_id=payload.session_id,
        user_email=payload.user_email,
    )
    prompt_sections["tools_allowed"] = tools_allowed
    prompt_sections["admin_tools_allowed"] = is_admin_user
    prompt_sections["awareness_block"] = awareness_block
    prompt_sections["proactivity_policy"] = proactivity.as_receipt()
    system_prompt = build_system_prompt_from_sections(prompt_sections)

    _tool_context = {"github_token": github_token, "user_email": payload.user_email, "session_id": payload.session_id}
    connector_tool_chunks: list[str] = []
    if connector_tools_allowed:
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
    trace.end("prompt_build", category="prompt", meta={"connector_tool_chunks": len(connector_tool_chunks), "tools_allowed": tools_allowed})
    _mark("pre_llm_ready")

    trace.start("file_content_build", category="attachments")
    file_contents = _build_file_contents(runtime["provider"], attachment_docs)
    trace.end("file_content_build", category="attachments", meta={"file_content_count": len(file_contents or [])})

    _mode_temp = {"fact": 0.1, "balanced": 0.3, "creative": 0.7}
    _temp = _mode_temp.get(getattr(profile, "chat_mode", "balanced"), 0.3)
    _env_temp = os.environ.get("CAOS_CHAT_TEMPERATURE")
    if _env_temp:
        try:
            _temp = float(_env_temp)
        except ValueError:
            pass

    trace.start("llm_prepare", category="llm", meta={"provider": runtime["provider"], "model": runtime["model"]})
    chat = LlmChat(
        api_key=runtime["api_key"],
        session_id=f"{payload.session_id}-{uuid.uuid4()}",
        system_message=system_prompt,
    ).with_model(runtime["provider"], runtime["model"])
    if supports_temperature_param(runtime["provider"], runtime["model"]):
        chat = chat.with_params(temperature=_temp)

    pending_messages = await chat.get_messages()
    await chat._add_user_message(pending_messages, UserMessage(text=payload.content, file_contents=file_contents or None))
    trace.end("llm_prepare", category="llm")

    _llm_start = time.perf_counter()
    llm_call_count = 1
    trace.start("llm_initial", category="llm", meta={"provider": runtime["provider"], "model": runtime["model"]})
    llm_response = await chat._execute_completion(pending_messages)
    reply = await chat._extract_response_text(llm_response)
    trace.end("llm_initial", category="llm")

    from app.services.aria_tools import extract_and_run_next_tool_async
    tool_iterations = 0
    tools_used: list[str] = []
    tool_step_timings: list[dict] = []
    max_tool_iterations = 4 if tools_allowed else 0
    while tool_iterations < max_tool_iterations:
        trace.start("tool_scan", category="tool", meta={"iteration": tool_iterations + 1})
        marker, result = await extract_and_run_next_tool_async(reply, context=_tool_context)
        trace.end("tool_scan", category="tool", meta={"marker_found": bool(marker)})
        if marker and result is not None:
            tool_iterations += 1
            name_match = _TOOL_NAME_RX.search(marker)
            tool_name = name_match.group(1) if name_match else "unknown"
            tools_used.append(tool_name)
            tool_exec_event = f"tool_exec.{tool_name}"
            trace.instant(tool_exec_event, category="tool", meta={"iteration": tool_iterations, "result_chars": len(result or "")})
            await chat._add_assistant_message(pending_messages, reply)
            await chat._add_user_message(pending_messages, UserMessage(text=f"[TOOL_RESULT for {marker}]\n{result[:60000]}"))
            recall_event = f"llm_recall.{tool_iterations}"
            trace.start(recall_event, category="llm", meta={"after_tool": tool_name, "iteration": tool_iterations})
            _llm_t0 = time.perf_counter()
            llm_call_count += 1
            llm_response = await chat._execute_completion(pending_messages)
            reply = await chat._extract_response_text(llm_response)
            recall_ms = int((time.perf_counter() - _llm_t0) * 1000)
            trace.end(recall_event, category="llm", meta={"after_tool": tool_name})
            tool_step_timings.append({"tool": tool_name, "tool_exec_ms": 0, "llm_recall_ms": recall_ms})
            continue

        mcp_match = _MCP_CALL_RX.search(reply) if mcp_servers else None
        if mcp_match:
            tool_iterations += 1
            server_id, tool_name, args_json = mcp_match.group(1), mcp_match.group(2), mcp_match.group(3)
            mcp_event = f"mcp_exec.{tool_name}"
            trace.start(mcp_event, category="tool", meta={"server_id": server_id, "iteration": tool_iterations})
            _mcp_t0 = time.perf_counter()
            try:
                import json as _json
                parsed_args = _json.loads(args_json)
                mcp_result = await dispatch_mcp_call(payload.user_email, server_id, tool_name, parsed_args)
            except McpError as me:
                mcp_result = f"ERROR: MCP — {str(me)[:200]}"
            except Exception as parse_err:
                mcp_result = f"ERROR: MCP_CALL args not valid JSON — {str(parse_err)[:120]}"
            _mcp_exec_ms = int((time.perf_counter() - _mcp_t0) * 1000)
            trace.end(mcp_event, category="tool", meta={"tool_exec_ms": _mcp_exec_ms})
            tools_used.append(f"mcp:{tool_name}")
            await chat._add_assistant_message(pending_messages, reply)
            await chat._add_user_message(pending_messages, UserMessage(text=f"[MCP_RESULT for {server_id}:{tool_name}]\n{mcp_result[:60000]}"))
            recall_event = f"llm_recall.{tool_iterations}"
            trace.start(recall_event, category="llm", meta={"after_tool": f"mcp:{tool_name}", "iteration": tool_iterations})
            _mcp_llm_t0 = time.perf_counter()
            llm_call_count += 1
            llm_response = await chat._execute_completion(pending_messages)
            reply = await chat._extract_response_text(llm_response)
            recall_ms = int((time.perf_counter() - _mcp_llm_t0) * 1000)
            trace.end(recall_event, category="llm", meta={"after_tool": f"mcp:{tool_name}"})
            tool_step_timings.append({"tool": f"mcp:{tool_name}", "tool_exec_ms": _mcp_exec_ms, "llm_recall_ms": recall_ms})
            continue
        break

    latency_ms = int((time.perf_counter() - _llm_start) * 1000)
    _mark("llm_done")

    trace.start("ticket_marker_parse", category="support")
    try:
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
            reply = marker_pattern.sub("", reply).strip()
            reply = f"{reply}\n\n✅ Support ticket filed: **{ticket_record.title}** (ID `{ticket_record.id[:8]}` · {ticket_record.category})."
            trace.end("ticket_marker_parse", category="support", meta={"ticket_filed": True})
        else:
            trace.end("ticket_marker_parse", category="support", meta={"ticket_filed": False})
    except Exception as ticket_error:
        trace.end("ticket_marker_parse", category="support", meta={"error": str(ticket_error)[:120]})
        print(f"CAOS ticket marker parse failed: {ticket_error}")

    trace.start("save_assistant_message", category="db")
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
    await collection("messages").insert_one(_serialize_message_doc(assistant_message))
    trace.end("save_assistant_message", category="db")

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

    trace.start("post_llm_reads", category="db")
    wcw_budget = model_ctx
    prior_receipts, previous_receipt, previous_summary, previous_seed = await asyncio.gather(
        collection("receipts").find({"session_id": payload.session_id}, {"_id": 0, "prompt_tokens": 1, "completion_tokens": 1}).to_list(500),
        collection("receipts").find_one({"session_id": payload.session_id}, {"_id": 0}, sort=[("created_at", -1)]),
        collection("thread_summaries").find_one({"session_id": payload.session_id}, {"_id": 0}, sort=[("created_at", -1)]),
        collection("context_seeds").find_one({"session_id": payload.session_id}, {"_id": 0}, sort=[("created_at", -1)]),
    )
    trace.end("post_llm_reads", category="db", meta={"prior_receipts": len(prior_receipts)})

    trace.start("token_receipt", category="tokens")
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
    receipt["tool_iterations"] = tool_iterations
    receipt["tools_used"] = tools_used
    receipt["tool_step_timings"] = tool_step_timings
    receipt["step_timings"] = step_timings
    receipt["llm_call_count"] = llm_call_count
    receipt["proactivity_policy"] = proactivity.as_receipt()
    receipt["hydration_policy"] = hydration.as_receipt()
    receipt["tools_allowed"] = tools_allowed
    receipt["connector_tools_allowed"] = connector_tools_allowed
    wcw_used_estimate = token_receipt["active_context_tokens"]
    trace.end("token_receipt", category="tokens", meta={"active_context_tokens": wcw_used_estimate})
    _mark("post_llm_compute")

    trace.start("artifact_build", category="receipt")
    lineage_depth = max(
        previous_receipt.get("lineage_depth", 0) if previous_receipt else 0,
        previous_summary.get("lineage_depth", 0) if previous_summary else 0,
        previous_seed.get("lineage_depth", 0) if previous_seed else 0,
    ) + 1
    source_message_ids = [user_message.id, assistant_message.id]

    receipt["phase_timings"] = trace.phase_timings()
    receipt["latency_category_totals"] = trace.totals_by_category()
    receipt["latency_budget"] = classify_latency_budget(
        total_ms=trace.now_ms(),
        tool_iterations=tool_iterations,
        active_context_tokens=wcw_used_estimate,
    )
    receipt["latency_trace"] = trace.receipt()

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
    trace.end("artifact_build", category="receipt", meta={"lineage_depth": lineage_depth})

    engine_usage_doc = None
    try:
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
            "cost_usd": compute_cost_usd(f"{runtime['provider']}:{runtime['model']}", token_receipt.get("prompt_tokens", 0), token_receipt.get("completion_tokens", 0)),
            "latency_ms": latency_ms,
            "tools_used": tools_used,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as usage_err:  # pragma: no cover
        print(f"CAOS engine_usage compute failed: {usage_err}")

    async def _persist_aftermath():
        try:
            ops = [
                collection("receipts").insert_one(receipt_record),
                collection("thread_summaries").insert_one(summary_record),
                collection("context_seeds").insert_one(seed_record),
                collection("sessions").update_one({"session_id": payload.session_id}, {"$set": title_updates}),
                upsert_global_info_entry(payload.user_email, payload.session_id, assistant_message.id, session_lane, list(subject_bins), retrieval_terms, reply),
            ]
            if hydration.use_lane_workers or "lane_workers" in proactivity.wake_departments:
                ops.append(rebuild_lane_workers(payload.user_email))
            if engine_usage_doc is not None:
                ops.append(collection("engine_usage").insert_one(engine_usage_doc))
            await asyncio.gather(*ops, return_exceptions=True)
        except Exception as exc:  # pragma: no cover
            print(f"CAOS turn aftermath failed: {exc}")

    asyncio.create_task(_persist_aftermath())
    _mark("handler_done")

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
