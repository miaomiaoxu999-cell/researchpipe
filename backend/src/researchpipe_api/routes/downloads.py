"""Static file serving for downloadable agent zip(s).

Path: GET /downloads/{filename}.zip → backend/static/downloads/{filename}.zip
No auth — these are public artifacts intended for free download.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parents[3]  # backend/
DOWNLOADS_DIR = ROOT / "static" / "downloads"

router = APIRouter(prefix="/downloads", tags=["downloads"])


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
    if not filename.endswith(".zip"):
        raise HTTPException(400, "only .zip downloads served here")

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
        media_type="application/zip",
        filename=filename,
        headers={"Cache-Control": "public, max-age=300"},
    )
