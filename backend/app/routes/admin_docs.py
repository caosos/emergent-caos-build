"""Admin-only endpoints that expose in-repo project documentation (blueprints,
PRD, TSB log, etc.) to authenticated admin users. Keeps the agent's
contract docs visible inside the live CAOS shell."""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.services.auth_service import require_user

router = APIRouter(prefix="/admin", tags=["admin"])

# Absolute allow-list of directories we are willing to surface.
ALLOWED_ROOTS = [Path("/app/memory")]


def _admin_guard(user: dict) -> None:
    if not (user.get("is_admin") or user.get("role") == "admin"):
        raise HTTPException(status_code=403, detail="Admin access required")


def _resolve(filename: str) -> Path:
    # Only bare filenames, no traversal.
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")
    for root in ALLOWED_ROOTS:
        candidate = (root / filename).resolve()
        if candidate.is_file() and str(candidate).startswith(str(root.resolve())):
            return candidate
    raise HTTPException(status_code=404, detail="Document not found")


@router.get("/docs")
async def list_docs(user=Depends(require_user)):
    _admin_guard(user)
    items = []
    for root in ALLOWED_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.md")):
            stat = path.stat()
            items.append({
                "filename": path.name,
                "title": path.stem.replace("_", " ").title(),
                "size_bytes": stat.st_size,
                "modified_at": stat.st_mtime,
            })
    return {"documents": items}


@router.get("/docs/{filename}")
async def read_doc(filename: str, user=Depends(require_user)):
    _admin_guard(user)
    path = _resolve(filename)
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Unable to read doc: {exc}")
    return {"filename": path.name, "content": content}
