"""Aria tools for Slack (bot-token based, simpler than per-user OAuth).

The user pastes a bot token (xoxb-…) into the Connectors hub. We store it
in `user_profiles.connectors.slack.token` (same shape as the GitHub PAT).
Aria uses it to list channels, search messages, and post messages.

Write actions (post_message) are flagged `requires_approval=True` so
chat_pipeline can route them through the per-action approval gate before
firing.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.db import collection

SLACK_API_BASE = "https://slack.com/api"
MAX_LIST = 30
MAX_RESULT_BYTES = 32 * 1024


async def _get_token(user_email: str) -> str | None:
    if not user_email:
        return None
    profile = await collection("user_profiles").find_one(
        {"user_email": user_email}, {"_id": 0, "connectors": 1},
    ) or {}
    return ((profile.get("connectors") or {}).get("slack") or {}).get("token") or None


def _trim(text: str) -> str:
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= MAX_RESULT_BYTES:
        return text
    return encoded[:MAX_RESULT_BYTES].decode("utf-8", errors="replace") + "\n[truncated]"


async def _slack_call(token: str, method: str, params: dict[str, Any], post: bool = False) -> dict[str, Any]:
    """Single authenticated call to the Slack Web API."""
    url = f"{SLACK_API_BASE}/{method}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient(timeout=20) as http:
            if post:
                resp = await http.post(url, headers={**headers, "Content-Type": "application/json; charset=utf-8"}, json=params)
            else:
                resp = await http.get(url, headers=headers, params=params)
    except httpx.RequestError as error:
        return {"ok": False, "error": f"network: {str(error)[:120]}"}
    try:
        body = resp.json()
    except Exception:
        return {"ok": False, "error": f"HTTP {resp.status_code} non-json"}
    return body


async def slack_list_channels(user_email: str, max_results: int = 20) -> str:
    token = await _get_token(user_email)
    if not token:
        return "ERROR: Slack not connected. Tell the user to paste their xoxb- bot token in the Slack connector card."
    body = await _slack_call(
        token, "conversations.list",
        {"types": "public_channel", "limit": max(1, min(int(max_results or 20), MAX_LIST)), "exclude_archived": "true"},
    )
    if not body.get("ok"):
        return f"ERROR: slack_list_channels — {body.get('error', '?')}"
    chans = body.get("channels", []) or []
    if not chans:
        return "SLACK_CHANNELS — none visible to the bot. Has the bot been invited?"
    lines = [f"SLACK_CHANNELS — {len(chans)} channel(s):"]
    for ch in chans:
        lines.append(
            f"  - id={ch.get('id')} | #{ch.get('name','?')[:40]} | members={ch.get('num_members','?')} | "
            f"topic={(ch.get('topic',{}) or {}).get('value','')[:60]}"
        )
    return "\n".join(lines)


async def slack_search_messages(user_email: str, query: str, max_results: int = 10) -> str:
    """NOTE: search.messages requires a USER token (xoxp-), not a bot token.
    Most users will only have xoxb- so this returns a clean hint.
    """
    token = await _get_token(user_email)
    if not token:
        return "ERROR: Slack not connected."
    if not (query or "").strip():
        return "ERROR: query required"
    if token.startswith("xoxb-"):
        return ("ERROR: slack_search_messages needs a USER token (xoxp-…). Bot tokens cannot search. "
                "Ask the user to swap to a user token, or use slack_list_channels + read individual channels instead.")
    body = await _slack_call(token, "search.messages", {"query": query, "count": max(1, min(int(max_results or 10), MAX_LIST))})
    if not body.get("ok"):
        return f"ERROR: slack_search_messages — {body.get('error', '?')}"
    matches = ((body.get("messages") or {}).get("matches") or [])
    if not matches:
        return f"SLACK_SEARCH q={query!r} — no matches."
    lines = [f"SLACK_SEARCH q={query!r} — {len(matches)} hit(s):"]
    for m in matches:
        ch = (m.get("channel") or {}).get("name") or "?"
        text = (m.get("text") or "").replace("\n", " ")[:160]
        lines.append(f"  - #{ch[:30]} | user={m.get('username','?')[:24]} | {text}")
    return _trim("\n".join(lines))


async def slack_post_message(user_email: str, channel: str, text: str) -> str:
    """Write action — chat_pipeline gates this through the approval UI."""
    token = await _get_token(user_email)
    if not token:
        return "ERROR: Slack not connected."
    if not channel or not text:
        return "ERROR: channel + text required"
    body = await _slack_call(
        token, "chat.postMessage", {"channel": channel, "text": text}, post=True,
    )
    if not body.get("ok"):
        return f"ERROR: slack_post_message — {body.get('error', '?')}"
    return f"SLACK_POSTED to {channel} (ts={body.get('ts','?')}): {text[:160]}"


SLACK_TOOL_DISPATCH = {
    "slack_list_channels": slack_list_channels,
    "slack_search_messages": slack_search_messages,
    "slack_post_message": slack_post_message,
}
SLACK_WRITE_TOOLS = {"slack_post_message"}


async def run_slack_tool(name: str, user_email: str, args: dict) -> str:
    fn = SLACK_TOOL_DISPATCH.get(name)
    if not fn:
        return f"ERROR: unknown slack tool '{name}'"
    int_keys = {"max_results"}
    cleaned: dict = {}
    for k, v in (args or {}).items():
        cleaned[k] = int(v) if k in int_keys else v
    try:
        return await fn(user_email=user_email, **cleaned)
    except TypeError as te:
        return f"ERROR: slack tool '{name}' bad args — {str(te)[:200]}"


SLACK_TOOL_PROMPT = """
[SLACK TOOLS — available because the user has connected Slack]

  • slack_list_channels  max_results=20
  • slack_search_messages query="incident" max_results=10  (needs xoxp- user token)
  • slack_post_message   channel=C0123456 text="Standup at 10"  (REQUIRES USER APPROVAL)

slack_post_message will trigger an approval prompt to the user before firing.
Other tools are read-only.
""".strip()
