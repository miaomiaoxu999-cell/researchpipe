"""Multi-source search: Tavily + Bocha + Serper 3 路并发 → 去重 → 加权排序.

战略：M1 起 search 端点的 `multi_source: true` 模式（默认 false 单源 Tavily 走原路）
- Tavily: 中英通吃，score 高
- Bocha:  中文站点深度，海外覆盖弱
- Serper: Google 海外结果，国内站点弱
"""
from __future__ import annotations

import asyncio
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from .settings import BOCHA_API_KEY, SERPER_API_KEY, TAVILY_API_KEY
from .tavily import search as tavily_search


TIMEOUT = 30.0


# ─────────────────────────────────────────────────────────────────────────
# Bocha (中文)
# ─────────────────────────────────────────────────────────────────────────


async def bocha_search(query: str, *, count: int = 10) -> list[dict[str, Any]]:
    """Wraps POST https://api.bochaai.com/v1/web-search."""
    if not BOCHA_API_KEY:
        return []
    async with httpx.AsyncClient(timeout=TIMEOUT) as cli:
        try:
            r = await cli.post(
                "https://api.bochaai.com/v1/web-search",
                headers={"Authorization": f"Bearer {BOCHA_API_KEY}", "Content-Type": "application/json"},
                json={"query": query, "freshness": "noLimit", "summary": True, "count": count},
            )
            r.raise_for_status()
        except Exception:
            return []
    body = r.json() or {}
    web_pages = ((body.get("data") or {}).get("webPages") or {}).get("value") or []
    return [
        {
            "title": x.get("name"),
            "url": x.get("url"),
            "snippet": (x.get("summary") or x.get("snippet") or "")[:300],
            "content": x.get("summary") or x.get("snippet"),
            "score": None,
            "published_at": x.get("datePublished"),
            "source_type": "web",
            "source_name": _hostname(x.get("url") or ""),
            "providers": "bocha",
        }
        for x in web_pages
    ]


# ─────────────────────────────────────────────────────────────────────────
# Serper (Google)
# ─────────────────────────────────────────────────────────────────────────


async def serper_search(query: str, *, num: int = 10, gl: str = "cn", hl: str = "zh-cn") -> list[dict[str, Any]]:
    if not SERPER_API_KEY:
        return []
    async with httpx.AsyncClient(timeout=TIMEOUT) as cli:
        try:
            r = await cli.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
                json={"q": query, "num": num, "gl": gl, "hl": hl},
            )
            r.raise_for_status()
        except Exception:
            return []
    body = r.json() or {}
    organic = body.get("organic") or []
    return [
        {
            "title": x.get("title"),
            "url": x.get("link"),
            "snippet": (x.get("snippet") or "")[:300],
            "content": x.get("snippet"),
            "score": None,
            "published_at": x.get("date"),
            "source_type": "web",
            "source_name": _hostname(x.get("link") or ""),
            "providers": "serper",
        }
        for x in organic
    ]


# ─────────────────────────────────────────────────────────────────────────
# Tavily wrapper that returns same shape
# ─────────────────────────────────────────────────────────────────────────


async def tavily_search_normalized(query: str, *, max_results: int = 10, search_depth: str = "basic") -> list[dict[str, Any]]:
    if not TAVILY_API_KEY:
        return []
    try:
        resp = await tavily_search(query, search_depth=search_depth, max_results=max_results)
    except Exception:
        return []
    items = []
    for r in resp.get("results") or []:
        items.append(
            {
                "title": r.get("title"),
                "url": r.get("url"),
                "snippet": (r.get("content") or "")[:300],
                "content": r.get("content"),
                "score": r.get("score"),
                "published_at": r.get("published_date"),
                "source_type": "web",
                "source_name": _hostname(r.get("url") or ""),
                "providers": "tavily",
            }
        )
    return items


# ─────────────────────────────────────────────────────────────────────────
# Combine 3 sources
# ─────────────────────────────────────────────────────────────────────────


def _hostname(url: str) -> str:
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""


def _normalize_url(url: str) -> str:
    """Strip fragment + trailing slash for dedup."""
    if not url:
        return ""
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}{p.path.rstrip('/')}{('?' + p.query) if p.query else ''}"


# Provider weights — higher = trusted more in tie-break
_PROVIDER_WEIGHT = {"tavily": 1.0, "bocha": 0.85, "serper": 0.85}


def _rank_score(items_for_url: list[dict[str, Any]]) -> float:
    """Rank by:
    1. Number of providers hitting same URL (the more, the higher)
    2. Tavily score if present
    3. Provider weight
    """
    n_providers = len({it.get("providers") for it in items_for_url})
    tavily_score = next(
        (it.get("score") for it in items_for_url if it.get("providers") == "tavily" and isinstance(it.get("score"), (int, float))),
        None,
    )
    weight_sum = sum(_PROVIDER_WEIGHT.get(it.get("providers", "?"), 0.5) for it in items_for_url)
    base = n_providers * 1.0 + weight_sum * 0.3
    if tavily_score is not None:
        base += tavily_score * 0.5
    return round(base, 3)


async def combined_search(
    query: str,
    *,
    max_results: int = 20,
    languages: list[str] | None = None,
    search_depth: str = "basic",
) -> dict[str, Any]:
    """3 路并发 + dedup + ranked. Returns ResearchPipe shape."""
    started = time.time()
    languages = languages or ["zh", "en"]
    is_chinese = "zh" in languages
    is_global = "en" in languages

    tasks: list[asyncio.Task] = []
    providers_attempted: list[str] = []

    # Tavily always
    tasks.append(asyncio.create_task(tavily_search_normalized(query, max_results=max_results, search_depth=search_depth)))
    providers_attempted.append("tavily")

    if is_chinese:
        tasks.append(asyncio.create_task(bocha_search(query, count=max_results)))
        providers_attempted.append("bocha")

    if is_global:
        tasks.append(asyncio.create_task(serper_search(query, num=max_results, gl="us" if is_global and not is_chinese else "cn", hl="en" if is_global and not is_chinese else "zh-cn")))
        providers_attempted.append("serper")

    results_per_provider = await asyncio.gather(*tasks, return_exceptions=True)

    all_items: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for provider, result in zip(providers_attempted, results_per_provider):
        if isinstance(result, BaseException):
            warnings.append(
                {
                    "code": "data_source_unavailable",
                    "source": provider,
                    "message": f"{type(result).__name__}: {str(result)[:120]}",
                    "hint_for_agent": f"Result is partial. Other providers (in `data_sources_used`) still returned data.",
                }
            )
            continue
        all_items.extend(result or [])

    # Dedup by normalized URL
    by_url: dict[str, list[dict[str, Any]]] = {}
    for item in all_items:
        u = _normalize_url(item.get("url") or "")
        if not u:
            continue
        by_url.setdefault(u, []).append(item)

    # Merge each group → keep one canonical item, but track which providers hit
    merged: list[dict[str, Any]] = []
    for u, group in by_url.items():
        # canonical = the one with most fields
        canonical = max(group, key=lambda it: len((it.get("content") or "")) + len((it.get("snippet") or "")))
        # Compute rank_score BEFORE mutating canonical (avoid unhashable list bug)
        score = _rank_score(group)
        canonical["providers"] = sorted({str(g.get("providers", "?")) for g in group})
        canonical["rank_score"] = score
        merged.append(canonical)

    # Sort by rank descending
    merged.sort(key=lambda it: it.get("rank_score", 0), reverse=True)
    final = merged[:max_results]

    providers_succeeded = sorted(set().union(*[set(it.get("providers") or []) for it in final])) if final else []

    return {
        "query": query,
        "answer": None,  # multi-source 不合成 answer，由调用方按需做
        "results": final,
        "metadata": {
            "data_sources_used": providers_succeeded or providers_attempted,
            "providers_attempted": providers_attempted,
            "total_results": len(final),
            "raw_results_before_dedup": len(all_items),
            "wall_time_ms": round((time.time() - started) * 1000, 1),
            "warnings": warnings if warnings else None,
            "partial": bool(warnings),
        },
    }
