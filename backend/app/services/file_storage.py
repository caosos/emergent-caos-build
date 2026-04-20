"""File upload records. Uploads go to Emergent object storage when available,
falling back to a local ephemeral disk path only if storage init fails (dev).

Returns a dict that matches the existing user_files schema (same keys as before)
so the /files/upload route and downstream consumers don't need to change.
"""
from __future__ import annotations

import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile

from app.services.object_storage import build_path, is_storage_ready, put_object


LOCAL_FALLBACK_ROOT = Path("/app/backend/uploads")
LOCAL_FALLBACK_ROOT.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger(__name__)


def _kind_for_upload(file: UploadFile) -> str:
    if (file.content_type or "").startswith("image/"):
        return "photo"
    return "file"


def _save_local_fallback(file: UploadFile, user_id: str, session_id: str | None) -> tuple[str, int]:
    user_dir = LOCAL_FALLBACK_ROOT / user_id
    if session_id:
        user_dir = user_dir / session_id
    user_dir.mkdir(parents=True, exist_ok=True)
    extension = Path(file.filename or "upload.bin").suffix or ".bin"
    file_id = uuid.uuid4().hex
    stored_path = user_dir / f"{file_id}{extension}"
    with stored_path.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    return str(stored_path), stored_path.stat().st_size


async def save_upload(file: UploadFile, user: dict, session_id: str | None = None) -> dict:
    """Upload a file to durable object storage (or local fallback). `user` is the
    authenticated user dict (user_id + email) from the auth dependency."""
    file_id = str(uuid.uuid4())
    user_id = user["user_id"]
    user_email = user["email"]
    name = file.filename or f"{file_id}.bin"
    mime_type = file.content_type or "application/octet-stream"
    kind = _kind_for_upload(file)

    if is_storage_ready():
        raw = await file.read()
        storage_path = build_path(user_id, name, file_id)
        try:
            result = put_object(storage_path, raw, mime_type)
            return {
                "id": file_id,
                "user_id": user_id,
                "user_email": user_email,
                "session_id": session_id,
                "name": name,
                "kind": kind,
                "mime_type": mime_type,
                "size": result.get("size", len(raw)),
                "storage_path": result.get("path", storage_path),
                "storage_backend": "emergent_objstore",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as error:
            logger.warning("Object storage upload failed, falling back to disk: %s", str(error)[:200])
            # Reset the UploadFile so the local fallback can re-read it.
            await file.seek(0)

    stored_path, size = _save_local_fallback(file, user_id, session_id)
    return {
        "id": file_id,
        "user_id": user_id,
        "user_email": user_email,
        "session_id": session_id,
        "name": name,
        "kind": kind,
        "mime_type": mime_type,
        "size": size,
        "storage_path": stored_path,
        "storage_backend": "local_ephemeral",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# --- Backwards-compat shim for any caller still invoking the old sync API ---
def save_upload_to_disk(file: UploadFile, user_email: str, session_id: str | None = None) -> dict:
    """Legacy entry point retained so migration is gradual. Always writes to disk."""
    file_id = uuid.uuid4().hex
    stored_path, size = _save_local_fallback(file, user_email.replace("@", "_").replace(".", "_"), session_id)
    return {
        "id": file_id,
        "user_email": user_email,
        "session_id": session_id,
        "name": file.filename or f"{file_id}.bin",
        "kind": _kind_for_upload(file),
        "mime_type": file.content_type or "application/octet-stream",
        "size": size,
        "storage_path": stored_path,
        "storage_backend": "local_ephemeral",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_link_record(user: dict, url: str, label: str, session_id: str | None = None) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        "user_email": user["email"],
        "session_id": session_id,
        "name": label,
        "kind": "link",
        "mime_type": "text/uri-list",
        "size": 0,
        "url": url,
        "storage_path": None,
        "storage_backend": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
