from app.schemas.caos import MemoryEntry, MessageRecord, SeedRecord, SummaryRecord
from app.services.context_engine import tokenize


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
    limit: int = 2,
) -> dict:
    query_terms = set(tokenize(query)) | {item.split(":", 1)[-1] for item in subject_bins}
    scored_summaries = [
        (" ".join([summary.source_user_excerpt, summary.summary, *summary.subject_bins]), _score_overlap(
            " ".join([summary.source_user_excerpt, summary.summary, *summary.subject_bins]), query_terms, subject_bins
        ), summary)
        for summary in summaries
    ]
    scored_seeds = [
        (" ".join([seed.seed_text, *seed.topics, *seed.subject_bins]), _score_overlap(
            " ".join([seed.seed_text, *seed.topics, *seed.subject_bins]), query_terms, subject_bins
        ), seed)
        for seed in seeds
    ]
    selected_summaries = [
        item[2] for item in sorted(scored_summaries, key=lambda row: (row[1], row[2].created_at), reverse=True) if item[1] > 0
    ][:limit]
    selected_seeds = [
        item[2] for item in sorted(scored_seeds, key=lambda row: (row[1], row[2].created_at), reverse=True) if item[1] > 0
    ][:limit]
    continuity_lines = [summary.summary for summary in selected_summaries] + [seed.seed_text for seed in selected_seeds]
    return {
        "subject_bins": subject_bins,
        "selected_summaries": selected_summaries,
        "selected_seeds": selected_seeds,
        "continuity_lines": continuity_lines[:4],
    }