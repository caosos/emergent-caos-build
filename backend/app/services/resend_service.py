"""Resend email connector — transactional email sending for CAOS.

Gracefully degrades when RESEND_API_KEY is not set: logs a warning and returns
False instead of raising, so the rest of the app keeps working when a user
hasn't configured the connector yet.
"""
from __future__ import annotations

import asyncio
import logging
import os

import resend

logger = logging.getLogger(__name__)

DEFAULT_SENDER = os.environ.get("SENDER_EMAIL") or "CAOS Care <onboarding@resend.dev>"


def _configure_client() -> bool:
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    if not api_key:
        return False
    resend.api_key = api_key
    return True


async def send_email(
    *,
    to: str | list[str],
    subject: str,
    html: str,
    from_addr: str | None = None,
    reply_to: str | None = None,
) -> dict | None:
    """Send a transactional email via Resend. Returns the Resend response
    dict (with an `id`) on success; returns None if RESEND_API_KEY is not set
    or if the call fails (error is logged and swallowed)."""
    if not _configure_client():
        logger.info("send_email skipped: RESEND_API_KEY is not configured")
        return None
    recipients = [to] if isinstance(to, str) else list(to)
    if not recipients:
        return None
    params: dict = {
        "from": from_addr or DEFAULT_SENDER,
        "to": recipients,
        "subject": subject,
        "html": html,
    }
    if reply_to:
        params["reply_to"] = [reply_to]
    try:
        response = await asyncio.to_thread(resend.Emails.send, params)
        return response
    except Exception as error:
        logger.warning("resend send failed: %s", error)
        # Surface to the error_log collection for Admin visibility.
        try:
            from app.services.error_logger import log_error
            await log_error(source="resend", error=error, context={"subject": subject[:120]})
        except Exception:  # pragma: no cover
            pass
        return None


def render_ticket_created(*, ticket_id: str, title: str, body: str, user_email: str, status: str) -> str:
    """Minimal inline-CSS HTML template — email-client safe (tables, inline styles)."""
    safe_body = (body or "").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
    return f"""
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:24px;font-family:-apple-system,Segoe UI,Helvetica,sans-serif;color:#e2e8f0;">
  <tr><td>
    <table width="560" cellpadding="0" cellspacing="0" align="center" style="background:#1e293b;border-radius:12px;border:1px solid #334155;">
      <tr><td style="padding:28px 28px 12px 28px;">
        <div style="font-size:12px;letter-spacing:0.08em;color:#a78bfa;text-transform:uppercase;margin-bottom:6px;">CAOS CARE · ticket</div>
        <div style="font-size:20px;font-weight:700;color:#f8fafc;">{title}</div>
        <div style="font-size:12px;color:#64748b;margin-top:4px;">ID: <code style="color:#94a3b8;">{ticket_id}</code> · status: <b>{status}</b></div>
      </td></tr>
      <tr><td style="padding:8px 28px 24px 28px;font-size:14px;line-height:1.55;color:#cbd5e1;">
        {safe_body}
      </td></tr>
      <tr><td style="padding:16px 28px 28px 28px;border-top:1px solid #334155;font-size:12px;color:#64748b;">
        You can reply in the CAOS Care panel inside the app.<br>
        <span style="color:#475569;">Submitted by {user_email}</span>
      </td></tr>
    </table>
  </td></tr>
</table>
""".strip()
