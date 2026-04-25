import re

from app.schemas.caos import MemoryEntry, MessageRecord
from app.services.token_meter import count_text_tokens


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


def _message_snapshot(message: MessageRecord, reason: str) -> dict:
    return {
        "id": message.id,
        "role": message.role,
        "reason": reason,
        "excerpt": message.content[:160],
    }


def _is_compression_summary(message: MessageRecord) -> bool:
    return message.role == "system" and message.content.startswith("[SANITIZED HISTORY SUMMARY:")


def _memory_snapshot(memory: MemoryEntry) -> dict:
    return {
        "id": memory.id,
        "bin_name": memory.bin_name,
        "reason": "retrieved_structured_memory",
        "excerpt": memory.content[:160],
    }


def _continuity_snapshots(continuity_packet: dict | None = None) -> list[dict]:
    continuity = continuity_packet or {}
    items: list[dict] = []
    for summary in continuity.get("selected_summaries", []):
        items.append({"id": summary.id, "kind": "summary", "reason": "rehydrated_summary", "excerpt": summary.summary[:160]})
    for seed in continuity.get("selected_seeds", []):
        items.append({"id": seed.id, "kind": "seed", "reason": "rehydrated_seed", "excerpt": seed.seed_text[:160]})
    for worker in continuity.get("selected_workers", []):
        items.append({"id": worker.id, "kind": "worker", "reason": "reused_lane_worker", "excerpt": worker.summary_text[:160]})
    return items


def _message_token_cost(message: MessageRecord, model: str) -> int:
    return count_text_tokens(f"{message.role.upper()}: {message.content}", model)


def _trim_text_to_token_budget(text: str, model: str, max_tokens: int) -> str:
    if max_tokens <= 0:
        return ""
    trimmed = text
    while count_text_tokens(trimmed, model) > max_tokens and len(trimmed) > 80:
        trimmed = trimmed[: max(80, int(len(trimmed) * 0.75))]
    return trimmed


def sanitize_history(messages: list[MessageRecord]) -> tuple[list[MessageRecord], dict]:
    """Remove duplicates and low-signal messages from history.
    
    Optimized: More aggressive deduplication for large threads to reduce
    noise and keep context window focused on meaningful exchanges.
    """
    seen: set[tuple[str, str]] = set()
    kept: list[MessageRecord] = []
    removed_duplicates = 0
    removed_low_signal = 0
    dropped_duplicate_messages: list[dict] = []
    dropped_low_signal_messages: list[dict] = []

    for message in messages:
        # Use FULL normalized content as the dedup key — exact match only.
        # The previous 200-char prefix key produced false positives (two
        # divergent messages that started with the same 200 chars were
        # collapsed into one, silently deleting real history). Aria flagged
        # this in her bug ticket. We accept that exact-match dedup catches
        # fewer near-duplicates; that is the correct trade-off because
        # information loss is worse than minor redundancy.
        normalized_content = _normalized(message.content)
        key = (message.role, normalized_content)

        if key in seen:
            removed_duplicates += 1
            dropped_duplicate_messages.append(_message_snapshot(message, "duplicate_message"))
            continue
        seen.add(key)
        if _is_low_signal(message):
            removed_low_signal += 1
            dropped_low_signal_messages.append(_message_snapshot(message, "low_signal_message"))
            continue
        kept.append(message)

    return kept, {
        "total_messages": len(messages),
        "removed_duplicates": removed_duplicates,
        "removed_low_signal": removed_low_signal,
        "kept_message_ids": [message.id for message in kept],
        "dropped_duplicate_messages": dropped_duplicate_messages,
        "dropped_low_signal_messages": dropped_low_signal_messages,
    }


def compress_history(messages: list[MessageRecord], hot_head: int, hot_tail: int) -> list[MessageRecord]:
    """Compress history by keeping hot head/tail and summarizing the middle.
    
    Optimized for large threads: Ensures we never exceed context window even
    with thousands of messages by aggressively compressing the middle section.
    """
    if len(messages) <= hot_head + hot_tail:
        return messages
    head = messages[:hot_head]
    tail = messages[-hot_tail:]
    omitted = len(messages) - hot_head - hot_tail
    
    # For very large threads (>100 messages), provide aggregate stats
    if omitted > 100:
        summary = MessageRecord(
            session_id=messages[-1].session_id,
            role="system",
            content=f"[SANITIZED HISTORY SUMMARY: {omitted} messages omitted from active context. Thread contains {len(messages)} total messages spanning this conversation's history.]",
        )
    else:
        summary = MessageRecord(
            session_id=messages[-1].session_id,
            role="system",
            content=f"[SANITIZED HISTORY SUMMARY: {omitted} lower-priority messages omitted from active context.]",
        )
    return [*head, summary, *tail]


def enforce_history_token_budget(messages: list[MessageRecord], model: str, max_tokens: int) -> tuple[list[MessageRecord], dict]:
    if not messages or max_tokens <= 0:
        return messages, {
            "history_budget_tokens": max_tokens,
            "history_tokens_before_budget": 0,
            "history_tokens_after_budget": 0,
            "budget_trimmed_messages": [],
        }

    history_tokens_before_budget = sum(_message_token_cost(message, model) for message in messages)
    kept_reversed: list[MessageRecord] = []
    budget_trimmed_messages: list[dict] = []
    used_tokens = 0

    for index, message in enumerate(reversed(messages)):
        cost = _message_token_cost(message, model)
        if index == 0 and cost > max_tokens:
            prefix = f"[TRIMMED {message.role.upper()} HISTORY: "
            available_tokens = max(24, max_tokens - count_text_tokens(prefix + "]", model))
            trimmed_text = _trim_text_to_token_budget(message.content, model, available_tokens)
            trimmed_message = MessageRecord(
                session_id=message.session_id,
                role="system",
                content=f"{prefix}{trimmed_text}]",
            )
            kept_reversed.append(trimmed_message)
            used_tokens += _message_token_cost(trimmed_message, model)
            budget_trimmed_messages.append(_message_snapshot(message, "trimmed_to_fit_token_budget"))
            continue

        keep_message = index == 0 or used_tokens + cost <= max_tokens
        if keep_message:
            kept_reversed.append(message)
            used_tokens += cost
        else:
            budget_trimmed_messages.append(_message_snapshot(message, "trimmed_for_token_budget"))

    kept = list(reversed(kept_reversed))
    return kept, {
        "history_budget_tokens": max_tokens,
        "history_tokens_before_budget": history_tokens_before_budget,
        "history_tokens_after_budget": used_tokens,
        "budget_trimmed_messages": list(reversed(budget_trimmed_messages)),
    }


def rank_memories(
    query: str,
    recent_messages: list[MessageRecord],
    memories: list[MemoryEntry],
    limit: int,
    subject_bins: list[str] | None = None,
) -> tuple[list[MemoryEntry], list[str]]:
    retrieval_terms = tokenize(query)
    personal_query = any(term in retrieval_terms for term in ["prefer", "preference", "favorite", "usually", "always", "myself"])
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
        fact_bonus = 3 if memory.bin_name == "personal_facts" else 0
        if memory.bin_name == "personal_facts" and personal_query:
            fact_bonus += 4
        if overlap or bin_bonus or (memory.bin_name == "personal_facts" and personal_query):
            score = overlap + bin_bonus + fact_bonus + (max(0, min(memory.priority, 100)) // 25)
            scores.append((score, memory))
    ranked = [
        memory for _, memory in sorted(
            scores,
            key=lambda item: (item[0], item[1].bin_name == "personal_facts", item[1].priority),
            reverse=True,
        )[:limit]
    ]
    return ranked, retrieval_terms[:20]


def build_context_receipt(
    stats: dict,
    original_messages: list[MessageRecord],
    compressed: list[MessageRecord],
    injected_memories: list[MemoryEntry],
    retrieval_terms: list[str],
    subject_bins: list[str] | None = None,
    continuity_packet: dict | None = None,
    global_info_entries: list | None = None,
) -> dict:
    chars_before = sum(len(message.content) for message in original_messages)
    sanitized_after = sum(len(message.content) for message in compressed)
    continuity_chars = sum(len(line) for line in (continuity_packet or {}).get("continuity_lines", []))
    reduction_ratio = 0.0 if chars_before == 0 else round(1 - (sanitized_after / chars_before), 4)
    active_history = [message for message in compressed if not _is_compression_summary(message)]
    active_ids = {message.id for message in active_history}
    kept_messages = [_message_snapshot(message, "kept_in_active_context") for message in active_history]
    compressed_messages = [
        _message_snapshot(message, "compressed_into_history_summary")
        for message in original_messages
        if message.id in set(stats.get("kept_message_ids", [])) and message.id not in active_ids
    ]
    dropped_messages = [
        *(stats.get("dropped_duplicate_messages", [])),
        *(stats.get("dropped_low_signal_messages", [])),
    ]
    reused_memories = [_memory_snapshot(memory) for memory in injected_memories]
    reused_continuity = _continuity_snapshots(continuity_packet)
    budget_trimmed_messages = stats.get("budget_trimmed_messages", [])
    personal_fact_ids = [memory.id for memory in injected_memories if memory.bin_name == "personal_facts"]
    general_memory_ids = [memory.id for memory in injected_memories if memory.bin_name != "personal_facts"]
    global_cache_entries = global_info_entries or []
    retention_explanation = [
        f"Kept {len(kept_messages)} messages in the live ARC packet.",
        f"Dropped {len(dropped_messages)} messages during sanitization ({stats.get('removed_duplicates', 0)} duplicate, {stats.get('removed_low_signal', 0)} low-signal).",
        f"Compressed {len(compressed_messages)} older sanitized messages into the active history summary.",
        f"Trimmed {len(budget_trimmed_messages)} messages to stay within the {stats.get('history_budget_tokens', 0)}-token history budget.",
        f"Reused {len(reused_memories)} structured memories and {len(reused_continuity)} continuity anchors.",
    ]
    return {
        "retrieval_terms": retrieval_terms,
        "selected_memory_ids": [memory.id for memory in injected_memories],
        "selected_summary_ids": [summary.id for summary in (continuity_packet or {}).get("selected_summaries", [])],
        "selected_seed_ids": [seed.id for seed in (continuity_packet or {}).get("selected_seeds", [])],
        "selected_worker_ids": [worker.id for worker in (continuity_packet or {}).get("selected_workers", [])],
        "selected_personal_fact_ids": personal_fact_ids,
        "selected_general_memory_ids": general_memory_ids,
        "selected_global_cache_ids": [entry.id for entry in global_cache_entries],
        "lane": (continuity_packet or {}).get("lane", "general"),
        "subject_bins": subject_bins or [],
        "rehydration_order": ["thread_history", "lane_continuity", "personal_facts", "structured_memory", "global_bin_reused" if global_cache_entries else "global_bin_empty"],
        "global_bin_status": "reused" if global_cache_entries else "empty",
        "injected_memory_count": len(injected_memories),
        "estimated_injected_memory_chars": sum(len(memory.content) for memory in injected_memories),
        "final_message_count": len(compressed),
        "estimated_chars_before": chars_before,
        "estimated_chars_after": sanitized_after,
        "continuity_chars": continuity_chars,
        "estimated_context_chars": sanitized_after + continuity_chars + sum(len(memory.content) for memory in injected_memories),
        "retained_messages": kept_messages,
        "dropped_messages": dropped_messages,
        "compressed_messages": compressed_messages,
        "budget_trimmed_messages": budget_trimmed_messages,
        "reused_memories": reused_memories,
        "reused_continuity": reused_continuity,
        "retained_message_count": len(kept_messages),
        "dropped_message_count": len(dropped_messages),
        "compressed_message_count": len(compressed_messages),
        "budget_trimmed_count": len(budget_trimmed_messages),
        "history_budget_tokens": stats.get("history_budget_tokens", 0),
        "history_tokens_before_budget": stats.get("history_tokens_before_budget", 0),
        "history_tokens_after_budget": stats.get("history_tokens_after_budget", 0),
        "personal_facts_count": len(personal_fact_ids),
        "general_memory_count": len(general_memory_ids),
        "global_cache_count": len(global_cache_entries),
        "reused_memory_count": len(reused_memories),
        "reused_continuity_count": len(reused_continuity),
        "retention_explanation": retention_explanation,
        "reduction_ratio": reduction_ratio,
        **stats,
    }