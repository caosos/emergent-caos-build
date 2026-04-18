from app.schemas.caos import LaneWorkerRecord, MemoryEntry, MessageRecord, SeedRecord, SummaryRecord
from app.services.context_engine import tokenize
from app.services.memory_worker_service import normalize_lane


def derive_subject_bins(
    query: str,
    recent_messages: list[MessageRecord],
    injected_memories: list[MemoryEntry] | None = None,
    limit: int = 4,
) -> list[str]:
    candidates: list[str] = []
    for token in tokenize(query):
        if token not in candidates:
            candidates.append(token)
    for message in recent_messages[-4:]:
        for token in tokenize(message.content):
            if token not in candidates:
                candidates.append(token)
    for memory in injected_memories or []:
        if memory.bin_name and memory.bin_name not in candidates:
            candidates.append(memory.bin_name)
    subject_bins = [f"topic:{token}" for token in candidates[:limit]]
    return subject_bins or ["topic:general"]


def _score_overlap(text: str, terms: set[str], subject_bins: list[str]) -> int:
    tokens = set(tokenize(text))
    bin_terms = {item.split(":", 1)[-1] for item in subject_bins}
    return len(tokens & terms) + len(tokens & bin_terms)


def build_continuity_packet(
    query: str,
    subject_bins: list[str],
    summaries: list[SummaryRecord],
    seeds: list[SeedRecord],
    workers: list[LaneWorkerRecord] | None = None,
    lane: str = "general",
    session_id: str | None = None,
    limit: int = 2,
) -> dict:
    query_terms = set(tokenize(query)) | {item.split(":", 1)[-1] for item in subject_bins}
    active_lane = normalize_lane(lane)

    def _lane_bonus(item_lane: str, item_session_id: str) -> int:
        bonus = 5 if normalize_lane(item_lane) == active_lane else 0
        if session_id and item_session_id == session_id:
            bonus += 4
        return bonus

    scored_summaries = []
    for summary in summaries:
        text = " ".join([summary.source_user_excerpt, summary.summary, *summary.subject_bins])
        scored_summaries.append((text, _score_overlap(text, query_terms, subject_bins) + _lane_bonus(summary.lane, summary.session_id), summary))
    scored_seeds = []
    for seed in seeds:
        text = " ".join([seed.seed_text, *seed.topics, *seed.subject_bins])
        scored_seeds.append((text, _score_overlap(text, query_terms, subject_bins) + _lane_bonus(seed.lane, seed.session_id), seed))
    selected_summaries = [
        item[2] for item in sorted(scored_summaries, key=lambda row: (row[1], row[2].created_at), reverse=True) if item[1] > 0
    ][:limit]
    selected_seeds = [
        item[2] for item in sorted(scored_seeds, key=lambda row: (row[1], row[2].created_at), reverse=True) if item[1] > 0
    ][:limit]
    scored_workers = []
    for worker in workers or []:
        if not worker.source_summary_ids and not worker.source_seed_ids:
            continue
        score = _score_overlap(worker.summary_text, query_terms, subject_bins)
        if normalize_lane(worker.lane) == active_lane:
            score += 5
        scored_workers.append((score, worker))
    selected_workers = [item[1] for item in sorted(scored_workers, key=lambda row: row[0], reverse=True) if item[0] > 0][:1]
    continuity_lines = [summary.summary[:240] for summary in selected_summaries] + [seed.seed_text[:240] for seed in selected_seeds] + [worker.summary_text[:240] for worker in selected_workers]
    return {
        "lane": active_lane,
        "subject_bins": subject_bins,
        "selected_summaries": selected_summaries,
        "selected_seeds": selected_seeds,
        "selected_workers": selected_workers,
        "continuity_lines": continuity_lines[:4],
    }