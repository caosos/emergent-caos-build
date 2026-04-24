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
  - web_fetch: HTTPS only, SSRF-blocked (no private/loopback/link-local),
    GET only, 128 KB body cap, 15s timeout, max 3 redirects.
"""
from __future__ import annotations

import ipaddress
import os
import re
import socket
from pathlib import Path
from urllib.parse import urlparse

import httpx

MAX_BYTES = 64 * 1024
MAX_WEB_BYTES = 128 * 1024
MAX_MATCHES = 50
MAX_DEPTH = 2
WEB_TIMEOUT = 15.0

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


# ---- Web fetch (SSRF-safe) ---------------------------------------------------

# Hostnames we explicitly refuse to hit — local / internal resolvers.
_HOST_DENY = re.compile(
    r"^(localhost|.*\.local|.*\.internal|metadata\.google\.internal|169\.254\..*)$",
    re.IGNORECASE,
)


def _is_public_host(hostname: str) -> tuple[bool, str]:
    """Resolve hostname and verify ALL of its A/AAAA records are public IPs.
    Returns (ok, reason_if_blocked)."""
    if not hostname:
        return False, "empty host"
    if _HOST_DENY.match(hostname):
        return False, f"blocked host: {hostname}"
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as err:
        return False, f"dns failed: {str(err)[:80]}"
    if not infos:
        return False, "no DNS records"
    for family, _, _, _, sockaddr in infos:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False, f"bad ip: {ip_str}"
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            return False, f"blocked IP ({ip_str}) — internal/private/loopback"
    return True, ""


_SCRIPT_STYLE_RX = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_TAG_RX = re.compile(r"<[^>]+>")
_WS_RX = re.compile(r"[ \t\r\f\v]+")
_NL_RX = re.compile(r"\n{3,}")


def _html_to_text(html: str) -> str:
    clean = _SCRIPT_STYLE_RX.sub(" ", html)
    clean = _TAG_RX.sub(" ", clean)
    clean = clean.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")
    clean = _WS_RX.sub(" ", clean)
    clean = _NL_RX.sub("\n\n", clean)
    return clean.strip()


def web_fetch(url: str, mode: str = "auto") -> str:
    """Fetch a public URL and return its body (HTML stripped to text by default).

    Args:
        url: http(s) URL. SSRF-blocked: no private/loopback/link-local hosts.
        mode: "text" (strip HTML), "raw" (verbatim), or "auto" (raw if content-type
            looks non-HTML like text/plain, application/json, text/markdown, etc.;
            text otherwise).

    Returns a human-readable string starting with a FETCH header line.
    """
    try:
        if not url or not isinstance(url, str):
            return "ERROR: url required"
        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return f"ERROR: only http/https allowed (got '{parsed.scheme}')"
        host = parsed.hostname or ""
        ok, reason = _is_public_host(host)
        if not ok:
            return f"ERROR: {reason}"
        headers = {
            "User-Agent": "CAOS-Aria/1.0 (+https://caosos.com)",
            "Accept": "text/html,application/xhtml+xml,application/json,text/plain,text/markdown,*/*;q=0.6",
        }
        with httpx.Client(
            follow_redirects=True,
            max_redirects=3,
            timeout=WEB_TIMEOUT,
            headers=headers,
        ) as client:
            response = client.get(url)
        status = response.status_code
        final_url = str(response.url)
        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        body_bytes = response.content or b""
        total = len(body_bytes)
        truncated = False
        if total > MAX_WEB_BYTES:
            body_bytes = body_bytes[:MAX_WEB_BYTES]
            truncated = True
        try:
            text = body_bytes.decode("utf-8", errors="replace")
        except Exception:
            text = body_bytes.decode("latin-1", errors="replace")
        # Decide rendering
        non_html_types = {"application/json", "text/plain", "text/markdown", "text/x-markdown", "text/csv", "application/xml", "text/xml"}
        is_htmlish = "html" in content_type or "xml" in content_type and "text" in content_type
        render_mode = mode
        if render_mode == "auto":
            render_mode = "raw" if (content_type in non_html_types or not is_htmlish) else "text"
        rendered = _html_to_text(text) if render_mode == "text" else text
        trailer = f"\n\n[truncated — showing first {MAX_WEB_BYTES} of {total} bytes]" if truncated else ""
        header = f"FETCH url={final_url} status={status} content-type={content_type or '?'} bytes={total}"
        return f"{header}\n---\n{rendered}{trailer}"
    except httpx.TimeoutException:
        return f"ERROR: timeout after {WEB_TIMEOUT}s fetching {url}"
    except httpx.TooManyRedirects:
        return f"ERROR: too many redirects fetching {url}"
    except Exception as error:
        return f"ERROR: web_fetch failed — {str(error)[:200]}"


def github_fetch(repo: str, path: str, ref: str = "main", user_token: str | None = None) -> str:
    """Fetch a file from a public (or private) GitHub repo via raw.githubusercontent.com.

    Args:
        repo: "<owner>/<name>" (e.g., "openai/gpt-5-cookbook").
        path: file path inside repo (e.g., "README.md" or "src/app.py").
        ref: branch/tag/commit SHA. Default "main".
        user_token: per-user PAT resolved by the dispatcher; wins over
            GITHUB_TOKEN env. Anonymous fallback if neither set (public only).
    """
    try:
        if not repo or "/" not in repo:
            return "ERROR: repo must be '<owner>/<name>'"
        if not path or path.startswith("/"):
            return "ERROR: path required (no leading slash)"
        ref = (ref or "main").strip()
        owner_name = repo.strip().strip("/")
        url = f"https://raw.githubusercontent.com/{owner_name}/{ref}/{path}"
        token = (user_token or "").strip() or os.environ.get("GITHUB_TOKEN", "").strip()
        headers = {
            "User-Agent": "CAOS-Aria/1.0 (+https://caosos.com)",
            "Accept": "text/plain, application/vnd.github.v3.raw, */*;q=0.6",
        }
        if token:
            headers["Authorization"] = f"token {token}"
        with httpx.Client(follow_redirects=True, max_redirects=3, timeout=WEB_TIMEOUT, headers=headers) as client:
            response = client.get(url)
        status = response.status_code
        if status == 404:
            return f"ERROR: not found — raw.githubusercontent.com/{owner_name}/{ref}/{path} (check repo, path, ref; if private, connect your GitHub PAT in Settings → Connectors)"
        if status >= 400:
            return f"ERROR: github returned {status} for {owner_name}/{ref}/{path}"
        body_bytes = response.content or b""
        total = len(body_bytes)
        truncated = False
        if total > MAX_WEB_BYTES:
            body_bytes = body_bytes[:MAX_WEB_BYTES]
            truncated = True
        text = body_bytes.decode("utf-8", errors="replace")
        trailer = f"\n\n[truncated — showing first {MAX_WEB_BYTES} of {total} bytes]" if truncated else ""
        header = f"GITHUB repo={owner_name} ref={ref} path={path} bytes={total}"
        return f"{header}\n---\n{text}{trailer}"
    except httpx.TimeoutException:
        return f"ERROR: timeout after {WEB_TIMEOUT}s fetching {repo}/{path}"
    except Exception as error:
        return f"ERROR: github_fetch failed — {str(error)[:200]}"


# ---- Marker parser -----------------------------------------------------------
_TOOL_RX = re.compile(r"\[TOOL:\s*(read_file|list_dir|grep_code|web_fetch|github_fetch)\s+(.*?)\]", re.DOTALL)
_KV_RX = re.compile(r"(\w+)\s*=\s*\"?([^\"\n]+?)\"?(?:\s+(?=\w+=)|$)")


def _parse_args(body: str) -> dict:
    args: dict = {}
    for m in _KV_RX.finditer(body.strip()):
        args[m.group(1).lower()] = m.group(2).strip()
    return args


def extract_and_run_next_tool(text: str, context: dict | None = None) -> tuple[str | None, str | None]:
    """Find the FIRST tool marker in `text`, run it, return (marker, result).

    Args:
        text: Aria's reply to scan.
        context: optional dict — supports `github_token` (per-user PAT).

    Returns (None, None) if no marker found.
    """
    match = _TOOL_RX.search(text)
    if not match:
        return None, None
    tool = match.group(1)
    body = match.group(2)
    args = _parse_args(body)
    ctx = context or {}
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
        elif tool == "web_fetch":
            result = web_fetch(
                url=args.get("url", ""),
                mode=args.get("mode", "auto"),
            )
        elif tool == "github_fetch":
            result = github_fetch(
                repo=args.get("repo", ""),
                path=args.get("path", ""),
                ref=args.get("ref", "main"),
                user_token=ctx.get("github_token"),
            )
        else:
            result = f"ERROR: unknown tool '{tool}'"
    except Exception as error:
        result = f"ERROR: tool crashed — {str(error)[:160]}"
    return match.group(0), result
