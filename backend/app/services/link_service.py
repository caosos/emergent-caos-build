from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit

from app.db import collection


URL_PATTERN = re.compile(r"((?:https?://|www\.)[^\s<>()\[\]{}\"']+)", re.IGNORECASE)
TRAILING_PUNCTUATION = ".,;:!?\"'>]}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_detected_url(value: str) -> str:
    url = (value or "").strip()
    while url and url[-1] in TRAILING_PUNCTUATION:
        url = url[:-1]
    while url.endswith(")") and url.count(")") > url.count("("):
        url = url[:-1]
    if url.startswith("www."):
        url = f"https://{url}"
    return url


def normalize_url(value: str) -> str:
    url = clean_detected_url(value)
    if not url:
        return ""
    parsed = urlsplit(url)
    scheme = (parsed.scheme or "https").lower()
    host = (parsed.netloc or parsed.path).lower()
    path = parsed.path if parsed.netloc else ""
    query = f"?{parsed.query}" if parsed.query else ""
    fragment = f"#{parsed.fragment}" if parsed.fragment else ""
    return f"{scheme}://{host}{path}{query}{fragment}".rstrip("/") or url


def infer_link_label(url: str) -> str:
    parsed = urlsplit(clean_detected_url(url))
    host = (parsed.netloc or parsed.path or url).replace("www.", "")
    return host or url


def extract_links_from_text(text: str) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in URL_PATTERN.findall(text or ""):
        cleaned = clean_detected_url(match)
        normalized = normalize_url(cleaned)
        if not cleaned or not normalized or normalized in seen:
            continue
        seen.add(normalized)
        found.append({
            "url": cleaned,
            "normalized_url": normalized,
            "label": infer_link_label(cleaned),
            "host": infer_link_label(cleaned),
        })
    return found


def build_user_link_record(user: dict, session_id: str, url: str, label: str | None = None, source: str = "manual") -> dict:
    cleaned = clean_detected_url(url)
    normalized = normalize_url(cleaned)
    host = infer_link_label(cleaned)
    now = _utc_now()
    return {
        "id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        "user_email": user["email"],
        "session_id": session_id,
        "url": cleaned,
        "normalized_url": normalized,
        "label": (label or host).strip(),
        "host": host,
        "source": source,
        "mention_count": 1,
        "created_at": now,
        "updated_at": now,
    }


async def upsert_session_links(user: dict, session_id: str, links: list[dict[str, str]], source: str = "auto") -> list[dict]:
    records: list[dict] = []
    for link in links:
        candidate = build_user_link_record(
            user,
            session_id,
            link.get("url", ""),
            link.get("label") or infer_link_label(link.get("url", "")),
            source=source,
        )
        if not candidate["normalized_url"]:
            continue
        await collection("user_links").update_one(
            {
                "user_id": user["user_id"],
                "session_id": session_id,
                "normalized_url": candidate["normalized_url"],
            },
            {
                "$setOnInsert": {
                    "id": candidate["id"],
                    "user_id": candidate["user_id"],
                    "user_email": candidate["user_email"],
                    "session_id": candidate["session_id"],
                    "created_at": candidate["created_at"],
                },
                "$set": {
                    "url": candidate["url"],
                    "normalized_url": candidate["normalized_url"],
                    "label": candidate["label"],
                    "host": candidate["host"],
                    "source": source,
                    "updated_at": candidate["updated_at"],
                },
                "$inc": {"mention_count": 1},
            },
            upsert=True,
        )
        doc = await collection("user_links").find_one(
            {
                "user_id": user["user_id"],
                "session_id": session_id,
                "normalized_url": candidate["normalized_url"],
            },
            {"_id": 0},
        )
        if doc:
            records.append(doc)
    return records


async def capture_links_from_message(user: dict, session_id: str, text: str) -> list[dict]:
    extracted = extract_links_from_text(text)
    if not extracted:
        return []
    return await upsert_session_links(user, session_id, extracted, source="auto")


def legacy_file_link_to_user_link(doc: dict) -> dict:
    url = doc.get("url") or ""
    host = infer_link_label(url)
    created_at = doc.get("created_at") or _utc_now()
    return {
        "id": doc.get("id") or str(uuid.uuid4()),
        "user_email": doc.get("user_email", ""),
        "session_id": doc.get("session_id"),
        "url": clean_detected_url(url),
        "normalized_url": normalize_url(url),
        "label": doc.get("name") or host,
        "host": host,
        "source": "legacy",
        "mention_count": 1,
        "created_at": created_at,
        "updated_at": created_at,
    }