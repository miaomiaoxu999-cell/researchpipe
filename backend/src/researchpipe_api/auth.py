"""Bearer auth dependency."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request

from .settings import VALID_API_KEYS


def _hint(message: str) -> dict:
    """Format a hint_for_agent error body."""
    return {
        "error": {
            "code": "auth_invalid",
            "message": message,
            "hint_for_agent": "Set Authorization: Bearer rp-... header. Get a key at https://rp.zgen.xin/dashboard.",
            "documentation_url": "https://rp.zgen.xin/docs/auth",
        }
    }


async def require_api_key(
    request: Request,
    authorization: str | None = Header(default=None),
) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail=_hint("missing Authorization header")["error"])
    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail=_hint("Authorization must be 'Bearer <key>'")["error"],
        )
    token = parts[1]
    if token not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail=_hint("invalid api key")["error"])
    request.state.api_key = token
    return token
