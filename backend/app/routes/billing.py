"""Stripe billing — tier upgrades for the CAOS quota system.

Design (per the verified Stripe Checkout playbook)
==================================================
- ONE-TIME Checkout sessions only (not subscriptions). Each upgrade buys a
  30-day pass at a chosen tier; the pass adds days to the user's
  `user_profiles.tier_expires_at`. Users re-up monthly. No auto-recurring.
  This matches the playbook's `CheckoutSessionRequest` shape and avoids
  Stripe's subscription-management complexity for the MVP.
- Tier prices are SERVER-SIDE ONLY (`token_quota.TIERS`). The frontend
  sends a `tier_id` and the backend looks up the price. Frontend NEVER
  sends an amount.
- Success / cancel URLs are built from the `origin_url` the frontend sends
  (window.location.origin). Hardcoded URLs are a deployment trap.
- Every checkout creates a row in `payment_transactions` with status
  "initiated" before the redirect. On status poll (`/billing/status/<sid>`)
  we update to "paid" / "expired" / "cancelled" and grant the upgrade
  exactly once (idempotent on session_id).
- Webhook at `/api/webhook/stripe` mirrors the same idempotent grant —
  whichever fires first (poll or webhook) does the upgrade, the other is
  a no-op.

ENV
---
- `STRIPE_API_KEY=sk_test_emergent`  (already in pod env per system prompt)

REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS,
THIS BREAKS THE AUTH. Origin is supplied by the frontend.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.db import collection
from app.services.auth_service import require_user
from app.services.token_quota import TIERS

router = APIRouter(prefix="/billing", tags=["billing"])
log = logging.getLogger("caos.billing")

# 30-day pass per upgrade. If a user upgrades while still on a tier, days
# stack — they don't lose the unused portion.
PASS_DAYS = 30


def _stripe_checkout(host_url: str):
    """Build a StripeCheckout client with the webhook URL relative to host."""
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="server missing STRIPE_API_KEY")
    # Lazy import to keep cold-start light + only fail at first use, not boot.
    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    webhook_url = f"{host_url.rstrip('/')}/api/webhook/stripe"
    return StripeCheckout(api_key=api_key, webhook_url=webhook_url)


# ---- Schemas --------------------------------------------------------------

class CheckoutRequest(BaseModel):
    tier_id: str
    origin_url: str  # window.location.origin from the frontend


class CheckoutResponse(BaseModel):
    url: str
    session_id: str


class BillingStatusResponse(BaseModel):
    session_id: str
    status: str  # initiated | paid | expired | cancelled | already_processed
    payment_status: str
    amount_total: int
    currency: str
    tier_id: Optional[str] = None
    tier_expires_at: Optional[str] = None


# ---- Routes ---------------------------------------------------------------

@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest, request: Request, user: dict = Depends(require_user),
) -> CheckoutResponse:
    """Create a Stripe Checkout session for a tier upgrade.

    - Tier price comes from `token_quota.TIERS[tier_id]['price_monthly']`.
    - Free tier doesn't get a checkout.
    - One transaction row created per session before redirect.
    """
    tier_id = body.tier_id.strip().lower()
    tier = TIERS.get(tier_id)
    if not tier or "price_monthly" not in tier:
        raise HTTPException(status_code=400, detail=f"tier '{tier_id}' is not purchasable")
    if tier_id == "free":
        raise HTTPException(status_code=400, detail="free tier needs no checkout")

    origin = (body.origin_url or "").rstrip("/")
    if not origin.startswith("http"):
        raise HTTPException(status_code=400, detail="origin_url must be absolute URL")

    # Build a StripeCheckout client. host_url comes from the request itself
    # (FastAPI/Starlette resolves it from headers). This goes to the WEBHOOK,
    # not the user-facing redirect — that's `success_url` below.
    host_url = str(request.base_url).rstrip("/")
    stripe = _stripe_checkout(host_url)

    # Frontend-facing redirects. The `?session_id=...` macro is replaced by
    # Stripe at redirect time so the page can poll status.
    success_url = f"{origin}/?caos_billing=success&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/?caos_billing=cancel"
    metadata = {
        "user_email": user["email"],
        "tier_id": tier_id,
        "source": "caos_pricing_drawer",
    }
    from emergentintegrations.payments.stripe.checkout import CheckoutSessionRequest
    checkout_req = CheckoutSessionRequest(
        amount=float(tier["price_monthly"]),
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
    )
    session = await stripe.create_checkout_session(checkout_req)

    # Persist BEFORE redirect so the status poll can find this row.
    now_iso = datetime.now(timezone.utc).isoformat()
    await collection("payment_transactions").insert_one({
        "session_id": session.session_id,
        "user_email": user["email"],
        "tier_id": tier_id,
        "amount": float(tier["price_monthly"]),
        "currency": "usd",
        "status": "initiated",
        "payment_status": "unpaid",
        "metadata": metadata,
        "applied": False,  # idempotency flag for the upgrade grant
        "created_at": now_iso,
        "updated_at": now_iso,
    })
    return CheckoutResponse(url=session.url, session_id=session.session_id)


@router.get("/status/{session_id}", response_model=BillingStatusResponse)
async def checkout_status(
    session_id: str, request: Request, user: dict = Depends(require_user),
) -> BillingStatusResponse:
    """Poll Stripe for status. On first 'paid' read, grant the tier upgrade
    and mark applied=True so subsequent polls don't double-grant.
    """
    txn = await collection("payment_transactions").find_one(
        {"session_id": session_id}, {"_id": 0},
    )
    if not txn:
        raise HTTPException(status_code=404, detail="unknown session_id")
    if txn.get("user_email") != user["email"]:
        # User is checking someone else's session — refuse silently.
        raise HTTPException(status_code=403, detail="not your session")

    # If we've already finalized this txn, no need to call Stripe again.
    if txn.get("applied") is True:
        profile = await collection("user_profiles").find_one(
            {"user_email": user["email"]}, {"_id": 0, "tier": 1, "tier_expires_at": 1},
        ) or {}
        return BillingStatusResponse(
            session_id=session_id,
            status="already_processed",
            payment_status="paid",
            amount_total=int((txn.get("amount") or 0) * 100),
            currency=txn.get("currency", "usd"),
            tier_id=txn.get("tier_id"),
            tier_expires_at=profile.get("tier_expires_at"),
        )

    host_url = str(request.base_url).rstrip("/")
    stripe = _stripe_checkout(host_url)
    status_resp = await stripe.get_checkout_status(session_id)

    new_status = "initiated"
    if status_resp.payment_status == "paid":
        new_status = "paid"
    elif status_resp.status == "expired":
        new_status = "expired"
    elif status_resp.status == "complete" and status_resp.payment_status != "paid":
        new_status = "cancelled"

    update = {
        "status": new_status,
        "payment_status": status_resp.payment_status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await collection("payment_transactions").update_one(
        {"session_id": session_id}, {"$set": update},
    )

    expires_iso: Optional[str] = None
    if new_status == "paid":
        expires_iso = await _grant_tier_upgrade(user["email"], txn["tier_id"], session_id)

    return BillingStatusResponse(
        session_id=session_id,
        status=new_status,
        payment_status=status_resp.payment_status,
        amount_total=status_resp.amount_total,
        currency=status_resp.currency,
        tier_id=txn.get("tier_id"),
        tier_expires_at=expires_iso,
    )


@router.get("/me")
async def my_billing(user: dict = Depends(require_user)) -> dict:
    """Current tier + expiry for the AccountMenu badge."""
    profile = await collection("user_profiles").find_one(
        {"user_email": user["email"]}, {"_id": 0, "tier": 1, "tier_expires_at": 1},
    ) or {}
    tier_id = profile.get("tier", "free")
    return {
        "tier": tier_id,
        "tier_name": (TIERS.get(tier_id) or TIERS["free"])["name"],
        "tier_expires_at": profile.get("tier_expires_at"),
        "available_tiers": [
            {
                "id": k,
                "name": v["name"],
                "description": v["description"],
                "price_monthly": v.get("price_monthly", 0),
                "daily_tokens": v["daily_tokens"],
            }
            for k, v in TIERS.items()
        ],
    }


# ---- Webhook (mounted under /api/webhook/stripe by server.py) -------------

webhook_router = APIRouter(prefix="/webhook", tags=["billing"])


@webhook_router.post("/stripe")
async def stripe_webhook(request: Request) -> dict:
    """Stripe POSTs here on `checkout.session.completed` etc. Signature is
    validated by the emergentintegrations handler. Idempotent: if the txn's
    `applied=True`, we no-op so a later poll doesn't double-grant.
    """
    host_url = str(request.base_url).rstrip("/")
    try:
        stripe = _stripe_checkout(host_url)
    except HTTPException as e:
        log.error("stripe webhook bootstrap failed: %s", e.detail)
        return {"ok": False, "error": "stripe not configured"}

    body_bytes = await request.body()
    signature = request.headers.get("Stripe-Signature", "")
    try:
        event = await stripe.handle_webhook(body_bytes, signature)
    except Exception as error:
        log.warning("invalid stripe webhook signature: %s", error)
        return {"ok": False, "error": "invalid signature"}

    if (event.event_type or "").lower() in {"checkout.session.completed", "payment_intent.succeeded"}:
        txn = await collection("payment_transactions").find_one(
            {"session_id": event.session_id}, {"_id": 0},
        )
        if txn and not txn.get("applied"):
            await collection("payment_transactions").update_one(
                {"session_id": event.session_id},
                {"$set": {
                    "status": "paid",
                    "payment_status": event.payment_status or "paid",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }},
            )
            await _grant_tier_upgrade(txn["user_email"], txn["tier_id"], event.session_id)
    return {"ok": True}


# ---- Internal grant helper ------------------------------------------------

async def _grant_tier_upgrade(user_email: str, tier_id: str, session_id: str) -> str:
    """Atomically grant 30 days of `tier_id`. Idempotent on session_id.

    If the user is already on a paid tier with time remaining, those days
    stack on top — they don't lose unused time. If they're on free or
    expired, the new pass starts now.

    Returns ISO timestamp of the new expiry.
    """
    txn_filter = {"session_id": session_id, "applied": {"$ne": True}}
    profile = await collection("user_profiles").find_one(
        {"user_email": user_email}, {"_id": 0, "tier": 1, "tier_expires_at": 1},
    ) or {}
    now = datetime.now(timezone.utc)
    current_expiry: Optional[datetime] = None
    if profile.get("tier_expires_at"):
        try:
            current_expiry = datetime.fromisoformat(profile["tier_expires_at"])
            if current_expiry.tzinfo is None:
                current_expiry = current_expiry.replace(tzinfo=timezone.utc)
        except Exception:
            current_expiry = None
    base = current_expiry if (current_expiry and current_expiry > now and profile.get("tier") == tier_id) else now
    new_expiry = base + timedelta(days=PASS_DAYS)
    new_expiry_iso = new_expiry.isoformat()

    # Atomic flip — only the first caller (poll OR webhook) succeeds. If the
    # txn already has applied=True, this is a no-op + the grant logic below
    # is skipped.
    txn_update = await collection("payment_transactions").update_one(
        txn_filter,
        {"$set": {"applied": True, "applied_at": now.isoformat(), "tier_expires_at": new_expiry_iso}},
    )
    if txn_update.modified_count == 0:
        # Already applied — return whatever's currently in the user profile.
        return profile.get("tier_expires_at") or new_expiry_iso

    await collection("user_profiles").update_one(
        {"user_email": user_email},
        {"$set": {
            "tier": tier_id,
            "tier_expires_at": new_expiry_iso,
            "updated_at": now.isoformat(),
        }},
        upsert=True,
    )
    log.info("granted tier=%s to %s, expires %s", tier_id, user_email, new_expiry_iso)
    return new_expiry_iso
