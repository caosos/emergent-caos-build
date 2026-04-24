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


def _iso(dt: datetime) -> str:
    return dt.isoformat()


@router.get("/dashboard/metrics")
async def get_dashboard_metrics(user: dict = Depends(require_admin)):
    """Full dashboard payload — live status, registrations, sessions, login
    methods, tier distribution, open tickets. Base44 parity.
    """
    now = datetime.now(timezone.utc)
    hour_ago = _iso(now - timedelta(hours=1))
    day_ago = _iso(now - timedelta(days=1))
    week_ago = _iso(now - timedelta(days=7))
    month_ago = _iso(now - timedelta(days=30))
    today_str = now.date().isoformat()
    week_start = _iso(datetime(now.year, now.month, now.day, tzinfo=timezone.utc) - timedelta(days=now.weekday()))
    today_start = _iso(datetime(now.year, now.month, now.day, tzinfo=timezone.utc))

    users_col = collection("users")
    sessions_col = collection("sessions")
    user_sessions_col = collection("user_sessions")
    messages_col = collection("messages")
    tickets_col = collection("support_tickets")
    profiles_col = collection("user_profiles")
    tokens_col = collection("token_usage")

    # --- LIVE STATUS ---------------------------------------------------------
    # A registered user is "active in last hour" if any of their caos sessions
    # (threads) got updated in that window.
    active_registered_1h = len(
        await sessions_col.distinct("user_email", {"updated_at": {"$gte": hour_ago}})
    )
    # Guest counting — we don't currently flag guest threads explicitly; count
    # caos sessions whose user_email is falsy/missing within the hour window.
    active_guests_1h = await sessions_col.count_documents({
        "updated_at": {"$gte": hour_ago},
        "$or": [{"user_email": {"$exists": False}}, {"user_email": ""}, {"user_email": None}],
    })
    # Unique-user counts for today / this week (not session touches — otherwise
    # the number balloons with chatty users).
    active_today = len(await sessions_col.distinct("user_email", {"updated_at": {"$gte": day_ago}}))
    active_week = len(await sessions_col.distinct("user_email", {"updated_at": {"$gte": week_ago}}))

    # --- REGISTERED ACCOUNTS -------------------------------------------------
    total_registered = await users_col.count_documents({})
    # "Ever logged in" — users that have an explicit last_login OR at least one
    # user_sessions row ever.
    ever_logged_in_set = set(await user_sessions_col.distinct("user_id"))
    ever_logged_in = len(ever_logged_in_set)
    new_this_month = await users_col.count_documents({"created_at": {"$gte": month_ago}})
    new_this_week = await users_col.count_documents({"created_at": {"$gte": week_start}})
    new_today = await users_col.count_documents({"created_at": {"$gte": today_start}})

    # Tier distribution (from profiles), clamped to total_registered
    tier_counts = await profiles_col.aggregate([
        {"$group": {"_id": "$tier", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]).to_list(10)
    raw_tiers = {(item["_id"] or "free"): item["count"] for item in tier_counts}
    tier_sum = sum(raw_tiers.values()) or 1
    if tier_sum > total_registered and total_registered > 0:
        factor = total_registered / tier_sum
        tier_distribution = {t: max(0, int(round(c * factor))) for t, c in raw_tiers.items()}
    else:
        tier_distribution = dict(raw_tiers)
        untiered = max(0, total_registered - sum(tier_distribution.values()))
        if untiered > 0:
            tier_distribution["free"] = tier_distribution.get("free", 0) + untiered

    # --- SESSIONS / THREADS --------------------------------------------------
    total_threads = await sessions_col.count_documents({})
    threads_today = await sessions_col.count_documents({"created_at": {"$gte": today_start}})
    threads_this_week = await sessions_col.count_documents({"created_at": {"$gte": week_start}})

    # Guest thread count (threads without a user_email)
    guest_threads = await sessions_col.count_documents({
        "$or": [{"user_email": {"$exists": False}}, {"user_email": ""}, {"user_email": None}],
    })

    # Average session length: for each thread, use the span between earliest and
    # latest message; then average. Done via aggregation pipeline.
    avg_pipeline = [
        {"$group": {"_id": "$session_id", "first": {"$min": "$timestamp"}, "last": {"$max": "$timestamp"}}},
        {"$project": {
            "seconds": {"$divide": [{"$subtract": [{"$toDate": "$last"}, {"$toDate": "$first"}]}, 1000]},
        }},
        {"$match": {"seconds": {"$gt": 0}}},
        {"$group": {"_id": None, "avg_seconds": {"$avg": "$seconds"}}},
    ]
    avg_result = await messages_col.aggregate(avg_pipeline).to_list(1)
    avg_seconds = (avg_result[0]["avg_seconds"] if avg_result else 0) or 0
    avg_minutes = int(round(avg_seconds / 60)) if avg_seconds else 0

    # --- LOGIN METHODS -------------------------------------------------------
    # Currently every authenticated login is Google OAuth; guest = threads with
    # no user_email. We derive a simple approximation here.
    login_methods = {
        "google": total_registered,
        "guest": guest_threads,
    }

    # --- TOKEN USAGE (kept for backwards compat) -----------------------------
    usage_pipeline = [
        {"$match": {"date": {"$gte": (now - timedelta(days=30)).date().isoformat(), "$lte": today_str}}},
        {"$group": {
            "_id": None,
            "total_tokens": {"$sum": "$tokens_used"},
            "total_requests": {"$sum": {"$size": {"$ifNull": ["$requests", []]}}},
        }},
    ]
    usage_result = await tokens_col.aggregate(usage_pipeline).to_list(1)
    token_stats = usage_result[0] if usage_result else {"total_tokens": 0, "total_requests": 0}

    # --- SUPPORT -------------------------------------------------------------
    open_tickets = await tickets_col.count_documents({"status": {"$ne": "closed"}})

    return {
        "live_status": {
            "active_registered_1h": active_registered_1h,
            "active_guests_1h": active_guests_1h,
            "active_today": active_today,
            "active_week": active_week,
        },
        "registered_accounts": {
            "total": total_registered,
            "ever_logged_in": ever_logged_in,
            "new_this_month": new_this_month,
            "new_this_week": new_this_week,
            "new_today": new_today,
        },
        "sessions": {
            "total_ever": total_threads,
            "guest_sessions": guest_threads,
            "avg_session_minutes": avg_minutes,
            "total_threads": total_threads,
            "threads_today": threads_today,
            "threads_this_week": threads_this_week,
        },
        "login_methods": login_methods,
        # Back-compat shape used by existing Overview UI:
        "users": {
            "total": total_registered,
            "active_7d": active_week,
            "by_tier": tier_distribution,
        },
        "usage": {
            "total_tokens_30d": token_stats.get("total_tokens", 0),
            "total_requests_30d": token_stats.get("total_requests", 0),
            "total_sessions": total_threads,
            "total_messages": await messages_col.count_documents({}),
        },
        "support": {"open_tickets": open_tickets},
        "timestamp": _iso(now),
    }


@router.get("/dashboard/activity-14d")
async def get_activity_14d(user: dict = Depends(require_admin)):
    """Daily new-registration and new-session counts for the last 14 days (for
    the twin sparkline charts)."""
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) - timedelta(days=13)

    # Build a 14-day skeleton so even days with zero activity appear.
    days = []
    for i in range(14):
        d = (start + timedelta(days=i)).date()
        days.append(d.isoformat())

    # Registrations
    regs_pipeline = [
        {"$match": {"created_at": {"$gte": start.isoformat()}}},
        {"$project": {"day": {"$substr": ["$created_at", 0, 10]}}},
        {"$group": {"_id": "$day", "count": {"$sum": 1}}},
    ]
    regs_rows = await collection("users").aggregate(regs_pipeline).to_list(50)
    reg_map = {r["_id"]: r["count"] for r in regs_rows}

    # Sessions started
    sess_pipeline = [
        {"$match": {"created_at": {"$gte": start.isoformat()}}},
        {"$project": {"day": {"$substr": ["$created_at", 0, 10]}}},
        {"$group": {"_id": "$day", "count": {"$sum": 1}}},
    ]
    sess_rows = await collection("sessions").aggregate(sess_pipeline).to_list(50)
    sess_map = {r["_id"]: r["count"] for r in sess_rows}

    return {
        "period": {"start": days[0], "end": days[-1]},
        "registrations": [{"date": d, "count": reg_map.get(d, 0)} for d in days],
        "sessions": [{"date": d, "count": sess_map.get(d, 0)} for d in days],
    }


@router.get("/dashboard/errors")
async def get_errors(user: dict = Depends(require_admin)):
    """Error stats. Sourced from the `error_log` collection (populated by
    `app.services.error_logger`). If empty, UI renders a 'No errors yet' state.
    """
    from app.services.error_logger import get_error_stats
    return await get_error_stats()


@router.get("/dashboard/errors/recent")
async def get_recent_errors(user: dict = Depends(require_admin)):
    from app.services.error_logger import list_recent_errors
    rows = await list_recent_errors(limit=50)
    return {"errors": rows}


@router.get("/dashboard/engine-timeline/{session_id}")
async def get_engine_timeline(session_id: str, user: dict = Depends(require_admin)):
    """Per-session audit: which engine answered each assistant turn, in order.
    Feeds the 'Engine Timeline' artifact view.
    """
    rows = await collection("messages").find(
        {"session_id": session_id, "role": "assistant"},
        {"_id": 0, "id": 1, "timestamp": 1, "inference_provider": 1, "latency_ms": 1, "tools_used": 1, "content": 1},
    ).sort("timestamp", 1).to_list(1000)
    # Trim content preview
    for row in rows:
        row["preview"] = (row.pop("content", "") or "")[:140]
    return {"session_id": session_id, "turns": rows}


@router.get("/dashboard/token-usage")
async def get_token_usage_breakdown(user: dict = Depends(require_admin)):
    """Detailed token usage by user (last 30 days)."""
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
    today = datetime.now(timezone.utc).date().isoformat()

    pipeline = [
        {"$match": {"date": {"$gte": thirty_days_ago, "$lte": today}}},
        {"$group": {"_id": "$user_email", "total_tokens": {"$sum": "$tokens_used"}, "days_active": {"$sum": 1}}},
        {"$sort": {"total_tokens": -1}},
        {"$limit": 100},
    ]
    results = await collection("token_usage").aggregate(pipeline).to_list(100)
    for item in results:
        profile = await collection("user_profiles").find_one({"user_email": item["_id"]}, {"tier": 1, "_id": 0})
        item["tier"] = profile.get("tier", "free") if profile else "free"
        item["user_email"] = item.pop("_id")
    return {"users": results, "period": {"start": thirty_days_ago, "end": today}}


@router.get("/dashboard/daily-usage")
async def get_daily_usage(user: dict = Depends(require_admin)):
    """Daily token usage for last 30 days (for charts)."""
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
    today = datetime.now(timezone.utc).date().isoformat()

    pipeline = [
        {"$match": {"date": {"$gte": thirty_days_ago, "$lte": today}}},
        {"$group": {"_id": "$date", "total_tokens": {"$sum": "$tokens_used"}, "unique_users": {"$addToSet": "$user_email"}}},
        {"$project": {"date": "$_id", "total_tokens": 1, "unique_users": {"$size": "$unique_users"}, "_id": 0}},
        {"$sort": {"date": 1}},
    ]
    results = await collection("token_usage").aggregate(pipeline).to_list(31)
    return {"daily_stats": results, "period": {"start": thirty_days_ago, "end": today}}
