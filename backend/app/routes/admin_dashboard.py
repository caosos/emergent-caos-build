"""Admin dashboard API endpoints for metrics and management."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from app.services.auth_service import require_user
from app.db import collection

router = APIRouter(prefix="/admin", tags=["admin"])


async def require_admin(user: dict = Depends(require_user)) -> dict:
    """Require admin role. Checks the authenticated user record (synced at
    login time via auth_service) — same pattern as admin_docs.py."""
    if not (user.get("is_admin") or user.get("role") == "admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/dashboard/metrics")
async def get_dashboard_metrics(user: dict = Depends(require_admin)):
    """Get overall platform metrics for admin dashboard."""

    # Users — total from users collection (source of truth for authenticated users)
    total_users = await collection("users").count_documents({})

    # Users by tier — aggregated from user_profiles, then capped so the sum never
    # exceeds total_users. Users without a profile are bucketed as `free`.
    tier_pipeline = [
        {"$group": {"_id": "$tier", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    tier_counts = await collection("user_profiles").aggregate(tier_pipeline).to_list(10)
    raw_tier_distribution = {
        (item["_id"] or "free"): item["count"]
        for item in tier_counts
    }
    # Clamp: tier distribution should never claim more users than exist. Rescale if needed.
    tier_sum = sum(raw_tier_distribution.values()) or 1
    if tier_sum > total_users and total_users > 0:
        factor = total_users / tier_sum
        tier_distribution = {
            tier: max(0, int(round(count * factor)))
            for tier, count in raw_tier_distribution.items()
        }
    else:
        tier_distribution = raw_tier_distribution
        # Fill in untiered users as free
        untiered = max(0, total_users - sum(tier_distribution.values()))
        if untiered > 0:
            tier_distribution["free"] = tier_distribution.get("free", 0) + untiered
    
    # Active users (logged in last 7 days)
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    active_users = await collection("users").count_documents({
        "last_login": {"$gte": week_ago}
    })
    
    # Token usage (last 30 days)
    today = datetime.now(timezone.utc).date().isoformat()
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
    
    usage_pipeline = [
        {"$match": {
            "date": {"$gte": thirty_days_ago, "$lte": today}
        }},
        {"$group": {
            "_id": None,
            "total_tokens": {"$sum": "$tokens_used"},
            "total_requests": {"$sum": {"$size": {"$ifNull": ["$requests", []]}}}
        }}
    ]
    usage_result = await collection("token_usage").aggregate(usage_pipeline).to_list(1)
    token_stats = usage_result[0] if usage_result else {"total_tokens": 0, "total_requests": 0}
    
    # Total sessions/threads
    total_sessions = await collection("sessions").count_documents({})
    
    # Total messages
    total_messages = await collection("messages").count_documents({})
    
    # Open support tickets
    open_tickets = await collection("support_tickets").count_documents({
        "status": {"$ne": "closed"}
    })
    
    return {
        "users": {
            "total": total_users,
            "active_7d": active_users,
            "by_tier": tier_distribution,
        },
        "usage": {
            "total_tokens_30d": token_stats.get("total_tokens", 0),
            "total_requests_30d": token_stats.get("total_requests", 0),
            "total_sessions": total_sessions,
            "total_messages": total_messages,
        },
        "support": {
            "open_tickets": open_tickets,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/dashboard/token-usage")
async def get_token_usage_breakdown(user: dict = Depends(require_admin)):
    """Get detailed token usage by user (last 30 days)."""
    
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
    today = datetime.now(timezone.utc).date().isoformat()
    
    pipeline = [
        {"$match": {
            "date": {"$gte": thirty_days_ago, "$lte": today}
        }},
        {"$group": {
            "_id": "$user_email",
            "total_tokens": {"$sum": "$tokens_used"},
            "days_active": {"$sum": 1},
        }},
        {"$sort": {"total_tokens": -1}},
        {"$limit": 100}
    ]
    
    results = await collection("token_usage").aggregate(pipeline).to_list(100)
    
    # Enhance with tier info
    for item in results:
        profile = await collection("user_profiles").find_one(
            {"user_email": item["_id"]},
            {"tier": 1, "_id": 0}
        )
        item["tier"] = profile.get("tier", "free") if profile else "free"
        item["user_email"] = item.pop("_id")
    
    return {
        "users": results,
        "period": {"start": thirty_days_ago, "end": today},
    }


@router.get("/dashboard/daily-usage")
async def get_daily_usage(user: dict = Depends(require_admin)):
    """Get daily token usage for last 30 days (for charts)."""
    
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
    today = datetime.now(timezone.utc).date().isoformat()
    
    pipeline = [
        {"$match": {
            "date": {"$gte": thirty_days_ago, "$lte": today}
        }},
        {"$group": {
            "_id": "$date",
            "total_tokens": {"$sum": "$tokens_used"},
            "unique_users": {"$addToSet": "$user_email"},
        }},
        {"$project": {
            "date": "$_id",
            "total_tokens": 1,
            "unique_users": {"$size": "$unique_users"},
            "_id": 0,
        }},
        {"$sort": {"date": 1}}
    ]
    
    results = await collection("token_usage").aggregate(pipeline).to_list(31)
    
    return {
        "daily_stats": results,
        "period": {"start": thirty_days_ago, "end": today},
    }
