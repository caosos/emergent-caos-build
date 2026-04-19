from datetime import datetime, timezone
import uuid


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_receipt_record(
    session_id: str,
    assistant_message_id: str,
    source_message_ids: list[str],
    provider: str,
    model: str,
    receipt: dict,
    wcw_used_estimate: int,
    wcw_budget: int,
    previous_receipt_id: str | None = None,
    previous_summary_id: str | None = None,
    previous_seed_id: str | None = None,
    lineage_depth: int = 0,
) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "assistant_message_id": assistant_message_id,
        "source_message_ids": source_message_ids,
        "provider": provider,
        "model": model,
        "retrieval_terms": receipt.get("retrieval_terms", []),
        "selected_memory_ids": receipt.get("selected_memory_ids", []),
        "selected_summary_ids": receipt.get("selected_summary_ids", []),
        "selected_seed_ids": receipt.get("selected_seed_ids", []),
        "selected_worker_ids": receipt.get("selected_worker_ids", []),
        "lane": receipt.get("lane", "general"),
        "subject_bins": receipt.get("subject_bins", []),
        "previous_receipt_id": previous_receipt_id,
        "previous_summary_id": previous_summary_id,
        "previous_seed_id": previous_seed_id,
        "lineage_depth": lineage_depth,
        "token_source": receipt.get("token_source", "local_tokenizer_fallback"),
        "history_tokens": receipt.get("history_tokens", 0),
        "memory_tokens": receipt.get("memory_tokens", 0),
        "continuity_tokens": receipt.get("continuity_tokens", 0),
        "active_context_tokens": receipt.get("active_context_tokens", 0),
        "system_prompt_tokens": receipt.get("system_prompt_tokens", 0),
        "user_message_tokens": receipt.get("user_message_tokens", 0),
        "prompt_tokens": receipt.get("prompt_tokens", 0),
        "completion_tokens": receipt.get("completion_tokens", 0),
        "total_tokens": receipt.get("total_tokens", 0),
        "session_prompt_tokens_total": receipt.get("session_prompt_tokens_total", 0),
        "session_completion_tokens_total": receipt.get("session_completion_tokens_total", 0),
        "session_total_tokens": receipt.get("session_total_tokens", 0),
        "reduction_ratio": receipt.get("reduction_ratio", 0),
        "final_message_count": receipt.get("final_message_count", 0),
        "wcw_used_estimate": wcw_used_estimate,
        "wcw_budget": wcw_budget,
        "continuity_chars": receipt.get("continuity_chars", 0),
        "estimated_context_chars": receipt.get("estimated_context_chars", 0),
        "created_at": utc_now_iso(),
    }


def build_summary_record(
    session_id: str,
    user_text: str,
    assistant_text: str,
    lane: str,
    subject_bins: list[str],
    source_message_ids: list[str],
    previous_summary_id: str | None = None,
    lineage_depth: int = 0,
) -> dict:
    summary = assistant_text.strip().replace("\n", " ")[:280]
    return {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "lane": lane,
        "source_user_excerpt": user_text[:180],
        "summary": summary,
        "subject_bins": subject_bins,
        "source_message_ids": source_message_ids,
        "previous_summary_id": previous_summary_id,
        "lineage_depth": lineage_depth,
        "created_at": utc_now_iso(),
    }


def build_seed_record(
    session_id: str,
    receipt: dict,
    user_text: str,
    assistant_text: str,
    lane: str,
    subject_bins: list[str],
    source_message_ids: list[str],
    previous_seed_id: str | None = None,
    previous_summary_id: str | None = None,
    lineage_depth: int = 0,
) -> dict:
    topics = receipt.get("retrieval_terms", [])[:8]
    return {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "lane": lane,
        "topics": topics,
        "seed_text": f"User: {user_text[:140]} | Assistant: {assistant_text[:220]}",
        "subject_bins": subject_bins,
        "selected_memory_ids": receipt.get("selected_memory_ids", []),
        "source_message_ids": source_message_ids,
        "previous_seed_id": previous_seed_id,
        "previous_summary_id": previous_summary_id,
        "lineage_depth": lineage_depth,
        "created_at": utc_now_iso(),
    }