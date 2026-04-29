"""Tavily Search + Extract client wrapper.

Maps Tavily's response shape to ResearchPipe's schema (consistent with PRD/EDD).
"""
from __future__ import annotations

import time
from typing import Any

import asyncio

import httpx

from .settings import TAVILY_API_KEY


async def _retry_async(fn, *args, attempts: int = 3, base_wait: float = 1.0, **kwargs):
    """Simple async retry: exponential backoff up to `attempts` times."""
    last_exc = None
    for i in range(attempts):
        try:
            return await fn(*args, **kwargs)
        except Exception as e:
            last_exc = e
            if i == attempts - 1:
                raise
            await asyncio.sleep(base_wait * (2**i))
    if last_exc:
        raise last_exc
    raise RuntimeError("unreachable")

BASE_URL = "https://api.tavily.com"
TIMEOUT = 60.0


def _headers() -> dict:
    return {"Authorization": f"Bearer {TAVILY_API_KEY}", "Content-Type": "application/json"}


async def search(
    query: str,
    *,
    type_: str = "research",
    search_depth: str = "basic",
    max_results: int = 20,
    include_answer: bool | str = False,
    include_raw_content: bool = False,
    time_range: str | None = None,
    regions: list[str] | None = None,
) -> dict[str, Any]:
    """Wraps POST https://api.tavily.com/search.

    Returns Tavily's raw JSON. Caller is responsible for shaping into ResearchPipe schema.
    """
    body: dict[str, Any] = {
        "query": query,
        "search_depth": search_depth,
        "max_results": max_results,
        "include_raw_content": include_raw_content,
    }
    if include_answer:
        body["include_answer"] = include_answer
    if time_range:
        body["days"] = _time_range_to_days(time_range)
    async def _do():
        async with httpx.AsyncClient(timeout=TIMEOUT) as cli:
            r = await cli.post(f"{BASE_URL}/search", headers=_headers(), json=body)
            r.raise_for_status()
            return r.json()

    return await _retry_async(_do)


def _time_range_to_days(t: str) -> int:
    # naive: "7d" -> 7, "30d" -> 30, "6m" -> 180, "12m" -> 365, "24m" -> 730
    t = t.strip().lower()
    if t.endswith("d"):
        return int(t[:-1])
    if t.endswith("m"):
        return int(t[:-1]) * 30
    if t.endswith("y"):
        return int(t[:-1]) * 365
    return 30


async def extract(
    urls: list[str] | str,
    *,
    extract_depth: str = "advanced",
    include_images: bool = False,
) -> dict[str, Any]:
    """Wraps POST https://api.tavily.com/extract."""
    if isinstance(urls, str):
        urls = [urls]
    body = {
        "urls": urls,
        "extract_depth": extract_depth,
        "include_images": include_images,
    }

    async def _do():
        async with httpx.AsyncClient(timeout=TIMEOUT) as cli:
            r = await cli.post(f"{BASE_URL}/extract", headers=_headers(), json=body)
            r.raise_for_status()
            return r.json()

    return await _retry_async(_do)


def shape_search_results(tavily_resp: dict[str, Any], *, source_filter: list[str] | None = None) -> dict[str, Any]:
    """Transform Tavily results to ResearchPipe /v1/search response schema."""
    started = time.time()
    results = []
    for r in tavily_resp.get("results") or []:
        results.append(
            {
                "title": r.get("title"),
                "url": r.get("url"),
                "snippet": (r.get("content") or "")[:300],
                "content": r.get("content"),
                "score": r.get("score"),
                "published_at": r.get("published_date"),
                "source_type": "web",
                "source_name": _hostname(r.get("url") or ""),
            }
        )
    return {
        "query": tavily_resp.get("query"),
        "answer": tavily_resp.get("answer"),
        "results": results,
        "metadata": {
            "data_sources_used": ["tavily"],
            "total_results": len(results),
            "shaped_in_ms": round((time.time() - started) * 1000, 1),
        },
    }


def _hostname(url: str) -> str:
    from urllib.parse import urlparse

    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""
