"""Aria tools for Obsidian vault search.

Read-only — Obsidian is a local-first system so write actions don't make
sense over the network. Aria can only search, read, and traverse links.
"""
from __future__ import annotations

import re

from app.db import collection

MAX_RESULT_CONTENT = 32 * 1024
MAX_LIST_RESULTS = 30


async def obsidian_search(user_email: str, query: str, max_results: int = 12) -> str:
    """Full-text search across note title + content + tags."""
    if not user_email:
        return "ERROR: user_email required"
    q = (query or "").strip()
    if not q:
        return "ERROR: query required"
    max_results = max(1, min(int(max_results or 12), MAX_LIST_RESULTS))
    rx = re.compile(re.escape(q), re.IGNORECASE)
    cursor = collection("obsidian_notes").find(
        {
            "user_email": user_email,
            "$or": [
                {"title": {"$regex": q, "$options": "i"}},
                {"content": {"$regex": q, "$options": "i"}},
                {"tags": {"$regex": q, "$options": "i"}},
            ],
        },
        {"_id": 0, "path": 1, "title": 1, "content": 1, "tags": 1},
    ).limit(max_results)
    rows = await cursor.to_list(length=max_results)
    if not rows:
        return f"OBSIDIAN_SEARCH q={q!r} — no matches."
    lines = [f"OBSIDIAN_SEARCH q={q!r} — {len(rows)} hit(s):"]
    for row in rows:
        excerpt = ""
        m = rx.search(row.get("content") or "")
        if m:
            start = max(0, m.start() - 60)
            end = min(len(row["content"]), m.end() + 90)
            excerpt = row["content"][start:end].replace("\n", " ").strip()
        tags = ", ".join((row.get("tags") or [])[:5]) or "-"
        lines.append(
            f"  - {row.get('path','?')} | title={row.get('title','?')[:80]} | tags={tags}\n"
            f"    excerpt: …{excerpt[:240]}…"
        )
    return "\n".join(lines)


async def obsidian_get_note(user_email: str, path: str) -> str:
    """Return the full content of a single note by vault-relative path."""
    if not user_email:
        return "ERROR: user_email required"
    if not path:
        return "ERROR: path required"
    row = await collection("obsidian_notes").find_one(
        {"user_email": user_email, "path": path}, {"_id": 0}
    )
    if not row:
        return f"OBSIDIAN_NOTE {path} — not found in vault."
    content = row.get("content", "")
    if len(content.encode("utf-8", errors="replace")) > MAX_RESULT_CONTENT:
        content = content.encode("utf-8")[:MAX_RESULT_CONTENT].decode("utf-8", errors="replace") + "\n\n[truncated]"
    tags = ", ".join(row.get("tags") or []) or "-"
    backlinks = ", ".join(row.get("backlinks") or []) or "-"
    return (
        f"OBSIDIAN_NOTE path={row['path']}\n"
        f"title: {row.get('title')}\n"
        f"tags: {tags}\n"
        f"backlinks ({len(row.get('backlinks') or [])}): {backlinks}\n"
        f"---\n{content}"
    )


async def obsidian_list_tags(user_email: str, max_results: int = 30) -> str:
    """List most-used tags + their note counts."""
    if not user_email:
        return "ERROR: user_email required"
    pipeline = [
        {"$match": {"user_email": user_email}},
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": max(1, min(int(max_results or 30), 100))},
    ]
    rows = await collection("obsidian_notes").aggregate(pipeline).to_list(length=200)
    if not rows:
        return "OBSIDIAN_TAGS — vault has no tags."
    lines = [f"OBSIDIAN_TAGS — top {len(rows)} tag(s):"]
    for row in rows:
        lines.append(f"  - #{row['_id']} ({row['count']} notes)")
    return "\n".join(lines)


async def obsidian_backlinks(user_email: str, title: str) -> str:
    """List all notes that wikilink to a given title."""
    if not user_email or not title:
        return "ERROR: user_email and title required"
    rows = await collection("obsidian_notes").find(
        {"user_email": user_email, "wikilinks": {"$regex": f"^{re.escape(title)}$", "$options": "i"}},
        {"_id": 0, "path": 1, "title": 1},
    ).to_list(length=50)
    if not rows:
        return f"OBSIDIAN_BACKLINKS to '{title}' — no inbound links."
    lines = [f"OBSIDIAN_BACKLINKS to '{title}' — {len(rows)} note(s):"]
    for row in rows:
        lines.append(f"  - {row.get('path','?')} | {row.get('title','?')[:80]}")
    return "\n".join(lines)


OBSIDIAN_TOOL_DISPATCH = {
    "obsidian_search": obsidian_search,
    "obsidian_get_note": obsidian_get_note,
    "obsidian_list_tags": obsidian_list_tags,
    "obsidian_backlinks": obsidian_backlinks,
}


async def run_obsidian_tool(name: str, user_email: str, args: dict) -> str:
    fn = OBSIDIAN_TOOL_DISPATCH.get(name)
    if not fn:
        return f"ERROR: unknown obsidian tool '{name}'"
    cleaned: dict = {}
    int_keys = {"max_results"}
    for k, v in (args or {}).items():
        cleaned[k] = int(v) if k in int_keys else v
    try:
        return await fn(user_email=user_email, **cleaned)
    except TypeError as te:
        return f"ERROR: obsidian tool '{name}' bad args — {str(te)[:200]}"


OBSIDIAN_TOOL_PROMPT = """
[OBSIDIAN TOOLS — available because the user has uploaded an Obsidian vault]

  • obsidian_search   query="some text" max_results=12
  • obsidian_get_note path="folder/note.md"
  • obsidian_list_tags max_results=30
  • obsidian_backlinks title="Note Title"

All read-only. Use these to answer questions about the user's notes.
""".strip()
