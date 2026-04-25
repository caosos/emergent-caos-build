"""Aria tools for Google Workspace (Gmail, Drive, Docs, Calendar).

Each tool returns a human-readable string that gets fed back into Aria's
context window. Long content is truncated and clearly marked.

These tools are dispatched by `aria_tools.extract_and_run_next_tool` when the
user has connected their Google account. If the user is NOT connected, the
tool returns a clean error string telling Aria to ask the user to connect.

SAFETY:
- All tools are READ-ONLY for Sprint 1. Write actions (gmail send, calendar
  create) come in Sprint 3 with explicit per-action user approval gates.
- Raw token bytes never leave the token_vault module.
- 64KB content cap per call to keep context window healthy.

REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS,
THIS BREAKS THE AUTH.
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.google_client import GoogleAuthError, build_service

MAX_CONTENT_BYTES = 64 * 1024
MAX_LIST_RESULTS = 20

_NOT_CONNECTED = (
    "ERROR: Google not connected. Tell the user to open Settings → Connectors "
    "and click Connect on the Google card."
)


def _fmt_auth_error(error: GoogleAuthError) -> str:
    return f"ERROR: Google auth — {str(error)[:200]}"


def _decode_gmail_body(part: dict[str, Any]) -> str:
    """Best-effort decode of a Gmail message part.body.data (urlsafe-base64)."""
    body = part.get("body", {}) or {}
    data = body.get("data")
    if not data:
        # Walk multipart subparts
        out: list[str] = []
        for sub in part.get("parts", []) or []:
            piece = _decode_gmail_body(sub)
            if piece:
                out.append(piece)
        return "\n".join(out)
    try:
        raw = base64.urlsafe_b64decode(data + "=" * (4 - len(data) % 4))
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _truncate(text: str, label: str = "content") -> str:
    if not text:
        return ""
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= MAX_CONTENT_BYTES:
        return text
    cut = encoded[:MAX_CONTENT_BYTES].decode("utf-8", errors="replace")
    return f"{cut}\n\n[truncated {label} — first {MAX_CONTENT_BYTES} of {len(encoded)} bytes]"


# ---- Gmail -----------------------------------------------------------------

async def gmail_search(user_email: str, query: str = "is:unread", max_results: int = 10) -> str:
    """List Gmail messages matching `query` (Gmail search syntax).

    Examples: "from:billing@stripe.com newer_than:7d", "subject:invoice",
    "is:unread is:important". Returns up to MAX_LIST_RESULTS, each with
    sender, subject, snippet, and message id.
    """
    try:
        service = await build_service(user_email, "gmail", "v1")
        max_results = max(1, min(int(max_results or 10), MAX_LIST_RESULTS))
        listing = service.users().messages().list(
            userId="me", q=query or "", maxResults=max_results
        ).execute()
        messages = listing.get("messages", []) or []
        if not messages:
            return f"GMAIL_SEARCH q={query!r} — no results."

        lines: list[str] = [f"GMAIL_SEARCH q={query!r} — {len(messages)} hit(s):"]
        for msg in messages:
            try:
                full = service.users().messages().get(
                    userId="me", id=msg["id"], format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                ).execute()
            except Exception as get_err:
                lines.append(f"  - id={msg['id']} (fetch failed: {str(get_err)[:60]})")
                continue
            headers = {h["name"]: h["value"] for h in (full.get("payload", {}).get("headers") or [])}
            sender = headers.get("From", "?")
            subject = headers.get("Subject", "(no subject)")
            date = headers.get("Date", "?")
            snippet = (full.get("snippet") or "")[:200]
            lines.append(
                f"  - id={msg['id']} | from={sender[:60]} | date={date[:32]}\n"
                f"    subject: {subject[:120]}\n"
                f"    snippet: {snippet}"
            )
        return "\n".join(lines)
    except GoogleAuthError as auth:
        return _fmt_auth_error(auth)
    except Exception as error:
        return f"ERROR: gmail_search failed — {str(error)[:200]}"


async def gmail_get_message(user_email: str, message_id: str) -> str:
    """Fetch the full body + headers of a single Gmail message by id."""
    try:
        if not message_id:
            return "ERROR: message_id required"
        service = await build_service(user_email, "gmail", "v1")
        full = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        headers = {h["name"]: h["value"] for h in (full.get("payload", {}).get("headers") or [])}
        body = _decode_gmail_body(full.get("payload", {}))
        return _truncate(
            f"GMAIL_MESSAGE id={message_id}\n"
            f"from: {headers.get('From', '?')}\n"
            f"to: {headers.get('To', '?')}\n"
            f"date: {headers.get('Date', '?')}\n"
            f"subject: {headers.get('Subject', '(no subject)')}\n"
            f"---\n{body or full.get('snippet', '(no body)')}",
            label="email body",
        )
    except GoogleAuthError as auth:
        return _fmt_auth_error(auth)
    except Exception as error:
        return f"ERROR: gmail_get_message failed — {str(error)[:200]}"


# ---- Drive -----------------------------------------------------------------

async def drive_search(user_email: str, query: str, max_results: int = 10) -> str:
    """Search Drive files. `query` uses Drive search syntax.

    Common forms: "name contains 'budget'", "mimeType='application/vnd.google-apps.document'",
    "modifiedTime > '2026-01-01'". For a simple keyword search, pass
    `name contains 'KEYWORD' or fullText contains 'KEYWORD'`.
    """
    try:
        service = await build_service(user_email, "drive", "v3")
        max_results = max(1, min(int(max_results or 10), MAX_LIST_RESULTS))
        # If user passed a bare keyword, sugar it into a fullText search.
        q = query.strip()
        if q and "'" not in q and " " not in q and ":" not in q:
            q = f"fullText contains '{q}'"
        listing = service.files().list(
            q=q or None, pageSize=max_results,
            fields="files(id,name,mimeType,modifiedTime,owners(emailAddress),size,webViewLink)",
        ).execute()
        files = listing.get("files", []) or []
        if not files:
            return f"DRIVE_SEARCH q={query!r} — no files."
        lines = [f"DRIVE_SEARCH q={query!r} — {len(files)} file(s):"]
        for f in files:
            owner = ((f.get("owners") or [{}])[0] or {}).get("emailAddress", "?")
            lines.append(
                f"  - id={f.get('id')} | mime={f.get('mimeType','?')[:50]} | "
                f"name={f.get('name','?')[:80]} | owner={owner[:40]} | "
                f"modified={f.get('modifiedTime','?')[:19]}"
            )
        return "\n".join(lines)
    except GoogleAuthError as auth:
        return _fmt_auth_error(auth)
    except Exception as error:
        return f"ERROR: drive_search failed — {str(error)[:200]}"


async def drive_read_file(user_email: str, file_id: str) -> str:
    """Read text content of a Drive file by id.

    Native Google formats (Docs, Sheets, Slides) are exported to plain text.
    Raw text files are downloaded directly. Binary files (images, PDFs) are
    refused with a hint; user should ask Aria to use docs_get_document for
    Google Docs specifically.
    """
    try:
        if not file_id:
            return "ERROR: file_id required"
        service = await build_service(user_email, "drive", "v3")
        meta = service.files().get(fileId=file_id, fields="id,name,mimeType,size").execute()
        mime = meta.get("mimeType", "")
        name = meta.get("name", "?")

        # Native Google formats need export
        export_map = {
            "application/vnd.google-apps.document": "text/plain",
            "application/vnd.google-apps.spreadsheet": "text/csv",
            "application/vnd.google-apps.presentation": "text/plain",
        }
        if mime in export_map:
            data = service.files().export_media(fileId=file_id, mimeType=export_map[mime]).execute()
            text = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)
        elif mime.startswith("text/") or mime == "application/json":
            data = service.files().get_media(fileId=file_id).execute()
            text = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)
        else:
            return f"DRIVE_READ id={file_id} name={name} mime={mime} — refused: binary file. Ask user to share a Doc/Sheet/Slide or text file."

        return _truncate(
            f"DRIVE_FILE id={file_id} name={name} mime={mime}\n---\n{text}",
            label="file content",
        )
    except GoogleAuthError as auth:
        return _fmt_auth_error(auth)
    except Exception as error:
        return f"ERROR: drive_read_file failed — {str(error)[:200]}"


# ---- Docs ------------------------------------------------------------------

async def docs_get_document(user_email: str, document_id: str) -> str:
    """Fetch a Google Doc as structured text (preserves headings + paragraphs)."""
    try:
        if not document_id:
            return "ERROR: document_id required"
        service = await build_service(user_email, "docs", "v1")
        doc = service.documents().get(documentId=document_id).execute()
        title = doc.get("title", "(untitled)")
        body = doc.get("body", {}).get("content", []) or []

        out_lines: list[str] = [f"GOOGLE_DOC id={document_id} title={title}"]
        for el in body:
            para = el.get("paragraph")
            if not para:
                continue
            text_runs = [
                (run.get("textRun") or {}).get("content", "")
                for run in (para.get("elements") or [])
            ]
            line = "".join(text_runs).rstrip("\n")
            if not line.strip():
                continue
            style = (para.get("paragraphStyle") or {}).get("namedStyleType", "")
            if style == "TITLE":
                out_lines.append(f"\n# {line}")
            elif style.startswith("HEADING_"):
                level = "#" * (int(style.split("_")[-1]) if style.split("_")[-1].isdigit() else 2)
                out_lines.append(f"\n{level} {line}")
            else:
                out_lines.append(line)
        return _truncate("\n".join(out_lines), label="doc body")
    except GoogleAuthError as auth:
        return _fmt_auth_error(auth)
    except Exception as error:
        return f"ERROR: docs_get_document failed — {str(error)[:200]}"


# ---- Calendar --------------------------------------------------------------

async def calendar_list_events(
    user_email: str,
    days_ahead: int = 7,
    max_results: int = 20,
) -> str:
    """List events in the user's primary calendar from now to N days ahead."""
    try:
        service = await build_service(user_email, "calendar", "v3")
        days = max(1, min(int(days_ahead or 7), 60))
        now = datetime.now(timezone.utc)
        time_min = now.isoformat()
        time_max = (now + timedelta(days=days)).isoformat()
        events = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max(1, min(int(max_results or 20), MAX_LIST_RESULTS)),
            singleEvents=True,
            orderBy="startTime",
        ).execute().get("items", []) or []
        if not events:
            return f"CALENDAR_EVENTS next {days}d — none."
        lines = [f"CALENDAR_EVENTS next {days}d — {len(events)} event(s):"]
        for ev in events:
            start = (ev.get("start") or {}).get("dateTime") or (ev.get("start") or {}).get("date") or "?"
            end = (ev.get("end") or {}).get("dateTime") or (ev.get("end") or {}).get("date") or "?"
            summary = ev.get("summary", "(no title)")
            attendees = [a.get("email", "?") for a in (ev.get("attendees") or [])][:5]
            attendees_str = ", ".join(attendees) if attendees else "(solo)"
            lines.append(
                f"  - {start} → {end} | {summary[:80]}\n    attendees: {attendees_str}"
            )
        return "\n".join(lines)
    except GoogleAuthError as auth:
        return _fmt_auth_error(auth)
    except Exception as error:
        return f"ERROR: calendar_list_events failed — {str(error)[:200]}"


async def calendar_freebusy(
    user_email: str,
    days_ahead: int = 7,
    work_start_hour: int = 9,
    work_end_hour: int = 17,
) -> str:
    """Return work-hour gaps over the next N days as a free-time summary."""
    try:
        service = await build_service(user_email, "calendar", "v3")
        days = max(1, min(int(days_ahead or 7), 14))
        now = datetime.now(timezone.utc)
        time_min = now.isoformat()
        time_max = (now + timedelta(days=days)).isoformat()
        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": "primary"}],
        }
        result = service.freebusy().query(body=body).execute()
        busy = ((result.get("calendars") or {}).get("primary") or {}).get("busy", []) or []
        if not busy:
            return f"FREEBUSY next {days}d — completely free between {work_start_hour}:00–{work_end_hour}:00."
        lines = [
            f"FREEBUSY next {days}d — busy windows ({work_start_hour}:00–{work_end_hour}:00 work hours):"
        ]
        for window in busy[:30]:
            lines.append(f"  - {window.get('start', '?')[:19]} → {window.get('end', '?')[:19]}")
        return "\n".join(lines)
    except GoogleAuthError as auth:
        return _fmt_auth_error(auth)
    except Exception as error:
        return f"ERROR: calendar_freebusy failed — {str(error)[:200]}"


# ---- Dispatch table --------------------------------------------------------

GOOGLE_TOOL_DISPATCH = {
    "gmail_search": gmail_search,
    "gmail_get_message": gmail_get_message,
    "drive_search": drive_search,
    "drive_read_file": drive_read_file,
    "docs_get_document": docs_get_document,
    "calendar_list_events": calendar_list_events,
    "calendar_freebusy": calendar_freebusy,
}


async def run_google_tool(name: str, user_email: str, args: dict) -> str:
    """Dispatcher for Google tools. Returns the rendered string Aria sees."""
    fn = GOOGLE_TOOL_DISPATCH.get(name)
    if not fn:
        return f"ERROR: unknown google tool '{name}'"
    if not user_email:
        return _NOT_CONNECTED
    # Translate string args to ints where the tool expects them.
    int_keys = {"max_results", "days_ahead", "work_start_hour", "work_end_hour"}
    cleaned: dict[str, Any] = {}
    for k, v in args.items():
        if k in int_keys:
            try:
                cleaned[k] = int(v)
            except Exception:
                cleaned[k] = 0
        else:
            cleaned[k] = v
    try:
        return await fn(user_email=user_email, **cleaned)  # type: ignore[arg-type]
    except TypeError as te:
        return f"ERROR: google tool '{name}' bad args — {str(te)[:200]}"


# Aria-facing tool docs injected into the system prompt when the user is connected.
GOOGLE_TOOL_PROMPT = """
[GOOGLE TOOLS — available because the user has connected Google Workspace]

Call any of these by emitting `[TOOL: <name> arg=value arg2=value2]` on its own line.

  • gmail_search       query="is:unread newer_than:7d" max_results=10
  • gmail_get_message  message_id=<id from gmail_search>
  • drive_search       query="quarterly report" max_results=10
  • drive_read_file    file_id=<id from drive_search>
  • docs_get_document  document_id=<google doc id>
  • calendar_list_events days_ahead=7 max_results=20
  • calendar_freebusy    days_ahead=7

All read-only. If the result starts with ERROR, surface it to the user verbatim
in your reply — it usually means a connection issue, not a question of effort.
""".strip()
