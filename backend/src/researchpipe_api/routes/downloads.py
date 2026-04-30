"""Static file serving for downloadable artifacts.

Path: GET /downloads/{filename} → backend/static/downloads/{filename}
No auth — these are public artifacts (agent zips, deep-research reports).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parents[3]  # backend/
DOWNLOADS_DIR = ROOT / "static" / "downloads"

router = APIRouter(prefix="/downloads", tags=["downloads"])

ALLOWED_EXTS = {".zip": "application/zip", ".md": "text/markdown; charset=utf-8"}


@router.get("/{filename}")
async def get_download(filename: str):
    # Defense in depth: reject anything that looks like a path or extension switch.
    if (
        "/" in filename
        or "\\" in filename
        or ".." in filename
        or "\x00" in filename
        or filename.startswith(".")
    ):
        raise HTTPException(400, "invalid filename")
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    media_type = ALLOWED_EXTS.get(suffix)
    if not media_type:
        raise HTTPException(400, f"unsupported extension; allowed: {', '.join(ALLOWED_EXTS)}")

    fp = DOWNLOADS_DIR / filename
    # Resolve and confirm we stay under DOWNLOADS_DIR (catches any residual edge case).
    try:
        resolved = fp.resolve()
        resolved.relative_to(DOWNLOADS_DIR.resolve())
    except (ValueError, OSError):
        raise HTTPException(400, "invalid filename")
    if not resolved.is_file():
        raise HTTPException(404, f"{filename} not found")

    return FileResponse(
        resolved,
        media_type=media_type,
        filename=filename,
        headers={"Cache-Control": "public, max-age=300"},
    )
