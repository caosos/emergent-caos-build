"""Token quota system for freemium model.

Tracks token usage per user and enforces daily limits.
"""
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db import collection


# Tier configurations
TIERS = {
    "free": {
        "daily_tokens": 50000,  # 50k tokens/day (~10-15 solid interactions)
        "name": "Free Tier",
        "description": "Perfect for trying out CAOS",
    },
    "pro": {
        "daily_tokens": 500000,  # 500k tokens/day
        "name": "Pro Tier",
        "description": "$10/month - For power users",
    },
    "unlimited": {
        "daily_tokens": float("inf"),
        "name": "Unlimited",
        "description": "$30/month - No limits",
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
    
    # Get user's tier (default to free)
    profile = await collection("user_profiles").find_one(
        {"user_email": user_email},
        {"tier": 1, "_id": 0}
    )
    tier = profile.get("tier", "free") if profile else "free"
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
