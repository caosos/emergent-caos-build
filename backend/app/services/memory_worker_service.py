from collections import Counter, defaultdict

from app.db import collection
from app.schemas.caos import LaneWorkerRecord, SeedRecord, SessionRecord, SummaryRecord
from app.services.context_engine import tokenize


WEAK_LANE_TOKENS = {"general", "lane", "thread", "chat", "session", "new", "continued", "remember", "should", "most", "week"}


def normalize_lane(value: str | None) -> str:
    lane = (value or "general").strip().lower().replace("topic:", "")
    return lane or "general"


def derive_lane(subject_bins: list[str] | None, title: str | None = None, existing_lane: str | None = None) -> str:
    if existing_lane and normalize_lane(existing_lane) != "general":
        return normalize_lane(existing_lane)
    title_tokens = [token for token in tokenize(title or "") if token not in WEAK_LANE_TOKENS]
    if title_tokens:
        return title_tokens[0]
    for bin_name in subject_bins or []:
        token = normalize_lane(bin_name)
        if token not in WEAK_LANE_TOKENS:
            return token
    tokens = tokenize(title or "")
    return tokens[0] if tokens else "general"


def _compose_worker_summary(summaries: list[SummaryRecord], seeds: list[SeedRecord], lane: str) -> str:
    recent_lines = [item.summary for item in summaries[:2]] + [item.seed_text for item in seeds[:2]]
    if recent_lines:
        return " | ".join(recent_lines)[:420]
    return f"Lane {lane} has no durable continuity yet."


async def rebuild_lane_workers(user_email: str) -> list[LaneWorkerRecord]:
    session_docs = await collection("sessions").find({"user_email": user_email}, {"_id": 0}).to_list(200)
    sessions = [SessionRecord(**doc) for doc in session_docs]
    session_ids = [session.session_id for session in sessions]
    if not session_ids:
        return []
    summary_docs = await collection("thread_summaries").find({"session_id": {"$in": session_ids}}, {"_id": 0}).sort("created_at", -1).to_list(400)
    seed_docs = await collection("context_seeds").find({"session_id": {"$in": session_ids}}, {"_id": 0}).sort("created_at", -1).to_list(400)
    summaries = [SummaryRecord(**doc) for doc in summary_docs]
    seeds = [SeedRecord(**doc) for doc in seed_docs]
    lane_map = {session.session_id: derive_lane([], session.title, session.lane) for session in sessions}
    grouped_summaries: dict[str, list[SummaryRecord]] = defaultdict(list)
    grouped_seeds: dict[str, list[SeedRecord]] = defaultdict(list)
    for summary in summaries:
        grouped_summaries[derive_lane(summary.subject_bins, existing_lane=summary.lane or lane_map.get(summary.session_id))].append(summary)
    for seed in seeds:
        grouped_seeds[derive_lane(seed.subject_bins, existing_lane=seed.lane or lane_map.get(seed.session_id))].append(seed)
    workers: list[LaneWorkerRecord] = []
    for lane in sorted(set(grouped_summaries) | set(grouped_seeds) | set(lane_map.values())):
        lane_summaries = grouped_summaries.get(lane, [])
        lane_seeds = grouped_seeds.get(lane, [])
        counter = Counter(bin_name for item in [*lane_summaries, *lane_seeds] for bin_name in item.subject_bins)
        worker = LaneWorkerRecord(
            user_email=user_email,
            lane=lane,
            subject_bins=[item for item, _ in counter.most_common(6)] or [f"topic:{lane}"],
            summary_text=_compose_worker_summary(lane_summaries, lane_seeds, lane),
            source_session_ids=sorted({item.session_id for item in [*lane_summaries, *lane_seeds]}),
            source_summary_ids=[item.id for item in lane_summaries[:12]],
            source_seed_ids=[item.id for item in lane_seeds[:12]],
        )
        await collection("lane_workers").update_one(
            {"user_email": user_email, "lane": lane},
            {"$set": {**worker.model_dump(), "refreshed_at": worker.refreshed_at.isoformat()}},
            upsert=True,
        )
        workers.append(worker)
    return workers


async def list_lane_workers(user_email: str) -> list[LaneWorkerRecord]:
    docs = await collection("lane_workers").find({"user_email": user_email}, {"_id": 0}).sort("refreshed_at", -1).to_list(100)
    return [LaneWorkerRecord(**doc) for doc in docs]