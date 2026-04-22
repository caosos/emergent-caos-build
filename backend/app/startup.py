"""MongoDB index creation + object-storage bootstrap at FastAPI startup.

Run once on boot. Idempotent — MongoDB silently skips already-existing indexes.
Indexes eliminate the full-collection scans that were happening on every
session / message / receipt query. With ~82 sessions in prod today this wasn't
user-visible yet, but it degrades quickly.
"""
from __future__ import annotations

import logging

from pymongo import ASCENDING, DESCENDING

from app.db import db


logger = logging.getLogger(__name__)


async def ensure_indexes() -> None:
    """Create the indexes used by hot code paths. Safe to call at every startup."""
    specs = [
        ("sessions", [("user_email", ASCENDING), ("session_id", ASCENDING)], {}),
        ("sessions", [("user_email", ASCENDING), ("updated_at", DESCENDING)], {}),
        ("messages", [("session_id", ASCENDING), ("timestamp", ASCENDING)], {}),
        ("user_profiles", [("user_email", ASCENDING)], {"unique": True}),
        ("user_files", [("user_email", ASCENDING), ("created_at", DESCENDING)], {}),
        ("user_files", [("user_email", ASCENDING), ("session_id", ASCENDING)], {}),
        ("user_links", [("user_id", ASCENDING), ("session_id", ASCENDING), ("normalized_url", ASCENDING)], {"unique": True}),
        ("user_links", [("user_id", ASCENDING), ("session_id", ASCENDING), ("updated_at", DESCENDING)], {}),
        ("receipts", [("session_id", ASCENDING), ("created_at", DESCENDING)], {}),
        ("thread_summaries", [("session_id", ASCENDING)], {}),
        ("context_seeds", [("session_id", ASCENDING)], {}),
        ("global_info_entries", [("user_email", ASCENDING), ("lane", ASCENDING)], {}),
        ("user_sessions", [("session_token", ASCENDING)], {"unique": True}),
        ("user_sessions", [("user_id", ASCENDING), ("expires_at", ASCENDING)], {}),
        ("users", [("email", ASCENDING)], {"unique": True}),
        ("users", [("user_id", ASCENDING)], {"unique": True}),
    ]
    created, skipped = 0, 0
    for collection, keys, options in specs:
        try:
            await db[collection].create_index(keys, **options)
            created += 1
        except Exception as error:
            # Likely pre-existing incompatible index — not fatal.
            logger.warning("Index skip on %s: %s", collection, str(error)[:160])
            skipped += 1
    logger.info("CAOS indexes: created/ok=%d, warned=%d", created, skipped)
