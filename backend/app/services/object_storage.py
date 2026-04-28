"""Emergent object storage adapter.

Wraps the Emergent object-storage REST API so the rest of the codebase can
stop writing to ephemeral disk (`/app/backend/uploads/`) and start storing
files durably. All paths are prefixed with `caos/` so we never collide with
other apps on the same bucket.

Public contract:
- `init_storage()` — call once at startup (fastapi on_event("startup")).
- `put_object(path, data, content_type)` — upload bytes, return `{path, size, etag}`.
- `get_object(path)` — download bytes, return an unpackable bytes payload.
- `is_storage_ready()` — bool, True if init succeeded.
"""
from __future__ import annotations

import logging
import os
import threading

import requests


STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
APP_PREFIX = "caos"
logger = logging.getLogger(__name__)

_storage_key: str | None = None
_lock = threading.Lock()


class ObjectPayload(bytes):
    """Bytes payload that also supports legacy tuple-unpack usage.

    Why this exists:
    - Download route uses: `data, content_type = get_object(path)`.
    - Vision attachment code uses: `raw = get_object(path)` and expects bytes.

    Returning this bytes subclass satisfies both call patterns without changing
    chat orchestration or route behavior. Iteration yields `(bytes, content_type)`
    for legacy unpacking; bytes APIs still receive a real bytes-like object.
    """

    content_type: str

    def __new__(cls, data: bytes, content_type: str):
        obj = super().__new__(cls, data)
        obj.content_type = content_type
        return obj

    def __iter__(self):
        yield bytes(self)
        yield self.content_type


def init_storage() -> str | None:
    """Initialize the storage session — idempotent. Returns the key (or None on failure)."""
    global _storage_key
    with _lock:
        if _storage_key:
            return _storage_key
        emergent_key = os.environ.get("EMERGENT_LLM_KEY")
        if not emergent_key:
            logger.warning("Object storage disabled: EMERGENT_LLM_KEY not set")
            return None
        try:
            response = requests.post(
                f"{STORAGE_URL}/init",
                json={"emergent_key": emergent_key},
                timeout=20,
            )
            response.raise_for_status()
            _storage_key = response.json()["storage_key"]
            logger.info("Object storage initialized")
            return _storage_key
        except Exception as error:
            logger.error("Object storage init failed: %s", str(error)[:200])
            return None


def is_storage_ready() -> bool:
    return _storage_key is not None


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    if not key:
        raise RuntimeError("Object storage not initialized")
    response = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data,
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def get_object(path: str) -> ObjectPayload:
    key = init_storage()
    if not key:
        raise RuntimeError("Object storage not initialized")
    response = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key},
        timeout=60,
    )
    response.raise_for_status()
    return ObjectPayload(
        response.content,
        response.headers.get("Content-Type", "application/octet-stream"),
    )


def build_path(user_id: str, filename: str, uuid_suffix: str) -> str:
    """Canonical path: caos/uploads/<user_id>/<uuid>.<ext>"""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    ext = "".join(ch for ch in ext if ch.isalnum())[:12] or "bin"
    return f"{APP_PREFIX}/uploads/{user_id}/{uuid_suffix}.{ext}"
