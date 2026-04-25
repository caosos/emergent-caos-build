"""Token quota system for freemium model.

Tracks token usage per user and enforces daily limits.
"""
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db import collection


# Tier configurations: Free → Novice → Skilled → Elite → Pro → Enterprise
TIERS = {
    "free": {
        "daily_tokens": 50000,  # 50k tokens/month (~20 chats)
        "name": "Free",
        "description": "Trial tier - get started with CAOS",
    },
    "novice": {
        "daily_tokens": 250000,  # 250k tokens/month (~100 chats)
        "name": "Novice",
        "description": "$10/month - Casual users",
        "price_monthly": 10,
    },
    "skilled": {
        "daily_tokens": 500000,  # 500k tokens/month (~200 chats)
        "name": "Skilled",
        "description": "$20/month - Regular users",
        "price_monthly": 20,
    },
    "elite": {
        "daily_tokens": 2000000,  # 2M tokens/month (~800 chats)
        "name": "Elite",
        "description": "$50/month - Active power users",
        "price_monthly": 50,
    },
    "pro": {
        "daily_tokens": 5000000,  # 5M tokens/month (~2k chats)
        "name": "Pro",
        "description": "$100/month - Professional users",
        "price_monthly": 100,
    },
    "enterprise": {
        "daily_tokens": 10000000,  # 10M tokens/month (~4k chats)
        "name": "Enterprise",
        "description": "$200/month - Teams & businesses",
        "price_monthly": 200,
    },
}


async def get_user_quota(user_email: str) -> dict:
    """Get user's current quota status.
    
    Returns:
        {
            "tier": "free",
            "tokens_used_today": 1234,
            "tokens_remaining": 48766,
            "daily_limit": 50000,
            "resets_at": "2026-04-25T00:00:00Z"
        }
    """
    # Get or create usage record
    today = datetime.now(timezone.utc).date().isoformat()
    usage_doc = await collection("token_usage").find_one(
        {"user_email": user_email, "date": today},
        {"_id": 0}
    )
    
    if not usage_doc:
        usage_doc = {
            "user_email": user_email,
            "date": today,
            "tokens_used": 0,
        }
        await collection("token_usage").insert_one(usage_doc)
    
    # Get user's tier (default to free). Honors `tier_expires_at`: a user
    # with an expired pass silently falls back to "free" so quota enforcement
    # still works without a cron job. Their `tier` field is NOT auto-rewritten
    # — that happens lazily on next upgrade or admin tooling.
    profile = await collection("user_profiles").find_one(
        {"user_email": user_email},
        {"tier": 1, "tier_expires_at": 1, "_id": 0}
    )
    tier = profile.get("tier", "free") if profile else "free"
    expires_at_iso = (profile or {}).get("tier_expires_at")
    if tier != "free" and expires_at_iso:
        try:
            expires_at = datetime.fromisoformat(expires_at_iso)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < datetime.now(timezone.utc):
                tier = "free"
        except Exception:
            tier = "free"
    tier_config = TIERS.get(tier, TIERS["free"])
    
    tokens_used = usage_doc.get("tokens_used", 0)
    daily_limit = tier_config["daily_tokens"]
    tokens_remaining = max(0, daily_limit - tokens_used)
    
    # Calculate reset time (next midnight UTC)
    tomorrow = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = tomorrow.replace(day=tomorrow.day + 1)
    
    return {
        "tier": tier,
        "tier_name": tier_config["name"],
        "tokens_used_today": tokens_used,
        "tokens_remaining": tokens_remaining,
        "daily_limit": daily_limit,
        "resets_at": tomorrow.isoformat(),
    }


async def check_and_deduct_tokens(user_email: str, tokens: int) -> dict:
    """Check if user has quota, deduct if available.
    
    Returns:
        {
            "allowed": True/False,
            "tokens_remaining": 48000,
            "message": "..." if not allowed
        }
    """
    quota = await get_user_quota(user_email)
    
    if tokens > quota["tokens_remaining"]:
        return {
            "allowed": False,
            "tokens_remaining": quota["tokens_remaining"],
            "message": f"Daily token limit reached. You have {quota['tokens_remaining']} tokens remaining. Resets at {quota['resets_at']}. Upgrade to Pro for more!"
        }
    
    # Deduct tokens
    today = datetime.now(timezone.utc).date().isoformat()
    await collection("token_usage").update_one(
        {"user_email": user_email, "date": today},
        {"$inc": {"tokens_used": tokens}},
        upsert=True
    )
    
    return {
        "allowed": True,
        "tokens_remaining": quota["tokens_remaining"] - tokens,
        "message": f"Success. {quota['tokens_remaining'] - tokens} tokens remaining today."
    }


async def record_token_usage(user_email: str, tokens_used: int, session_id: str = None, model: str = None):
    """Record token usage for a completed request (for analytics/debugging)."""
    today = datetime.now(timezone.utc).date().isoformat()
    
    # Update daily total
    await collection("token_usage").update_one(
        {"user_email": user_email, "date": today},
        {
            "$inc": {"tokens_used": tokens_used},
            "$push": {
                "requests": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "tokens": tokens_used,
                    "session_id": session_id,
                    "model": model,
                }
            }
        },
        upsert=True
    )
