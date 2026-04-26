"""Aria diagnostic & DB-read tools — gives her actual measurement eyes on the
system instead of having to guess from code-reading.

Every tool is scoped to the calling user's `user_email` so Aria can NEVER read
another user's data. Read-only except `write_file`, which is sandboxed to the
user's CAOS Files (object storage / user_files row + extension allowlist + 256
KB cap + path-traversal guard).

Tools exposed:
  - query_receipts     → recent receipts with step_timings, tool timings, latency
  - profile_session    → auto-summary across last N receipts (slowest phase, p95, etc.)
  - query_messages     → last N message records for a session (trimmed)
  - query_files        → user_files attached to a session
  - query_memory_atoms → 13-bin memory atoms
  - query_engine_usage → cost / latency rollup
  - query_tickets      → user's support tickets
  - write_file         → save a file to user's CAOS Files
"""
from __future__ import annotations

import json
import re
import statistics
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.db import collection

# ---------- safety ----------

_FILENAME_RX = re.compile(r"^[A-Za-z0-9_\-. ]{1,120}$")
_ALLOWED_EXTENSIONS = {
    ".md", ".txt", ".json", ".csv", ".py", ".js", ".ts", ".html",
    ".yaml", ".yml", ".log", ".sql",
}
_MAX_WRITE_BYTES = 256 * 1024
_MAX_DB_LIMIT = 50

_MIME_BY_EXT = {
    ".md": "text/markdown", ".txt": "text/plain", ".json": "application/json",
    ".csv": "text/csv", ".py": "text/x-python", ".js": "application/javascript",
    ".ts": "application/typescript", ".html": "text/html",
    ".yaml": "text/yaml", ".yml": "text/yaml", ".log": "text/plain",
    ".sql": "application/sql",
}


def _clamp_limit(raw: str | int | None, default: int = 20) -> int:
    try:
        n = int(raw) if raw is not None else default
    except (TypeError, ValueError):
        n = default
    return max(1, min(_MAX_DB_LIMIT, n))


def _trim(value, max_chars: int = 400) -> str:
    if value is None:
        return ""
    s = str(value)
    if len(s) <= max_chars:
        return s
    return s[:max_chars] + f"... [{len(s) - max_chars} more chars]"


def _format_lines(items: list[dict]) -> str:
    """Compact JSONL-ish output — one record per line, easy for the LLM to scan."""
    if not items:
        return "(no records)"
    out = []
    for item in items:
        out.append(json.dumps(item, default=str, separators=(",", ":")))
    return "\n".join(out)


# ---------- query_receipts ----------

async def query_receipts(user_email: str, args: dict) -> str:
    """Pull recent receipts for a session. Returns step_timings, tool_step_timings,
    latency, tokens, and tools_used per turn — the actual measurement data Aria
    needs to diagnose latency without guessing.

    Args:
        session_id (required) — scope to one thread.
        limit (default 10, max 50) — how many recent receipts.
    """
    sid = args.get("session_id", "").strip()
    if not sid:
        return "ERROR: query_receipts requires session_id="
    # Verify the session belongs to this user — prevents cross-user reads.
    session = await collection("sessions").find_one(
        {"session_id": sid, "user_email": user_email}, {"_id": 0, "session_id": 1}
    )
    if not session:
        return f"ERROR: session_id={sid} not found for this user"
    limit = _clamp_limit(args.get("limit"), 10)
    rows = await collection("receipts").find(
        {"session_id": sid},
        {
            "_id": 0,
            "id": 1,
            "created_at": 1,
            "provider": 1,
            "model": 1,
            "latency_ms": 1,
            "step_timings": 1,
            "tool_iterations": 1,
            "tools_used": 1,
            "tool_step_timings": 1,
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "total_tokens": 1,
            "active_context_tokens": 1,
        },
    ).sort("created_at", -1).to_list(limit)
    return f"{len(rows)} receipts (most recent first):\n" + _format_lines(rows)


# ---------- profile_session ----------

async def profile_session(user_email: str, args: dict) -> str:
    """Auto-summary of latency across the last N receipts. One-shot diagnostic.
    Returns: per-phase mean & p95, slowest tool, tool histogram, total spend.
    """
    sid = args.get("session_id", "").strip()
    if not sid:
        return "ERROR: profile_session requires session_id="
    session = await collection("sessions").find_one(
        {"session_id": sid, "user_email": user_email}, {"_id": 0, "session_id": 1}
    )
    if not session:
        return f"ERROR: session_id={sid} not found for this user"
    limit = _clamp_limit(args.get("limit"), 20)
    rows = await collection("receipts").find(
        {"session_id": sid},
        {"_id": 0, "step_timings": 1, "latency_ms": 1, "tool_iterations": 1,
         "tools_used": 1, "tool_step_timings": 1, "total_tokens": 1, "created_at": 1},
    ).sort("created_at", -1).to_list(limit)
    if not rows:
        return f"(no receipts found for session {sid})"

    # Aggregate per-phase deltas (cumulative-ms → phase-ms).
    phase_order = ["setup", "fetch_history", "history_compress", "memory_rank",
                   "pre_llm_ready", "llm_done", "post_llm_compute", "handler_done"]
    phase_deltas: dict[str, list[int]] = {p: [] for p in phase_order}
    for r in rows:
        st = r.get("step_timings") or {}
        prev = 0
        for p in phase_order:
            cur = st.get(p)
            if cur is None:
                continue
            phase_deltas[p].append(max(0, cur - prev))
            prev = cur

    def _stats(values: list[int]) -> dict:
        if not values:
            return {"n": 0}
        return {
            "n": len(values),
            "mean": int(statistics.mean(values)),
            "p50": int(statistics.median(values)),
            "p95": int(sorted(values)[max(0, int(len(values) * 0.95) - 1)]),
            "max": max(values),
        }

    phase_summary = {p: _stats(phase_deltas[p]) for p in phase_order if phase_deltas[p]}

    # Tool histogram + slowest tool
    tool_counts: dict[str, int] = {}
    tool_exec: dict[str, list[int]] = {}
    tool_recall: dict[str, list[int]] = {}
    for r in rows:
        for t in r.get("tools_used") or []:
            tool_counts[t] = tool_counts.get(t, 0) + 1
        for step in r.get("tool_step_timings") or []:
            t = step.get("tool", "unknown")
            tool_exec.setdefault(t, []).append(step.get("tool_exec_ms", 0))
            tool_recall.setdefault(t, []).append(step.get("llm_recall_ms", 0))

    tool_breakdown = {}
    for t, execs in tool_exec.items():
        recalls = tool_recall.get(t, [])
        tool_breakdown[t] = {
            "calls": len(execs),
            "exec_avg_ms": int(statistics.mean(execs)) if execs else 0,
            "exec_max_ms": max(execs) if execs else 0,
            "llm_recall_avg_ms": int(statistics.mean(recalls)) if recalls else 0,
        }

    latencies = [r.get("latency_ms", 0) for r in rows if r.get("latency_ms") is not None]
    tokens = sum(r.get("total_tokens", 0) for r in rows)
    tool_iter_total = sum(r.get("tool_iterations", 0) for r in rows)

    summary = {
        "session_id": sid,
        "turns_analyzed": len(rows),
        "llm_latency_ms": _stats(latencies),
        "phase_breakdown_ms": phase_summary,
        "tool_iterations_total": tool_iter_total,
        "tools_used_count": tool_counts,
        "tool_breakdown_ms": tool_breakdown,
        "total_tokens": tokens,
    }
    # Identify slowest phase by mean
    if phase_summary:
        worst = max(phase_summary.items(), key=lambda kv: kv[1].get("mean", 0))
        summary["slowest_phase"] = {"name": worst[0], **worst[1]}
    return json.dumps(summary, indent=2, default=str)


# ---------- query_messages ----------

async def query_messages(user_email: str, args: dict) -> str:
    sid = args.get("session_id", "").strip()
    if not sid:
        return "ERROR: query_messages requires session_id="
    session = await collection("sessions").find_one(
        {"session_id": sid, "user_email": user_email}, {"_id": 0, "session_id": 1}
    )
    if not session:
        return f"ERROR: session_id={sid} not found for this user"
    limit = _clamp_limit(args.get("limit"), 10)
    rows = await collection("messages").find(
        {"session_id": sid},
        {"_id": 0, "id": 1, "role": 1, "content": 1, "timestamp": 1,
         "inference_provider": 1, "latency_ms": 1, "tools_used": 1},
    ).sort("timestamp", -1).to_list(limit)
    rows.reverse()  # chronological for readability
    trimmed = [
        {**r, "content": _trim(r.get("content", ""), 600)}
        for r in rows
    ]
    return f"{len(trimmed)} messages (chronological):\n" + _format_lines(trimmed)


# ---------- query_files ----------

async def query_files(user_email: str, args: dict) -> str:
    sid = args.get("session_id", "").strip()
    query = {"user_email": user_email}
    if sid:
        query["session_id"] = sid
    limit = _clamp_limit(args.get("limit"), 30)
    rows = await collection("user_files").find(
        query,
        {"_id": 0, "id": 1, "name": 1, "mime_type": 1, "size": 1, "kind": 1,
         "session_id": 1, "created_at": 1, "extracted_text": 1},
    ).sort("created_at", -1).to_list(limit)
    out = []
    total_bytes = 0
    for r in rows:
        et = r.get("extracted_text") or ""
        out.append({
            **{k: v for k, v in r.items() if k != "extracted_text"},
            "extracted_text_chars": len(et),
        })
        total_bytes += r.get("size", 0)
    return f"{len(out)} files, total {total_bytes} bytes:\n" + _format_lines(out)


# ---------- query_memory_atoms ----------

async def query_memory_atoms(user_email: str, args: dict) -> str:
    bin_filter = args.get("bin", "").strip().lower()
    limit = _clamp_limit(args.get("limit"), 30)
    query = {"user_email": user_email}
    if bin_filter:
        query["bin"] = bin_filter
    rows = await collection("memory_atoms").find(
        query,
        {"_id": 0, "id": 1, "bin": 1, "subject": 1, "predicate": 1, "object": 1,
         "confidence": 1, "created_at": 1, "evidence_count": 1, "last_seen_at": 1},
    ).sort("last_seen_at", -1).to_list(limit)
    return f"{len(rows)} memory_atoms{f' in bin={bin_filter}' if bin_filter else ''}:\n" + _format_lines(rows)


# ---------- query_engine_usage ----------

async def query_engine_usage(user_email: str, args: dict) -> str:
    limit = _clamp_limit(args.get("limit"), 30)
    rows = await collection("engine_usage").find(
        {"user_email": user_email},
        {"_id": 0, "session_id": 1, "provider": 1, "model": 1, "prompt_tokens": 1,
         "completion_tokens": 1, "total_tokens": 1, "cost_usd": 1, "latency_ms": 1,
         "tools_used": 1, "created_at": 1},
    ).sort("created_at", -1).to_list(limit)
    if not rows:
        return "(no engine_usage records)"
    total_cost = round(sum(r.get("cost_usd", 0) or 0 for r in rows), 4)
    total_tokens = sum(r.get("total_tokens", 0) for r in rows)
    summary = {"records": len(rows), "total_cost_usd": total_cost, "total_tokens": total_tokens}
    return json.dumps(summary) + "\n" + _format_lines(rows)


# ---------- query_tickets ----------

async def query_tickets(user_email: str, args: dict) -> str:
    status = args.get("status", "").strip().lower()
    query = {"user_email": user_email}
    if status:
        query["status"] = status
    limit = _clamp_limit(args.get("limit"), 20)
    rows = await collection("support_tickets").find(
        query,
        {"_id": 0, "id": 1, "category": 1, "title": 1, "description": 1,
         "status": 1, "source": 1, "created_at": 1, "updated_at": 1},
    ).sort("created_at", -1).to_list(limit)
    trimmed = [{**r, "description": _trim(r.get("description", ""), 200)} for r in rows]
    return f"{len(trimmed)} tickets:\n" + _format_lines(trimmed)


# ---------- write_file ----------

async def write_file(user_email: str, session_id: str, args: dict) -> str:
    """Save a file to the user's CAOS Files. Sandboxed: extension allowlist,
    256 KB cap, path-traversal guard. Stores via object storage (or local
    fallback) and inserts a user_files row so it appears under Profile → Files.
    """
    name = (args.get("name") or "").strip()
    content = args.get("content") or ""
    if not name:
        return "ERROR: write_file requires name="
    if not content:
        return "ERROR: write_file requires content="
    # Validate filename
    if not _FILENAME_RX.match(name):
        return f"ERROR: filename '{name}' has invalid characters (allowed: A-Z, a-z, 0-9, _, -, ., space)"
    if "/" in name or "\\" in name or ".." in name:
        return f"ERROR: filename '{name}' must not contain path separators or '..'"
    ext = Path(name).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        return f"ERROR: extension '{ext}' not allowed. Permitted: {sorted(_ALLOWED_EXTENSIONS)}"
    if not user_email:
        return "ERROR: write_file requires authenticated user context"
    if not session_id:
        return "ERROR: write_file requires session_id context"
    # Cap content size
    raw = content.encode("utf-8")
    if len(raw) > _MAX_WRITE_BYTES:
        return f"ERROR: content too large ({len(raw)} bytes > {_MAX_WRITE_BYTES} cap)"

    file_id = str(uuid.uuid4())
    mime_type = _MIME_BY_EXT.get(ext, "application/octet-stream")
    # Resolve user_id from email (file_storage row needs both)
    user_doc = await collection("users").find_one({"email": user_email}, {"_id": 0, "user_id": 1})
    user_id = user_doc.get("user_id") if user_doc else f"user_email_{user_email}"

    # Persist via object storage when ready, else local fallback.
    from app.services.object_storage import is_storage_ready, put_object, build_path
    storage_path = build_path(user_id, name, file_id)
    storage_backend = "local_ephemeral"
    final_path = storage_path
    if is_storage_ready():
        try:
            result = put_object(storage_path, raw, mime_type)
            final_path = result.get("path", storage_path)
            storage_backend = "emergent_objstore"
        except Exception as exc:
            return f"ERROR: storage upload failed — {str(exc)[:120]}"
    else:
        # Local fallback — same pattern as file_storage.py
        from app.services.file_storage import LOCAL_FALLBACK_ROOT
        user_dir = LOCAL_FALLBACK_ROOT / user_id / session_id
        user_dir.mkdir(parents=True, exist_ok=True)
        stored = user_dir / f"{file_id}{ext}"
        stored.write_bytes(raw)
        final_path = str(stored)

    doc = {
        "id": file_id,
        "user_id": user_id,
        "user_email": user_email,
        "session_id": session_id,
        "name": name,
        "kind": "file",
        "mime_type": mime_type,
        "size": len(raw),
        "storage_path": final_path,
        "storage_backend": storage_backend,
        "extracted_text": content[:32 * 1024],  # already-text contents — searchable
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "aria_write_file",
    }
    await collection("user_files").insert_one(doc)
    return (
        f"WROTE: name={name} id={file_id} bytes={len(raw)} mime={mime_type} "
        f"backend={storage_backend} url=/api/caos/files/{file_id}/download "
        f"(visible in Profile → Files for this session)"
    )
