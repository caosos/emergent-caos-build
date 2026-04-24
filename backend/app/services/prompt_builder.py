from app.schemas.caos import MemoryEntry, MessageRecord, UserProfileRecord


def _format_memories(memories: list[MemoryEntry]) -> str:
    if not memories:
        return "No structured memory was retrieved for this turn."
    lines = []
    for memory in memories:
        created = getattr(memory, "created_at", None)
        updated = getattr(memory, "updated_at", None)
        try:
            created_label = created.strftime("%Y-%m-%d %H:%M UTC") if created else "unknown"
            updated_label = updated.strftime("%Y-%m-%d %H:%M UTC") if updated else created_label
        except Exception:
            created_label = str(created or "unknown")
            updated_label = str(updated or created or "unknown")
        lines.append(f"- [memory recorded {created_label}; last updated {updated_label}] {memory.content}")
    return "\n".join(lines)


def _split_memories(memories: list[MemoryEntry]) -> tuple[list[MemoryEntry], list[MemoryEntry]]:
    personal_facts = [memory for memory in memories if memory.bin_name == "personal_facts"]
    structured_memory = [memory for memory in memories if memory.bin_name != "personal_facts"]
    return personal_facts, structured_memory


def _format_history(history: list[MessageRecord]) -> str:
    if not history:
        return "No prior session history is available."
    lines: list[str] = []
    for message in history:
        # Prepend a compact timestamp so Aria can calculate temporal deltas
        # ("this was said 3 days ago"). Falls back to role-only if missing.
        ts = getattr(message, "timestamp", None)
        try:
            when = ts.strftime("%b %-d, %-I:%M %p") if ts else ""
        except Exception:
            when = str(ts) if ts else ""
        stamp = f" [{when}]" if when else ""
        lines.append(f"{message.role.upper()}{stamp}: {message.content}")
    return "\n".join(lines)


def _format_continuity(continuity_packet: dict) -> str:
    bins = continuity_packet.get("subject_bins", [])
    anchors = continuity_packet.get("continuity_lines", [])
    if not bins and not anchors:
        return "No prior continuity anchors were selected for reinjection this turn."
    lines = [
        f"- Active bins: {', '.join(bins) if bins else 'none'}",
        "- Temporal rule: when a continuity line includes a timestamp, treat that timestamp as the event/update date for any relative date math.",
        "- Rehydration rule: a fact being injected right now does NOT mean it happened right now. Use the anchor date attached to that fact, summary, or seed.",
    ]
    lines.extend(f"- {anchor}" for anchor in anchors)
    return "\n".join(lines)


def _format_global_info(entries: list[dict]) -> str:
    if not entries:
        return "No cached global facts were reused this turn."
    return "\n".join(f"- {entry['snippet']}" for entry in entries)


def _format_attachments(attachments: list[dict], provider_supports_vision: bool = False) -> str:
    if not attachments:
        return "No files have been attached to this thread."
    lines = []
    for item in attachments:
        size_kb = max(1, int(item.get("size", 0) / 1024))
        kind = item.get("kind", "file")
        mime = item.get("mime_type", "application/octet-stream")
        lines.append(f"- [{kind}] {item.get('name')} ({mime}, ~{size_kb}KB)")
    hint = (
        "These attachments are included as binary inputs below; inspect them directly."
        if provider_supports_vision
        else "NOTE: Binary contents of these files are NOT visible to you on this provider. "
        "You can reference them by name/type. To let the AI see image/file contents, "
        "the user should switch the engine to Gemini."
    )
    return "\n".join(lines) + "\n" + hint


def build_prompt_sections(
    profile: UserProfileRecord,
    sanitized_history: list[MessageRecord],
    injected_memories: list[MemoryEntry],
    continuity_packet: dict,
    global_info_entries: list[dict] | None = None,
    attachments: list[dict] | None = None,
    provider: str | None = None,
) -> dict:
    personal_facts, structured_memory = _split_memories(injected_memories)
    global_entries = global_info_entries or []
    attachment_items = attachments or []
    provider_supports_vision = provider == "gemini"
    return {
        "assistant_name": profile.assistant_name or "Aria",
        "preferred_name": profile.preferred_name or "the user",
        "environment_name": profile.environment_name,
        "personal_facts_block": _format_memories(personal_facts),
        "structured_memory_block": _format_memories(structured_memory),
        "memory_block": _format_memories(injected_memories),
        "continuity_block": _format_continuity(continuity_packet),
        "global_info_block": _format_global_info(global_entries),
        "attachments_block": _format_attachments(attachment_items, provider_supports_vision),
        "history_block": _format_history(sanitized_history),
        "rehydration_order": f"thread_history -> lane_continuity -> personal_facts -> structured_memory -> {'global_bin(reused)' if global_entries else 'global_bin(empty)'}",
    }


def build_system_prompt_from_sections(sections: dict) -> str:
    tools_block = ""
    # Tool access now open to all authenticated users (freemium model)
    if sections.get("admin_tools_allowed") or True:  # Always include tools
        tools_block = (
            "\n- **Read-only code inspection & web tools**: when the user asks about specific code behavior, file contents, implementation details, or needs real-time information, emit ONE tool marker on its own line. The pipeline will run the tool, feed the result back, and you will continue. You have AT MOST 3 tool calls per reply. Do NOT use tools for casual chat or questions you can already answer from context."
            "\n  - **Project structure you are inspecting**:"
            "\n    - Frontend: React + plain JavaScript under `/app/frontend/src/` (files are `*.js`, NOT `.tsx` or `.ts`). Main CAOS components live in `/app/frontend/src/components/caos/`."
            "\n    - Backend: FastAPI + Python under `/app/backend/app/` (files are `*.py`). Routes in `/app/backend/app/routes/`, services in `/app/backend/app/services/`, schemas in `/app/backend/app/schemas/caos.py`."
            "\n    - Product docs + handoff summaries: `/app/memory/*.md`."
            "\n  - `[TOOL: read_file path=/absolute/path/to/file]` — returns up to 64 KB of a file."
            "\n  - `[TOOL: list_dir path=/absolute/path]` — returns a 2-deep tree."
            "\n  - `[TOOL: grep_code pattern=<regex> path=/absolute/path glob=*.js]` — returns up to 50 matching `file:line: text` lines. Default glob is `*.py`; use `*.js` for frontend searches."
            "\n  - `[TOOL: web_fetch url=<https_url> mode=auto]` — fetches a public webpage or raw file (128 KB cap, 15s timeout). `mode=text` strips HTML, `mode=raw` returns verbatim, `mode=auto` picks based on content-type. Use this for live documentation, news, API references, release notes, and any real-time info beyond your training cutoff. Cite the final URL in your reply."
            "\n  - `[TOOL: github_fetch repo=<owner>/<name> path=<file> ref=main]` — fetches a file from a public GitHub repo via raw.githubusercontent.com. Example: `[TOOL: github_fetch repo=facebook/react path=README.md]`. Use this when the user references GitHub code you haven't seen in `/app`."
            "\n  After each tool result comes back, produce your next step: either another tool call (if you need more data) or the final user-facing reply (no more markers). Cite exact file paths and line numbers when you explain what you found. Secrets (`.env`, `*.key`, `*.pem`, `credentials*`, `secrets*`) are blocked at the tool layer — don't try to read them."
        )
    import datetime as _dt
    _now = _dt.datetime.now(_dt.timezone.utc)
    _time_block = (
        f"\n\nTIME_CONTEXT (authoritative — anchor ALL temporal math to this, NOT to any date you see in older messages):"
        f"\n- Today is {_now.strftime('%A, %B %-d, %Y')}"
        f"\n- Current UTC timestamp: {_now.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        f"\n- When you see phrases like 'in 7 days' or 'next week' in history, calculate relative to the date/time stamp on THAT message, not today. When the user asks 'what day is it?' or similar, answer with the date above."
        f"\n- If memory or continuity is rehydrated into the prompt, NEVER treat the injection moment as the fact date. Use the attached source-window / recorded timestamp instead."
    )
    return f"""
You are {sections.get('assistant_name', 'Aria')} inside {sections['environment_name']}, a continuous AI workspace.{_time_block}

Operating rules:
- Treat `session_id` as the active isolation boundary.
- Use structured memory only when it was explicitly retrieved below.
- Continuity anchors may be reintroduced only from the bins and summaries listed below.
- Follow this rehydration order exactly: {sections['rehydration_order']}.
- Never fabricate prior knowledge beyond the supplied memory and session history.
- Be concise, technically grounded, and useful.
- **Formatting contract (always on)**:
  - Use clean markdown that renders well in CAOS.
  - Use `##` for major sections and `###` for sub-sections when structure helps.
  - Use proper markdown tables for comparisons, matrices, and multi-column data. Always include a header row.
  - Use bullet lists for non-sequential items and numbered lists only for steps.
  - Keep paragraphs short (max 3-4 sentences). Avoid walls of text.
  - Use fenced code blocks with language tags for multiline code.
  - Lead with the answer. No filler like "Certainly!" or "Great question!"
  - If the user explicitly asks you to adopt a formatting contract, acknowledge it once with exactly `Formatting contract accepted.` then continue following it on future replies without repeating that line.
- If the active history is thin, say so plainly instead of pretending continuity exists.
- **Fact discipline**: prefer verifiable statements. If you are not sure, say "I'm not sure" instead of guessing. When the user asks about code, files, or tool output you cannot see, say so explicitly rather than inventing details. Cite the source (history / memory / tool output) when you rely on specific facts.
- **Complaint / suggestion flagging**: if the user expresses dissatisfaction ("this is broken", "I hate X", "it doesn't work"), a feature request ("I wish it could", "it would be nice if"), or a bug report, briefly ask in-chat: "Would you like me to file a support ticket on your behalf?" If they confirm (yes/sure/do it/please), emit a SINGLE tool marker on its own line at the END of your reply in this exact format:
  `[FILE_TICKET: category=bug|feature|ux|other, title=<short title>, description=<1-2 sentence summary of the user's concern>]`
  Do NOT emit the marker unless the user has explicitly confirmed. Only one marker per reply. The system will strip it from the visible reply and create the ticket automatically.
- **System awareness**: the "System status" block below reflects the live health of CAOS subsystems and the user's open ticket count. When a user reports something broken, cross-check against that block before speculating. If a subsystem is DEGRADED, name it plainly.{tools_block}

User profile:
- Preferred name: {sections['preferred_name']}
- Environment: {sections['environment_name']}

Sanitized active thread history:
{sections['history_block']}

Lane continuity anchors:
{sections['continuity_block']}

Personal facts:
{sections['personal_facts_block']}

Structured memory:
{sections['structured_memory_block']}

Global bin:
{sections['global_info_block']}

Attachments in this thread:
{sections['attachments_block']}

System status:
{sections.get('awareness_block', 'awareness unavailable')}
""".strip()


def build_system_prompt(
    profile: UserProfileRecord,
    sanitized_history: list[MessageRecord],
    injected_memories: list[MemoryEntry],
    continuity_packet: dict,
    global_info_entries: list[dict] | None = None,
) -> str:
    return build_system_prompt_from_sections(
        build_prompt_sections(profile, sanitized_history, injected_memories, continuity_packet, global_info_entries)
    )