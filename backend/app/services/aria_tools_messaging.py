"""Aria tools for Twilio (SMS) and Telegram (bot messages).

Both share a "messaging connector" pattern: user pastes credentials into the
Connectors hub, we store on `user_profiles.connectors.<provider>.{config}`,
Aria can send a message (gated by per-action approval) and list recent
inbound messages from a `messaging_inbox` MongoDB collection.

For Sprint 3 MVP we ship OUTBOUND only. Inbound webhooks (Twilio /sms,
Telegram /bot/<token>/setWebhook) are scaffolded but not wired to a public
endpoint — that needs a stable webhook URL which the user can configure
later when they're ready.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.db import collection

MAX_RESULT_BYTES = 16 * 1024


# ---- Twilio SMS -----------------------------------------------------------

async def _twilio_creds(user_email: str) -> dict[str, str] | None:
    if not user_email:
        return None
    profile = await collection("user_profiles").find_one(
        {"user_email": user_email}, {"_id": 0, "connectors": 1},
    ) or {}
    cfg = (profile.get("connectors") or {}).get("twilio") or {}
    sid = cfg.get("account_sid")
    auth = cfg.get("auth_token")
    from_n = cfg.get("from_number")
    if not (sid and auth and from_n):
        return None
    return {"account_sid": sid, "auth_token": auth, "from_number": from_n}


async def sms_send(user_email: str, to: str, body: str) -> str:
    """Send an SMS via Twilio. WRITE — gated through approval."""
    creds = await _twilio_creds(user_email)
    if not creds:
        return ("ERROR: Twilio not connected. Tell the user to paste Account SID + Auth Token + "
                "From-number in the Twilio connector card.")
    if not to or not body:
        return "ERROR: to + body required"
    url = f"https://api.twilio.com/2010-04-01/Accounts/{creds['account_sid']}/Messages.json"
    payload = {"To": to, "From": creds["from_number"], "Body": body[:1500]}
    try:
        async with httpx.AsyncClient(timeout=20) as http:
            resp = await http.post(
                url,
                data=payload,
                auth=(creds["account_sid"], creds["auth_token"]),
            )
    except httpx.RequestError as error:
        return f"ERROR: twilio network — {str(error)[:160]}"
    if resp.status_code >= 400:
        return f"ERROR: twilio HTTP {resp.status_code}: {(resp.text or '')[:200]}"
    body_resp = resp.json()
    return f"SMS_SENT to {to} (sid={body_resp.get('sid','?')}): {body[:160]}"


async def sms_inbox_list(user_email: str, max_results: int = 20) -> str:
    """List recent inbound SMS (from `messaging_inbox`). Empty if no
    webhook configured yet — Sprint 3 MVP doesn't wire inbound."""
    if not user_email:
        return "ERROR: user_email required"
    rows = await collection("messaging_inbox").find(
        {"user_email": user_email, "provider": "twilio"},
        {"_id": 0},
    ).sort("received_at", -1).to_list(length=max(1, min(int(max_results or 20), 50)))
    if not rows:
        return "SMS_INBOX — empty (or webhook not configured yet)."
    lines = [f"SMS_INBOX — {len(rows)} message(s):"]
    for row in rows:
        lines.append(f"  - {row.get('received_at','?')[:19]} | from={row.get('from','?')} | {(row.get('body','') or '')[:160]}")
    return "\n".join(lines)


# ---- Telegram bot ---------------------------------------------------------

async def _telegram_token(user_email: str) -> str | None:
    if not user_email:
        return None
    profile = await collection("user_profiles").find_one(
        {"user_email": user_email}, {"_id": 0, "connectors": 1},
    ) or {}
    return ((profile.get("connectors") or {}).get("telegram") or {}).get("bot_token") or None


async def telegram_send_message(user_email: str, chat_id: str, text: str) -> str:
    """Send a Telegram message via the user's bot. WRITE — gated."""
    token = await _telegram_token(user_email)
    if not token:
        return "ERROR: Telegram not connected. Tell the user to paste their Telegram bot token (from @BotFather)."
    if not chat_id or not text:
        return "ERROR: chat_id + text required"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=20) as http:
            resp = await http.post(url, json={"chat_id": chat_id, "text": text[:3500]})
    except httpx.RequestError as error:
        return f"ERROR: telegram network — {str(error)[:160]}"
    body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    if not body.get("ok"):
        return f"ERROR: telegram — {(body.get('description') or resp.text)[:200]}"
    return f"TELEGRAM_SENT to chat={chat_id} (msg_id={body.get('result',{}).get('message_id','?')}): {text[:160]}"


async def telegram_inbox_list(user_email: str, max_results: int = 20) -> str:
    """Recent inbound messages from `messaging_inbox` (provider=telegram).
    Empty if webhook isn't pointed at this app yet (Sprint 3 MVP)."""
    if not user_email:
        return "ERROR: user_email required"
    rows = await collection("messaging_inbox").find(
        {"user_email": user_email, "provider": "telegram"},
        {"_id": 0},
    ).sort("received_at", -1).to_list(length=max(1, min(int(max_results or 20), 50)))
    if not rows:
        return "TELEGRAM_INBOX — empty (or webhook not configured yet)."
    lines = [f"TELEGRAM_INBOX — {len(rows)} message(s):"]
    for row in rows:
        lines.append(f"  - {row.get('received_at','?')[:19]} | from={row.get('from','?')} | {(row.get('body','') or '')[:160]}")
    return "\n".join(lines)


# ---- Dispatch -------------------------------------------------------------

MESSAGING_TOOL_DISPATCH = {
    "sms_send": sms_send,
    "sms_inbox_list": sms_inbox_list,
    "telegram_send_message": telegram_send_message,
    "telegram_inbox_list": telegram_inbox_list,
}
MESSAGING_WRITE_TOOLS = {"sms_send", "telegram_send_message"}


async def run_messaging_tool(name: str, user_email: str, args: dict) -> str:
    fn = MESSAGING_TOOL_DISPATCH.get(name)
    if not fn:
        return f"ERROR: unknown messaging tool '{name}'"
    int_keys = {"max_results"}
    cleaned: dict = {}
    for k, v in (args or {}).items():
        cleaned[k] = int(v) if k in int_keys else v
    try:
        return await fn(user_email=user_email, **cleaned)
    except TypeError as te:
        return f"ERROR: messaging tool '{name}' bad args — {str(te)[:200]}"


MESSAGING_TOOL_PROMPT = """
[MESSAGING TOOLS — available because the user has connected SMS / Telegram]

  • sms_send             to=+15551234567 body="..."  (REQUIRES USER APPROVAL)
  • sms_inbox_list       max_results=20
  • telegram_send_message chat_id=12345 text="..."  (REQUIRES USER APPROVAL)
  • telegram_inbox_list   max_results=20

Write tools will trigger an approval prompt before firing.
""".strip()
