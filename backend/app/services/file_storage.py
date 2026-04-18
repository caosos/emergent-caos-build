from datetime import datetime, timezone
from pathlib import Path
import shutil
import uuid

from fastapi import UploadFile


UPLOAD_ROOT = Path("/app/backend/uploads")
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


def _kind_for_upload(file: UploadFile) -> str:
    if (file.content_type or "").startswith("image/"):
        return "photo"
    return "file"


def save_upload_to_disk(file: UploadFile, user_email: str, session_id: str | None = None) -> dict:
    user_dir = UPLOAD_ROOT / user_email.replace("@", "_").replace(".", "_")
    if session_id:
        user_dir = user_dir / session_id
    user_dir.mkdir(parents=True, exist_ok=True)
    extension = Path(file.filename or "upload.bin").suffix or ".bin"
    file_id = str(uuid.uuid4())
    stored_name = f"{file_id}{extension}"
    stored_path = user_dir / stored_name
    with stored_path.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    size = stored_path.stat().st_size
    return {
        "id": file_id,
        "user_email": user_email,
        "session_id": session_id,
        "name": file.filename or stored_name,
        "kind": _kind_for_upload(file),
        "mime_type": file.content_type or "application/octet-stream",
        "size": size,
        "storage_path": str(stored_path),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_link_record(user_email: str, url: str, label: str, session_id: str | None = None) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "user_email": user_email,
        "session_id": session_id,
        "name": label,
        "kind": "link",
        "mime_type": "text/uri-list",
        "size": 0,
        "url": url,
        "storage_path": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }