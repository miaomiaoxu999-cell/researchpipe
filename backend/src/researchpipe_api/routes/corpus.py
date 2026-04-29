"""v1/corpus/* — 2026 研报合集 metadata search."""
from __future__ import annotations

import time
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from .. import corpus_db, siliconflow
from ..auth import require_api_key

router = APIRouter(prefix="/v1/corpus", tags=["corpus"], dependencies=[Depends(require_api_key)])


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError as e:
        raise HTTPException(400, f"invalid date '{s}': {e}")


@router.post("/search")
async def corpus_search(body: dict):
    """Search 2026 research-report corpus metadata.

    Body:
        query:        str  — title fuzzy match (trigram + ILIKE)
        broker:       str  — exact broker name e.g. "中信建投"
        industry:     str  — alias key e.g. "具身智能" (auto-expanded via aliases)
        week:         str  — e.g. "2026-1-2"
        library:      str  — substring of library name e.g. "重点报告"
        date_from:    str  — ISO date e.g. "2026-01-01"
        date_to:      str  — ISO date
        limit:        int  — default 20, max 100
        offset:       int  — default 0
    """
    started = time.time()
    limit = min(int(body.get("limit") or 20), 100)
    offset = max(int(body.get("offset") or 0), 0)
    res = await corpus_db.corpus_search(
        query=body.get("query"),
        broker=body.get("broker"),
        industry=body.get("industry"),
        week=body.get("week"),
        library=body.get("library"),
        date_from=_parse_date(body.get("date_from")),
        date_to=_parse_date(body.get("date_to")),
        limit=limit,
        offset=offset,
    )
    elapsed = round((time.time() - started) * 1000, 1)
    return {
        "total": res["total"],
        "results": res["results"],
        "metadata": {
            "data_sources_used": ["corpus_2026"],
            "wall_time_ms": elapsed,
            "credits_charged": 0,
            "limit": limit,
            "offset": offset,
        },
    }


@router.post("/semantic_search")
async def corpus_semantic_search(body: dict):
    """Semantic search corpus chunks via bge-m3 embedding + bge-reranker-v2-m3.

    Body:
        query:        str (required) — natural-language question
        top_n:        int  — final reranked results (default 15, max 30)
        candidate_k:  int  — pre-rerank candidates to fetch (default 50, max 100)
        industry:     str  — filter by industry alias
        broker:       str  — filter by broker
        week:         str  — filter by week '2026-1-2'
    """
    started = time.time()
    query = (body.get("query") or "").strip()
    if not query:
        raise HTTPException(400, "query required")
    top_n = min(int(body.get("top_n") or 15), 30)
    candidate_k = min(int(body.get("candidate_k") or 50), 100)

    t_embed = time.time()
    q_emb = await siliconflow.embed_query(query)
    embed_ms = round((time.time() - t_embed) * 1000, 1)

    t_ann = time.time()
    candidates = await corpus_db.semantic_search(
        q_emb,
        candidate_top_k=candidate_k,
        industry=body.get("industry"),
        broker=body.get("broker"),
        week=body.get("week"),
    )
    ann_ms = round((time.time() - t_ann) * 1000, 1)

    if not candidates:
        return {
            "total": 0,
            "results": [],
            "metadata": {
                "data_sources_used": ["corpus_2026"],
                "wall_time_ms": round((time.time() - started) * 1000, 1),
                "credits_charged": 0.5,
                "phases_ms": {"embed": embed_ms, "ann": ann_ms, "rerank": 0},
            },
        }

    # Rerank
    t_rer = time.time()
    docs = [c["content"] for c in candidates]
    try:
        ranked = await siliconflow.rerank(query, docs, top_n=top_n)
        # Reorder candidates by rerank result
        results = []
        for r in ranked:
            c = candidates[r["index"]]
            c["rerank_score"] = r["relevance_score"]
            results.append(c)
        rerank_ms = round((time.time() - t_rer) * 1000, 1)
    except Exception as e:
        # Fall back to ANN order if rerank fails
        results = candidates[:top_n]
        for r in results:
            r["rerank_score"] = None
        rerank_ms = -1

    # Trim content for response (full text in `content_full` if needed)
    for r in results:
        r["content_preview"] = r["content"][:300]

    # Quality warning: if top rerank is below threshold, corpus may not have relevant content.
    MIN_RERANK_GOOD = 0.05
    top_rerank = max((r.get("rerank_score") or 0) for r in results) if results else 0
    warnings: list[dict] = []
    if rerank_ms != -1 and results and top_rerank < MIN_RERANK_GOOD:
        warnings.append({
            "code": "no_good_match",
            "max_rerank_score": round(top_rerank, 4),
            "threshold": MIN_RERANK_GOOD,
            "message": f"Top rerank score {top_rerank:.3f} is below threshold {MIN_RERANK_GOOD} — corpus likely lacks content for this query.",
            "hint_for_agent": "Do not synthesize an answer from these results — they're likely off-topic. Tell the user to rephrase or note that the 2026 research corpus does not cover this topic.",
        })

    md = {
        "data_sources_used": ["corpus_2026"],
        "wall_time_ms": round((time.time() - started) * 1000, 1),
        "credits_charged": 0.5,
        "phases_ms": {"embed": embed_ms, "ann": ann_ms, "rerank": rerank_ms},
        "rerank_failed": rerank_ms == -1,
        "max_rerank_score": round(top_rerank, 4),
    }
    if warnings:
        md["warnings"] = warnings

    return {"total": len(results), "results": results, "metadata": md}


@router.get("/stats")
async def corpus_stats():
    """Aggregate distribution: brokers / industries / weeks / libraries."""
    started = time.time()
    s = await corpus_db.corpus_stats()
    s["metadata"] = {
        "data_sources_used": ["corpus_2026"],
        "wall_time_ms": round((time.time() - started) * 1000, 1),
        "credits_charged": 0,
    }
    return s
