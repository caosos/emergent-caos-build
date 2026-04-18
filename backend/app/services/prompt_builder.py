from app.schemas.caos import MemoryEntry, MessageRecord, UserProfileRecord


def _format_memories(memories: list[MemoryEntry]) -> str:
    if not memories:
        return "No structured memory was retrieved for this turn."
    return "\n".join(f"- {memory.content}" for memory in memories)


def _format_history(history: list[MessageRecord]) -> str:
    if not history:
        return "No prior session history is available."
    return "\n".join(f"{message.role.upper()}: {message.content}" for message in history)


def build_system_prompt(
    profile: UserProfileRecord,
    sanitized_history: list[MessageRecord],
    injected_memories: list[MemoryEntry],
) -> str:
    preferred_name = profile.preferred_name or "the user"
    return f"""
You are Aria inside CAOS, a continuous AI workspace.

Operating rules:
- Treat `session_id` as the active isolation boundary.
- Use structured memory only when it was explicitly retrieved below.
- Never fabricate prior knowledge beyond the supplied memory and session history.
- Be concise, technically grounded, and useful.
- If the active history is thin, say so plainly instead of pretending continuity exists.

User profile:
- Preferred name: {preferred_name}
- Environment: {profile.environment_name}

Retrieved structured memory:
{_format_memories(injected_memories)}

Sanitized active session history:
{_format_history(sanitized_history)}
""".strip()