"""File upload records. Uploads go to Emergent object storage when available,
falling back to a local ephemeral disk path only if storage init fails (dev).

Returns a dict that matches the existing user_files schema (same keys as before)
so the /files/upload route and downstream consumers don't need to change.

HEIC/HEIF auto-transcode: iPhone photos upload as image/heic which no
mainstream browser can render in `<img>` tags. We transcode to JPEG at
upload time using `pillow-heif` so the chat thumbnail + lightbox just work.
"""
from __future__ import annotations

import io
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


# HEIC/HEIF support — register the opener once at module load so PIL.Image.open
# can handle them throughout the process. Fails closed with a warning if the
# native library is missing (we still accept the upload as raw HEIC; browser
# just won't render the preview).
_HEIF_AVAILABLE = False
try:
    import pillow_heif  # type: ignore[import-not-found]
    pillow_heif.register_heif_opener()
    _HEIF_AVAILABLE = True
except Exception as exc:  # pragma: no cover
    logger.warning("pillow-heif not available — HEIC uploads won't be transcoded: %s", exc)


def _maybe_transcode_heic(raw: bytes, mime_type: str, name: str) -> tuple[bytes, str, str]:
    """If `raw` is a HEIC/HEIF file and pillow-heif is available, transcode
    it to JPEG so browsers can render it in `<img>` tags. Returns
    `(bytes, mime_type, name)` — possibly the originals if no transcode
    happened. Errors fall through to the original bytes (better to store
    a HEIC the browser can't render than to drop the upload entirely).
    """
    is_heic = mime_type in {"image/heic", "image/heif", "image/heic-sequence", "image/heif-sequence"}
    if not is_heic or not _HEIF_AVAILABLE:
        return raw, mime_type, name
    try:
        from PIL import Image
        with Image.open(io.BytesIO(raw)) as img:
            # Force RGB — HEICs from iPhone Live Photos sometimes have an
            # alpha channel JPEG can't encode.
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            buf = io.BytesIO()
            # Quality 88 keeps the photo crisp without doubling file size.
            img.save(buf, format="JPEG", quality=88, optimize=True)
            new_name = Path(name).with_suffix(".jpg").name
            logger.info("HEIC transcoded to JPEG: %s → %s (%.1f KB → %.1f KB)",
                        name, new_name, len(raw) / 1024, buf.tell() / 1024)
            return buf.getvalue(), "image/jpeg", new_name
    except Exception as exc:
        logger.warning("HEIC transcode failed (storing original): %s", exc)
        return raw, mime_type, name


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
    authenticated user dict (user_id + email) from the auth dependency.
    HEIC/HEIF photos are auto-transcoded to JPEG so browsers can render them.
    """
    file_id = str(uuid.uuid4())
    user_id = user["user_id"]
    user_email = user["email"]
    name = file.filename or f"{file_id}.bin"
    mime_type = file.content_type or "application/octet-stream"

    raw = await file.read()
    raw, mime_type, name = _maybe_transcode_heic(raw, mime_type, name)
    kind = "photo" if mime_type.startswith("image/") else "file"

    # PDF text extraction (Path B): so OpenAI/Claude/Gemini all receive the
    # PDF's contents as text in the system prompt, regardless of which engine
    # the user picks. Without this, only Gemini could read PDFs (via its
    # native file-input API). The user's engine selector is never overridden.
    extracted_text = ""
    if mime_type == "application/pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(raw))
            chunks: list[str] = []
            total = 0
            MAX_BYTES = 32 * 1024  # 32 KB cap per file
            for page in reader.pages:
                page_text = (page.extract_text() or "").strip()
                if not page_text:
                    continue
                chunks.append(page_text)
                total += len(page_text)
                if total >= MAX_BYTES:
                    break
            extracted_text = ("\n\n".join(chunks))[:MAX_BYTES]
            logger.info("PDF extracted: %s — %d pages, %d chars", name, len(reader.pages), len(extracted_text))
        except Exception as exc:
            logger.warning("PDF extraction failed for %s: %s", name, exc)

    if is_storage_ready():
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
                "extracted_text": extracted_text,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as error:
            logger.warning("Object storage upload failed, falling back to disk: %s", str(error)[:200])

    # Local fallback — write the (possibly transcoded) bytes manually since
    # we already consumed the UploadFile stream.
    user_dir = LOCAL_FALLBACK_ROOT / user_id
    if session_id:
        user_dir = user_dir / session_id
    user_dir.mkdir(parents=True, exist_ok=True)
    extension = Path(name).suffix or ".bin"
    stored_path = user_dir / f"{file_id}{extension}"
    stored_path.write_bytes(raw)
    return {
        "id": file_id,
        "user_id": user_id,
        "user_email": user_email,
        "session_id": session_id,
        "name": name,
        "kind": kind,
        "mime_type": mime_type,
        "size": len(raw),
        "storage_path": str(stored_path),
        "storage_backend": "local_ephemeral",
        "extracted_text": extracted_text,
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
