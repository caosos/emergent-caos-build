import re

from app.schemas.caos import MemoryEntry, MessageRecord


STOPWORDS = {
    "the", "and", "for", "that", "with", "this", "have", "from", "your",
    "about", "just", "into", "they", "them", "then", "there", "been",
    "were", "what", "when", "where", "will", "would", "could", "should",
}
LOW_SIGNAL_PATTERNS = [
    re.compile(r"^(ok|okay|thanks|thank you|got it|cool|sure|yep|yeah|right)[!. ]*$", re.I),
    re.compile(r"^(sounds good|understood|makes sense)[!. ]*$", re.I),
]


def tokenize(text: str) -> list[str]:
    return [
        token for token in re.findall(r"[a-z0-9_]{3,}", text.lower())
        if token not in STOPWORDS
    ]


def extract_tags(text: str, limit: int = 6) -> list[str]:
    tags: list[str] = []
    for token in tokenize(text):
        if token not in tags:
            tags.append(token)
        if len(tags) >= limit:
            break
    return tags


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _is_low_signal(message: MessageRecord) -> bool:
    content = _normalized(message.content)
    if message.role == "system":
        return False
    if len(content) > 80:
        return False
    if "?" in content or any(ch.isdigit() for ch in content):
        return False
    return any(pattern.match(content) for pattern in LOW_SIGNAL_PATTERNS)


def sanitize_history(messages: list[MessageRecord]) -> tuple[list[MessageRecord], dict]:
    seen: set[tuple[str, str]] = set()
    kept: list[MessageRecord] = []
    removed_duplicates = 0
    removed_low_signal = 0

    for message in messages:
        key = (message.role, _normalized(message.content))
        if key in seen:
            removed_duplicates += 1
            continue
        seen.add(key)
        if _is_low_signal(message):
            removed_low_signal += 1
            continue
        kept.append(message)

    return kept, {
        "total_messages": len(messages),
        "removed_duplicates": removed_duplicates,
        "removed_low_signal": removed_low_signal,
    }


def compress_history(messages: list[MessageRecord], hot_head: int, hot_tail: int) -> list[MessageRecord]:
    if len(messages) <= hot_head + hot_tail:
        return messages
    head = messages[:hot_head]
    tail = messages[-hot_tail:]
    omitted = len(messages) - hot_head - hot_tail
    summary = MessageRecord(
        session_id=messages[-1].session_id,
        role="system",
        content=f"[SANITIZED HISTORY SUMMARY: {omitted} lower-priority messages omitted from active context.]",
    )
    return [*head, summary, *tail]


def rank_memories(
    query: str,
    recent_messages: list[MessageRecord],
    memories: list[MemoryEntry],
    limit: int,
    subject_bins: list[str] | None = None,
) -> tuple[list[MemoryEntry], list[str]]:
    retrieval_terms = tokenize(query)
    bin_terms = {item.split(":", 1)[-1] for item in (subject_bins or [])}
    for message in recent_messages[-5:]:
        for token in tokenize(message.content):
            if token not in retrieval_terms:
                retrieval_terms.append(token)
    scores: list[tuple[int, MemoryEntry]] = []
    for memory in memories:
        haystack = set(tokenize(memory.content))
        haystack.update(memory.tags)
        haystack.update(tokenize(memory.bin_name))
        overlap = sum(1 for term in retrieval_terms if term in haystack)
        bin_bonus = 2 if memory.bin_name in bin_terms else 0
        if overlap or bin_bonus:
            score = overlap + bin_bonus + (max(0, min(memory.priority, 100)) // 25)
            scores.append((score, memory))
    ranked = [memory for _, memory in sorted(scores, key=lambda item: item[0], reverse=True)[:limit]]
    return ranked, retrieval_terms[:20]


def build_context_receipt(
    stats: dict,
    original_messages: list[MessageRecord],
    compressed: list[MessageRecord],
    injected_memories: list[MemoryEntry],
    retrieval_terms: list[str],
    subject_bins: list[str] | None = None,
    continuity_packet: dict | None = None,
) -> dict:
    chars_before = sum(len(message.content) for message in original_messages)
    sanitized_after = sum(len(message.content) for message in compressed)
    reduction_ratio = 0.0 if chars_before == 0 else round(1 - (sanitized_after / chars_before), 4)
    return {
        "retrieval_terms": retrieval_terms,
        "selected_memory_ids": [memory.id for memory in injected_memories],
        "selected_summary_ids": [summary.id for summary in (continuity_packet or {}).get("selected_summaries", [])],
        "selected_seed_ids": [seed.id for seed in (continuity_packet or {}).get("selected_seeds", [])],
        "subject_bins": subject_bins or [],
        "injected_memory_count": len(injected_memories),
        "estimated_injected_memory_chars": sum(len(memory.content) for memory in injected_memories),
        "final_message_count": len(compressed),
        "estimated_chars_before": chars_before,
        "estimated_chars_after": sanitized_after,
        "reduction_ratio": reduction_ratio,
        **stats,
    }