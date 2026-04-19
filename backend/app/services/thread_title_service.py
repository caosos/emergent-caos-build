from collections import Counter

from app.schemas.caos import MessageRecord
from app.services.context_engine import tokenize
from app.services.memory_worker_service import normalize_lane


GENERIC_TITLES = {"new thread", "continued thread", "chat", "general thread", "runtime smoke"}
TITLE_STOPWORDS = {
    "need", "want", "please", "make", "build", "help", "working", "works", "thing",
    "system", "using", "there", "their", "about", "would", "could", "should", "thread",
    "continue", "continuity", "message", "messages", "actually", "already", "going",
}


def is_generic_session_title(title: str | None) -> bool:
    value = (title or "").strip().lower()
    if not value:
        return True
    if value in GENERIC_TITLES:
        return True
    return value.startswith("test ") or value.startswith("new ") or value.startswith("continued ")


def build_auto_thread_title(messages: list[MessageRecord], lane: str) -> str:
    user_messages = [message for message in messages if message.role == "user"][:3]
    combined = " ".join(message.content for message in user_messages)
    tokens = [token for token in tokenize(combined) if token not in TITLE_STOPWORDS]
    counts = Counter(tokens)
    ordered = []
    for token in tokens:
        if token not in ordered:
            ordered.append(token)
    ranked = sorted(ordered, key=lambda token: (-counts[token], ordered.index(token)))[:4]
    lane_token = normalize_lane(lane)
    if lane_token != "general" and lane_token not in ranked:
        ranked.insert(0, lane_token)
    ranked = ranked[:4]
    if not ranked:
        return "General Thread" if lane_token == "general" else f"{lane_token.title()} Thread"
    return " ".join(token.replace("_", " ").title() for token in ranked)[:48]