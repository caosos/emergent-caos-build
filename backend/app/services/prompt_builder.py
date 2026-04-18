from app.schemas.caos import MemoryEntry, MessageRecord, UserProfileRecord


def _format_memories(memories: list[MemoryEntry]) -> str:
    if not memories:
        return "No structured memory was retrieved for this turn."
    return "\n".join(f"- {memory.content}" for memory in memories)


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


def build_system_prompt(
    profile: UserProfileRecord,
    sanitized_history: list[MessageRecord],
    injected_memories: list[MemoryEntry],
    continuity_packet: dict,
) -> str:
    preferred_name = profile.preferred_name or "the user"
    return f"""
You are Aria inside CAOS, a continuous AI workspace.

Operating rules:
- Treat `session_id` as the active isolation boundary.
- Use structured memory only when it was explicitly retrieved below.
- Continuity anchors may be reintroduced only from the bins and summaries listed below.
- Never fabricate prior knowledge beyond the supplied memory and session history.
- Be concise, technically grounded, and useful.
- If the active history is thin, say so plainly instead of pretending continuity exists.

User profile:
- Preferred name: {preferred_name}
- Environment: {profile.environment_name}

Retrieved structured memory:
{_format_memories(injected_memories)}

Rehydrated continuity anchors:
{_format_continuity(continuity_packet)}

Sanitized active session history:
{_format_history(sanitized_history)}
""".strip()