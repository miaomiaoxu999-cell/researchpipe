"""Idempotency-Key + token-bucket rate limit middleware.

PRD ch4 + EDD ch7 spec:
  - Idempotency-Key: 24h replay (same key + same path returns cached response)
    → backed by SQLite (storage.idem_*) for restart-survival
  - Rate limit: 60 req/min sustained + burst 10, per-API-key (in-memory; refreshes naturally)
  - Usage logging: every 200/2xx response → storage.usage_log (async, non-blocking)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections import deque
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from . import storage

# ─────────────────────────────────────────────────────────────────────────
# Idempotency cache — SQLite-backed (storage.idem_*) with in-memory fast-path
# ─────────────────────────────────────────────────────────────────────────


class IdempotencyCache:
    """24h TTL cache. Reads/writes to storage.idem_* via async wrappers.

    Has a tiny in-memory shadow `_store` to keep unit-tests' `_store.clear()` working.
    """

    def __init__(self, ttl_s: int = 24 * 3600):
        self.ttl_s = ttl_s
        self._store: dict[str, tuple[float, dict[str, Any]]] = {}  # in-memory shadow (test-friendly)
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> dict[str, Any] | None:
        now = time.time()
        # Memory fast path
        async with self._lock:
            v = self._store.get(key)
        if v:
            ts, data = v
            if now - ts <= self.ttl_s:
                return data
        # SQLite slow path (survives restart)
        try:
            stored = await storage.idem_get(key, ttl_s=self.ttl_s)
            if stored:
                # Backfill memory shadow
                async with self._lock:
                    self._store[key] = (now, stored)
                return stored
        except Exception:
            pass
        return None

    async def set(self, key: str, response_body: bytes, status_code: int, content_type: str):
        data = {"body": response_body, "status_code": status_code, "content_type": content_type}
        async with self._lock:
            self._store[key] = (time.time(), data)
            if len(self._store) > 5000:
                cutoff = time.time() - self.ttl_s
                self._store = {k: v for k, v in self._store.items() if v[0] > cutoff}
        # Persist to SQLite (best-effort)
        try:
            api_key = key.split("|", 1)[0]
            await storage.idem_set(key, api_key, response_body, status_code, content_type)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────
# Token bucket rate limit per API key
# ─────────────────────────────────────────────────────────────────────────


class TokenBucket:
    """Token bucket: capacity=10 (burst), refill=1 token / second (= 60/min)."""

    def __init__(self, capacity: int = 10, refill_per_s: float = 1.0):
        self.capacity = capacity
        self.refill_per_s = refill_per_s
        self._tokens: dict[str, float] = {}
        self._last: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def take(self, key: str) -> tuple[bool, int, int]:
        """Returns (allowed, remaining_tokens_int, retry_after_seconds_int).

        retry_after is only meaningful when allowed=False.
        """
        async with self._lock:
            now = time.time()
            last = self._last.get(key, now)
            tokens = self._tokens.get(key, float(self.capacity))
            tokens = min(self.capacity, tokens + (now - last) * self.refill_per_s)
            if tokens >= 1.0:
                tokens -= 1.0
                self._tokens[key] = tokens
                self._last[key] = now
                return True, int(tokens), 0
            # Not enough; compute wait time
            self._last[key] = now
            self._tokens[key] = tokens
            need = 1.0 - tokens
            wait = need / self.refill_per_s
            return False, 0, max(1, int(wait + 0.99))


# ─────────────────────────────────────────────────────────────────────────
# Wiring
# ─────────────────────────────────────────────────────────────────────────


idempotency = IdempotencyCache(ttl_s=24 * 3600)
ratelimit = TokenBucket(capacity=10, refill_per_s=1.0)
# Demo key: stricter — 5 burst, refill 5/hour (~0.0014/s). Shared across demo users.
demo_ratelimit = TokenBucket(capacity=5, refill_per_s=5.0 / 3600)


def _api_key_from_auth(authz: str | None) -> str | None:
    if not authz:
        return None
    parts = authz.strip().split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def _idempotency_cache_key(api_key: str, idem: str, method: str, path: str, body_bytes: bytes) -> str:
    h = hashlib.sha256(method.encode() + b"\0" + path.encode() + b"\0" + body_bytes).hexdigest()[:16]
    return f"{api_key}|{idem}|{h}"


def install_middleware(app):
    """Register the middleware on the app (sync — must run before app start)."""

    @app.middleware("http")
    async def rate_limit_and_idempotency(request: Request, call_next):
        # Skip non-/v1 paths (health / docs / root)
        if not request.url.path.startswith("/v1"):
            return await call_next(request)

        api_key = _api_key_from_auth(request.headers.get("authorization"))
        idem_key = request.headers.get("idempotency-key")

        # 1) Rate limit (only if we have an API key)
        if api_key:
            from .settings import RP_DEMO_API_KEY
            is_demo = api_key == RP_DEMO_API_KEY
            bucket = demo_ratelimit if is_demo else ratelimit
            # Demo key is shared — bucket per IP so one user can't burn quota for everyone.
            client_ip = (
                request.headers.get("x-forwarded-for", "").split(",")[0].strip()
                or (request.client.host if request.client else "unknown")
            )
            bucket_key = f"{api_key}|{client_ip}" if is_demo else api_key
            allowed, remaining, retry_after = await bucket.take(bucket_key)
            limit_label = "5 / hour / IP (demo)" if is_demo else "60 / min"
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    headers={
                        "X-RateLimit-Limit": "5" if is_demo else "60",
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(retry_after),
                        "Retry-After": str(retry_after),
                    },
                    content={
                        "error": {
                            "code": "rate_limit_exceeded",
                            "message": f"Rate limit: {limit_label}. Retry in {retry_after}s." + (
                                " Demo key has limited quota — sign up for a free key at https://rp.zgen.xin to remove limits."
                                if is_demo else ""
                            ),
                            "retry_after_seconds": retry_after,
                            "is_demo_key": is_demo,
                            "hint_for_agent": f"Wait {retry_after} seconds and retry. Pass `Idempotency-Key` header to safely retry without double-charge.",
                            "documentation_url": "https://rp.zgen.xin/docs/errors/rate_limit_exceeded",
                        }
                    },
                )
        else:
            remaining = 10

        # 2) Idempotency replay
        body_bytes = b""
        cached_resp = None
        if api_key and idem_key:
            body_bytes = await request.body()
            ckey = _idempotency_cache_key(api_key, idem_key, request.method, request.url.path, body_bytes)
            cached = await idempotency.get(ckey)
            if cached:
                # Replay
                hdrs = {
                    "X-RateLimit-Limit": "60",
                    "X-RateLimit-Remaining": str(remaining),
                    "X-Idempotency-Replay": "true",
                }
                if cached.get("content_type"):
                    hdrs["Content-Type"] = cached["content_type"]
                return Response(
                    content=cached["body"],
                    status_code=cached["status_code"],
                    headers=hdrs,
                )

            # Re-inject body so downstream can read it
            async def receive():
                return {"type": "http.request", "body": body_bytes, "more_body": False}

            request._receive = receive  # type: ignore[attr-defined]

        # Process request
        response = await call_next(request)

        # 3) Cache successful response if Idempotency-Key was set
        if api_key and idem_key and 200 <= response.status_code < 300:
            chunks: list[bytes] = []
            async for chunk in response.body_iterator:  # type: ignore[attr-defined]
                chunks.append(chunk)
            full_body = b"".join(chunks)
            content_type = response.headers.get("content-type", "application/json")
            ckey = _idempotency_cache_key(api_key, idem_key, request.method, request.url.path, body_bytes)
            await idempotency.set(ckey, full_body, response.status_code, content_type)
            response = Response(
                content=full_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=content_type,
            )

        # 4) Override rate limit headers
        response.headers["X-RateLimit-Limit"] = "60"
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        # 5) Async usage log (best-effort, doesn't block response)
        if api_key and 200 <= response.status_code < 300 and request.url.path.startswith("/v1"):
            asyncio.create_task(_log_usage_safe(api_key, request.url.path))

        return response


async def _log_usage_safe(api_key: str, path: str):
    """Log usage to SQLite without blocking response. Reads credits from response if needed.

    For now we use a fixed credits=1 default since extracting from response body would
    require buffering. Endpoints that want accurate logging should call storage.usage_log
    directly after computing credits.
    """
    try:
        # Map path → endpoint name (last 2 segments)
        parts = [p for p in path.strip("/").split("/") if not p.startswith("v1")]
        endpoint = "/".join(parts) if parts else path
        # Default credits — endpoints with metadata.credits_charged should override via direct call
        await storage.usage_log(api_key, endpoint, credits=1.0)
    except Exception:
        pass
