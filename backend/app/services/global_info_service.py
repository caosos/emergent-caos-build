from datetime import datetime, timezone

from app.db import collection
from app.schemas.caos import GlobalInfoEntry
from app.services.context_engine import tokenize
from app.services.memory_worker_service import normalize_lane


def _signature(lane: str, retrieval_terms: list[str], subject_bins: list[str]) -> str:
    terms = sorted(set([*retrieval_terms[:8], *subject_bins[:4]]))
    return f"{normalize_lane(lane)}::{ '|'.join(terms) }"


async def list_global_info_entries(user_email: str, lane: str | None = None) -> list[GlobalInfoEntry]:
    query = {"user_email": user_email}
    if lane:
        query["lane"] = normalize_lane(lane)
    docs = await collection("global_info_bin").find(query, {"_id": 0}).sort("updated_at", -1).to_list(100)
    return [GlobalInfoEntry(**doc) for doc in docs]


async def select_global_info_entries(user_email: str, query: str, subject_bins: list[str], lane: str, limit: int = 2) -> list[GlobalInfoEntry]:
    entries = await list_global_info_entries(user_email)
    query_terms = set(tokenize(query)) | {item.split(":", 1)[-1] for item in subject_bins}
    active_lane = normalize_lane(lane)
    scored: list[tuple[int, GlobalInfoEntry]] = []
    for entry in entries:
        entry_terms = set(entry.retrieval_terms) | set(tokenize(entry.snippet)) | {item.split(":", 1)[-1] for item in entry.subject_bins}
        overlap = len(query_terms & entry_terms)
        lane_bonus = 4 if normalize_lane(entry.lane) == active_lane else 0
        score = overlap + lane_bonus + min(entry.hits, 5)
        if score > 0:
            scored.append((score, entry))
    return [entry for _, entry in sorted(scored, key=lambda row: (row[0], row[1].updated_at), reverse=True)[:limit]]


async def upsert_global_info_entry(
    user_email: str,
    session_id: str,
    assistant_message_id: str,
    lane: str,
    subject_bins: list[str],
    retrieval_terms: list[str],
    assistant_reply: str,
):
    if len(assistant_reply.strip()) < 80 or not retrieval_terms:
        return None
    signature = _signature(lane, retrieval_terms, subject_bins)
    existing = await collection("global_info_bin").find_one({"user_email": user_email, "signature": signature}, {"_id": 0})
    snippet = assistant_reply.strip().replace("\n", " ")[:320]
    if existing:
        hits = existing.get("hits", 1) + 1
        await collection("global_info_bin").update_one(
            {"user_email": user_email, "signature": signature},
            {"$set": {
                "lane": normalize_lane(lane),
                "subject_bins": subject_bins,
                "retrieval_terms": retrieval_terms[:16],
                "snippet": snippet,
                "source_session_id": session_id,
                "source_message_id": assistant_message_id,
                "hits": hits,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        return existing.get("id")

    entry = GlobalInfoEntry(
        user_email=user_email,
        lane=normalize_lane(lane),
        subject_bins=subject_bins,
        retrieval_terms=retrieval_terms[:16],
        snippet=snippet,
        source_session_id=session_id,
        source_message_id=assistant_message_id,
    )
    doc = entry.model_dump()
    doc["signature"] = signature
    doc["created_at"] = entry.created_at.isoformat()
    doc["updated_at"] = entry.updated_at.isoformat()
    await collection("global_info_bin").insert_one(doc)
    return entry.id