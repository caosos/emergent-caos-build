from app.schemas.caos import MemoryEntry, MessageRecord, UserProfileRecord


def _format_memories(memories: list[MemoryEntry]) -> str:
    if not memories:
        return "No structured memory was retrieved for this turn."
    return "\n".join(f"- {memory.content}" for memory in memories)


def _split_memories(memories: list[MemoryEntry]) -> tuple[list[MemoryEntry], list[MemoryEntry]]:
    personal_facts = [memory for memory in memories if memory.bin_name == "personal_facts"]
    structured_memory = [memory for memory in memories if memory.bin_name != "personal_facts"]
    return personal_facts, structured_memory


def _format_history(history: list[MessageRecord]) -> str:
    if not history:
        return "No prior session history is available."
    return "\n".join(f"{message.role.upper()}: {message.content}" for message in history)


def _format_continuity(continuity_packet: dict) -> str:
    bins = continuity_packet.get("subject_bins", [])
    anchors = continuity_packet.get("continuity_lines", [])
    if not bins and not anchors:
        return "No prior continuity anchors were selected for reinjection this turn."
    lines = [f"- Active bins: {', '.join(bins) if bins else 'none'}"]
    lines.extend(f"- {anchor}" for anchor in anchors)
    return "\n".join(lines)


def build_prompt_sections(
    profile: UserProfileRecord,
    sanitized_history: list[MessageRecord],
    injected_memories: list[MemoryEntry],
    continuity_packet: dict,
) -> dict:
    personal_facts, structured_memory = _split_memories(injected_memories)
    return {
        "preferred_name": profile.preferred_name or "the user",
        "environment_name": profile.environment_name,
        "personal_facts_block": _format_memories(personal_facts),
        "structured_memory_block": _format_memories(structured_memory),
        "memory_block": _format_memories(injected_memories),
        "continuity_block": _format_continuity(continuity_packet),
        "history_block": _format_history(sanitized_history),
        "rehydration_order": "thread_history -> lane_continuity -> personal_facts -> structured_memory -> global_bin(empty)",
    }


def build_system_prompt_from_sections(sections: dict) -> str:
    return f"""
You are Aria inside CAOS, a continuous AI workspace.

Operating rules:
- Treat `session_id` as the active isolation boundary.
- Use structured memory only when it was explicitly retrieved below.
- Continuity anchors may be reintroduced only from the bins and summaries listed below.
- Follow this rehydration order exactly: {sections['rehydration_order']}.
- Never fabricate prior knowledge beyond the supplied memory and session history.
- Be concise, technically grounded, and useful.
- If the active history is thin, say so plainly instead of pretending continuity exists.

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
No cached global facts were reused this turn.
""".strip()


def build_system_prompt(
    profile: UserProfileRecord,
    sanitized_history: list[MessageRecord],
    injected_memories: list[MemoryEntry],
    continuity_packet: dict,
) -> str:
    return build_system_prompt_from_sections(
        build_prompt_sections(profile, sanitized_history, injected_memories, continuity_packet)
    )