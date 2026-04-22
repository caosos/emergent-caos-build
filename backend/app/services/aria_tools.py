"""Aria tool layer — read-only codebase inspection with strict safety rails.

Exposed as tool markers in the chat pipeline. Aria emits something like
`[TOOL: read_file path=/app/backend/app/services/chat_pipeline.py]` and the
pipeline runs the tool, feeds the result back, and loops up to 3 times before
producing the final user-visible reply.

SAFETY RAILS (non-negotiable):
  - Path allowlist: /app/frontend/src, /app/backend/app, /app/memory
  - Filename denylist: .env*, *.pem, *.key, *.pfx, credentials*, secrets*,
    *.crt, id_rsa*, *.p12, token*, session_token*
  - 64 KB truncation per read (with explicit marker)
  - No write access. Ever.
  - Max 50 search matches per grep
  - Max depth 2 for list_directory
"""
from __future__ import annotations

import re
from pathlib import Path

MAX_BYTES = 64 * 1024
MAX_MATCHES = 50
MAX_DEPTH = 2

ALLOWED_ROOTS = [
    Path("/app/frontend/src").resolve(),
    Path("/app/backend/app").resolve(),
    Path("/app/memory").resolve(),
]

# Filename patterns (basename, case-insensitive) that must NEVER be read,
# even inside an allowed root.
DENYLIST_PATTERNS = [
    re.compile(r"^\.env($|\..*)", re.IGNORECASE),
    re.compile(r".*\.(pem|key|pfx|crt|p12)$", re.IGNORECASE),
    re.compile(r"^(credentials|secrets?|token|session_token).*", re.IGNORECASE),
    re.compile(r"^id_rsa.*", re.IGNORECASE),
]


def _is_under_allowlist(target: Path) -> bool:
    try:
        resolved = target.resolve()
    except Exception:
        return False
    return any(str(resolved).startswith(str(root) + "/") or str(resolved) == str(root) for root in ALLOWED_ROOTS)


def _is_denied_name(name: str) -> bool:
    return any(p.match(name) for p in DENYLIST_PATTERNS)


def safe_read_file(path: str) -> str:
    try:
        target = Path(path)
        if not target.is_absolute():
            return "ERROR: path must be absolute (e.g. /app/backend/app/...)"
        if not _is_under_allowlist(target):
            return f"ERROR: path outside allowlist. Allowed roots: {', '.join(str(r) for r in ALLOWED_ROOTS)}"
        if _is_denied_name(target.name):
            return f"ERROR: filename '{target.name}' matches secrets denylist — refusing to read"
        if not target.exists():
            return f"ERROR: file not found: {path}"
        if not target.is_file():
            return f"ERROR: not a file: {path}"
        data = target.read_bytes()
        total = len(data)
        truncated = False
        if total > MAX_BYTES:
            data = data[:MAX_BYTES]
            truncated = True
        text = data.decode("utf-8", errors="replace")
        suffix = f"\n\n[truncated — showing first {MAX_BYTES} of {total} bytes]" if truncated else ""
        return f"FILE: {target.resolve()}\n---\n{text}{suffix}"
    except Exception as error:
        return f"ERROR: read failed — {str(error)[:160]}"


def list_dir(path: str) -> str:
    try:
        target = Path(path)
        if not target.is_absolute():
            return "ERROR: path must be absolute"
        if not _is_under_allowlist(target):
            return "ERROR: path outside allowlist"
        if not target.exists() or not target.is_dir():
            return f"ERROR: not a directory: {path}"
        lines: list[str] = [str(target.resolve())]

        def walk(current: Path, depth: int, prefix: str) -> None:
            if depth > MAX_DEPTH:
                return
            try:
                entries = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            except PermissionError:
                lines.append(f"{prefix}[permission denied]")
                return
            for i, entry in enumerate(entries):
                if entry.name.startswith(".") and entry.name not in {".emergent"}:
                    continue
                last = i == len(entries) - 1
                connector = "└── " if last else "├── "
                lines.append(f"{prefix}{connector}{entry.name}{'/' if entry.is_dir() else ''}")
                if entry.is_dir() and depth < MAX_DEPTH:
                    walk(entry, depth + 1, prefix + ("    " if last else "│   "))

        walk(target, 0, "")
        return "\n".join(lines[:400])
    except Exception as error:
        return f"ERROR: list failed — {str(error)[:160]}"


def grep_code(pattern: str, path: str = "/app/backend/app", glob: str = "*.py") -> str:
    try:
        target = Path(path)
        if not target.is_absolute():
            return "ERROR: path must be absolute"
        if not _is_under_allowlist(target):
            return "ERROR: path outside allowlist"
        try:
            rx = re.compile(pattern, re.IGNORECASE)
        except re.error as bad:
            return f"ERROR: bad regex — {bad}"
        matches: list[str] = []
        for file_path in target.rglob(glob):
            if not file_path.is_file() or _is_denied_name(file_path.name):
                continue
            if not _is_under_allowlist(file_path):
                continue
            try:
                with file_path.open("r", encoding="utf-8", errors="replace") as fh:
                    for line_num, line in enumerate(fh, 1):
                        if rx.search(line):
                            matches.append(f"{file_path}:{line_num}: {line.strip()[:240]}")
                            if len(matches) >= MAX_MATCHES:
                                break
            except Exception:
                continue
            if len(matches) >= MAX_MATCHES:
                break
        if not matches:
            return f"No matches for /{pattern}/ in {path} (glob {glob})"
        header = f"{len(matches)} match{'' if len(matches) == 1 else 'es'} for /{pattern}/:"
        return header + "\n" + "\n".join(matches)
    except Exception as error:
        return f"ERROR: grep failed — {str(error)[:160]}"


# ---- Marker parser -----------------------------------------------------------
_TOOL_RX = re.compile(r"\[TOOL:\s*(read_file|list_dir|grep_code)\s+(.*?)\]", re.DOTALL)
_KV_RX = re.compile(r"(\w+)\s*=\s*\"?([^\"\n]+?)\"?(?:\s+(?=\w+=)|$)")


def _parse_args(body: str) -> dict:
    args: dict = {}
    for m in _KV_RX.finditer(body.strip()):
        args[m.group(1).lower()] = m.group(2).strip()
    return args


def extract_and_run_next_tool(text: str) -> tuple[str | None, str | None]:
    """Find the FIRST tool marker in `text`, run it, return (marker, result).

    Returns (None, None) if no marker found.
    """
    match = _TOOL_RX.search(text)
    if not match:
        return None, None
    tool = match.group(1)
    body = match.group(2)
    args = _parse_args(body)
    try:
        if tool == "read_file":
            result = safe_read_file(args.get("path", ""))
        elif tool == "list_dir":
            result = list_dir(args.get("path", ""))
        elif tool == "grep_code":
            result = grep_code(
                pattern=args.get("pattern", ""),
                path=args.get("path", "/app/backend/app"),
                glob=args.get("glob", "*.py"),
            )
        else:
            result = f"ERROR: unknown tool '{tool}'"
    except Exception as error:
        result = f"ERROR: tool crashed — {str(error)[:160]}"
    return match.group(0), result
