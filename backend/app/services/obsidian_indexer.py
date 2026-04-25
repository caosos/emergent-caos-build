"""Obsidian vault indexer.

Aria treats an Obsidian vault as a flat searchable corpus of markdown notes
plus metadata (tags, frontmatter, wikilinks, backlinks). The user uploads
their vault from the Connectors drawer; the indexer parses + stores every
note. There is NO live sync — re-uploading replaces the vault.

Storage
=======
collection `obsidian_notes`:
  user_email         str — owner
  path               str — vault-relative path ("daily/2026-04-25.md")
  title              str — first H1, frontmatter `title`, or filename stem
  content            str — full markdown body (capped at 256KB per note)
  size_bytes         int
  word_count         int
  tags               list[str] — extracted from #tags + frontmatter
  wikilinks          list[str] — outbound [[Note Name]] references
  backlinks          list[str] — populated post-index (notes pointing to this)
  frontmatter        dict — parsed YAML frontmatter (None if absent)
  uploaded_at        ISO datetime

A `obsidian_vaults` row tracks the vault metadata per user (size, note count,
last upload) so the Connectors UI can show "Connected · 412 notes".
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.db import collection

MAX_NOTE_BYTES = 256 * 1024
WIKILINK_RX = re.compile(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")
TAG_RX = re.compile(r"(?:^|\s)#([\w\-/]+)")
FRONTMATTER_RX = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
HEADING_RX = re.compile(r"^# (.+)$", re.MULTILINE)


def _parse_frontmatter(body: str) -> tuple[dict[str, Any] | None, str]:
    """Strip + parse YAML frontmatter. Returns (frontmatter_dict_or_None, body_without_frontmatter)."""
    match = FRONTMATTER_RX.match(body)
    if not match:
        return None, body
    raw = match.group(1)
    fm: dict[str, Any] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        key = k.strip()
        val = v.strip().strip("\"'")
        if not key:
            continue
        # Crude list parser: tags: [a, b]
        if val.startswith("[") and val.endswith("]"):
            fm[key] = [piece.strip().strip("\"'") for piece in val[1:-1].split(",") if piece.strip()]
        else:
            fm[key] = val
    return fm, body[match.end():]


def _extract_tags(body: str, frontmatter: dict[str, Any] | None) -> list[str]:
    tags: set[str] = set()
    for m in TAG_RX.finditer(body):
        tags.add(m.group(1))
    if frontmatter and "tags" in frontmatter:
        fm_tags = frontmatter.get("tags")
        if isinstance(fm_tags, list):
            for t in fm_tags:
                if isinstance(t, str) and t.strip():
                    tags.add(t.strip().lstrip("#"))
        elif isinstance(fm_tags, str):
            tags.add(fm_tags.strip().lstrip("#"))
    return sorted(tags)


def _extract_wikilinks(body: str) -> list[str]:
    return sorted({m.group(1).strip() for m in WIKILINK_RX.finditer(body) if m.group(1).strip()})


def _derive_title(path: str, body: str, frontmatter: dict[str, Any] | None) -> str:
    if frontmatter and frontmatter.get("title"):
        return str(frontmatter["title"])
    h1 = HEADING_RX.search(body)
    if h1:
        return h1.group(1).strip()
    stem = path.rsplit("/", 1)[-1]
    if stem.endswith(".md"):
        stem = stem[:-3]
    return stem or "(untitled)"


async def index_vault(user_email: str, notes: list[dict[str, str]]) -> dict[str, Any]:
    """Replace the user's existing vault with a fresh upload.

    `notes` is a list of `{path, content}` dicts straight from the frontend
    File-API reader. We parse, store, then run a second pass to populate
    backlinks now that all titles are known.

    Returns a summary dict: {note_count, total_bytes, tag_count}.
    """
    if not user_email:
        raise ValueError("user_email required")
    now = datetime.now(timezone.utc).isoformat()

    # Wipe previous vault for this user.
    await collection("obsidian_notes").delete_many({"user_email": user_email})

    docs_to_insert: list[dict[str, Any]] = []
    title_to_path: dict[str, str] = {}
    total_bytes = 0
    all_tags: set[str] = set()

    for note in notes:
        path = (note.get("path") or "").strip().lstrip("/")
        content = note.get("content") or ""
        if not path or not path.endswith(".md"):
            continue
        # Cap each note to MAX_NOTE_BYTES so a giant doc can't blow the DB.
        encoded = content.encode("utf-8", errors="replace")
        if len(encoded) > MAX_NOTE_BYTES:
            content = encoded[:MAX_NOTE_BYTES].decode("utf-8", errors="replace") + "\n\n[truncated by indexer]"
            note_size = MAX_NOTE_BYTES
        else:
            note_size = len(encoded)

        frontmatter, body_no_fm = _parse_frontmatter(content)
        title = _derive_title(path, body_no_fm, frontmatter)
        tags = _extract_tags(body_no_fm, frontmatter)
        wikilinks = _extract_wikilinks(body_no_fm)
        word_count = len(body_no_fm.split())

        title_to_path[title.lower()] = path
        all_tags.update(tags)
        total_bytes += note_size

        docs_to_insert.append({
            "user_email": user_email,
            "path": path,
            "title": title,
            "content": content,
            "size_bytes": note_size,
            "word_count": word_count,
            "tags": tags,
            "wikilinks": wikilinks,
            "backlinks": [],  # filled in post-pass
            "frontmatter": frontmatter,
            "uploaded_at": now,
        })

    if docs_to_insert:
        await collection("obsidian_notes").insert_many(docs_to_insert)

    # Backlink pass: for every note that wikilinks to <Title>, add this note's
    # title to that target's `backlinks`. Cheap because we already have all
    # titles in title_to_path.
    backlink_buckets: dict[str, list[str]] = {}
    for doc in docs_to_insert:
        for link in doc["wikilinks"]:
            target_path = title_to_path.get(link.lower())
            if target_path:
                backlink_buckets.setdefault(target_path, []).append(doc["title"])
    for path, sources in backlink_buckets.items():
        await collection("obsidian_notes").update_one(
            {"user_email": user_email, "path": path},
            {"$set": {"backlinks": sorted(set(sources))}},
        )

    summary = {
        "note_count": len(docs_to_insert),
        "total_bytes": total_bytes,
        "tag_count": len(all_tags),
        "uploaded_at": now,
    }
    await collection("obsidian_vaults").update_one(
        {"user_email": user_email},
        {"$set": {"user_email": user_email, **summary}},
        upsert=True,
    )
    return summary


async def get_vault_summary(user_email: str) -> dict[str, Any] | None:
    if not user_email:
        return None
    return await collection("obsidian_vaults").find_one({"user_email": user_email}, {"_id": 0})


async def delete_vault(user_email: str) -> None:
    await collection("obsidian_notes").delete_many({"user_email": user_email})
    await collection("obsidian_vaults").delete_one({"user_email": user_email})
