from datetime import datetime, timezone
import uuid


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_receipt_record(
    session_id: str,
    assistant_message_id: str,
    provider: str,
    model: str,
    receipt: dict,
    wcw_used_estimate: int,
    wcw_budget: int,
) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "assistant_message_id": assistant_message_id,
        "provider": provider,
        "model": model,
        "retrieval_terms": receipt.get("retrieval_terms", []),
        "selected_memory_ids": receipt.get("selected_memory_ids", []),
        "reduction_ratio": receipt.get("reduction_ratio", 0),
        "final_message_count": receipt.get("final_message_count", 0),
        "wcw_used_estimate": wcw_used_estimate,
        "wcw_budget": wcw_budget,
        "created_at": utc_now_iso(),
    }


def build_summary_record(session_id: str, user_text: str, assistant_text: str) -> dict:
    summary = assistant_text.strip().replace("\n", " ")[:280]
    return {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "source_user_excerpt": user_text[:180],
        "summary": summary,
        "created_at": utc_now_iso(),
    }


def build_seed_record(session_id: str, receipt: dict, user_text: str, assistant_text: str) -> dict:
    topics = receipt.get("retrieval_terms", [])[:8]
    return {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "topics": topics,
        "seed_text": f"User: {user_text[:140]} | Assistant: {assistant_text[:220]}",
        "selected_memory_ids": receipt.get("selected_memory_ids", []),
        "created_at": utc_now_iso(),
    }