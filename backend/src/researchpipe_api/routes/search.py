"""Real Tavily-backed routes: /v1/search, /v1/extract, /v1/extract/research."""
from __future__ import annotations

import secrets
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from .. import tavily as tavily_client
from ..auth import require_api_key
from ..extract_research_prompt import build_messages
from ..llm import chat_json
from ..schemas import (
    ExtractRequest,
    ExtractResearchOutput,
    ExtractResearchRequest,
    ExtractResearchResponse,
    ExtractResponse,
    SearchRequest,
    SearchResponse,
)

router = APIRouter(prefix="/v1", tags=["search"], dependencies=[Depends(require_api_key)])


def _req_id() -> str:
    return f"req_{secrets.token_hex(5)}"


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    started = time.time()

    # multi_source=true → 套壳组合层（Tavily + Bocha + Serper 并发 + 去重 + 排序）
    if req.multi_source:
        from .. import multi_search

        shaped = await multi_search.combined_search(
            req.query,
            max_results=req.max_results,
            languages=req.languages,
            search_depth=req.search_depth,
        )
        shaped["metadata"]["request_id"] = _req_id()
        shaped["metadata"]["credits_charged"] = 2 if req.search_depth == "basic" else 3
        return shaped

    # 单源 Tavily（默认，最快）
    try:
        tavily_resp = await tavily_client.search(
            req.query,
            type_=req.type,
            search_depth=req.search_depth,
            max_results=req.max_results,
            include_answer=req.include_answer if req.include_answer else False,
            include_raw_content=req.include_raw_content,
            time_range=req.time_range,
            regions=req.regions,
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "upstream_failure",
                "message": f"Tavily request failed: {type(e).__name__}",
                "hint_for_agent": "Retry in a few seconds; or pass `multi_source: true` to fan out to Bocha + Serper as fallback.",
                "documentation_url": "https://rp.zgen.xin/docs/errors/upstream_failure",
            },
        )

    shaped = tavily_client.shape_search_results(tavily_resp)
    shaped["metadata"]["request_id"] = _req_id()
    shaped["metadata"]["credits_charged"] = 1 if req.search_depth == "basic" else 2
    shaped["metadata"]["wall_time_ms"] = round((time.time() - started) * 1000, 1)
    shaped["metadata"]["data_sources_used"] = ["tavily"]
    return shaped


@router.post("/extract", response_model=ExtractResponse)
async def extract(req: ExtractRequest):
    started = time.time()
    try:
        resp = await tavily_client.extract(
            req.url,
            extract_depth=req.extract_depth,
            include_images=req.include_images,
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "upstream_failure",
                "message": f"Tavily extract failed: {type(e).__name__}",
                "hint_for_agent": "Verify the URL is publicly accessible; some sites block crawlers.",
                "documentation_url": "https://rp.zgen.xin/docs/errors/upstream_failure",
            },
        )

    results = resp.get("results") or []
    if not results:
        return ExtractResponse(
            url=req.url,
            content=None,
            metadata={
                "request_id": _req_id(),
                "credits_charged": 2,
                "data_sources_used": ["tavily"],
                "warnings": [
                    {
                        "code": "extract_empty",
                        "source": "tavily",
                        "message": "Tavily returned no extracted content",
                        "hint_for_agent": "Try /v1/search first to find a different URL, or use a different extract_depth.",
                    }
                ],
            },
        )

    item = results[0]
    return ExtractResponse(
        url=req.url,
        title=item.get("title"),
        content=item.get("raw_content"),
        images=item.get("images"),
        metadata={
            "request_id": _req_id(),
            "credits_charged": 2 if req.extract_depth == "basic" else 5,
            "data_sources_used": ["tavily"],
            "wall_time_ms": round((time.time() - started) * 1000, 1),
        },
    )


@router.post("/extract/research", response_model=ExtractResearchResponse)
async def extract_research(req: ExtractResearchRequest):
    started = time.time()
    # Step 1: pull full text via Tavily Extract
    try:
        ext = await tavily_client.extract(req.url, extract_depth="advanced")
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "upstream_failure",
                "message": f"Tavily extract failed: {type(e).__name__}",
                "hint_for_agent": "Verify URL accessibility.",
            },
        )

    items = ext.get("results") or []
    if not items or not items[0].get("raw_content"):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "extract_empty",
                "message": "Could not extract any content from the URL",
                "hint_for_agent": "The URL may be JS-rendered or behind a login. Try /v1/search to find an alternative source.",
            },
        )

    full_text = items[0]["raw_content"]
    title_hint = items[0].get("title", "")

    # Truncate very long inputs to keep latency / cost bounded
    if len(full_text) > 80000:
        full_text = full_text[:80000]

    # Step 2: LLM extract 11 fields
    sys_msg, user_msg = build_messages(full_text=full_text, source_url=req.url, hint_title=title_hint)
    parsed, usage = chat_json(sys_msg, user_msg, max_tokens=8000)

    # Step 3: schema validate (try, but don't hard-fail)
    extraction: ExtractResearchOutput | None = None
    schema_warnings: list[dict[str, Any]] = []
    try:
        extraction = ExtractResearchOutput.model_validate(parsed)
    except Exception as e:
        schema_warnings.append(
            {
                "code": "schema_validation_partial",
                "source": "llm",
                "message": str(e)[:300],
                "hint_for_agent": "The LLM output didn't fully conform to the 11-field schema. Inspect raw `extraction` field; consider re-running with a more capable model.",
            }
        )

    metadata: dict[str, Any] = {
        "request_id": _req_id(),
        "credits_charged": 5,
        "data_sources_used": ["tavily", "deepseek-v4"],
        "model": usage.get("model"),
        "wall_time_ms": round((time.time() - started) * 1000, 1),
        "tokens": {
            "input": usage.get("prompt_tokens"),
            "output": usage.get("completion_tokens"),
            "total": usage.get("total_tokens"),
        },
        "partial": bool(schema_warnings),
    }
    if schema_warnings:
        metadata["warnings"] = schema_warnings

    # Convert pydantic model to dict (if validated) so the response keeps a uniform type.
    extraction_dict: dict[str, Any] | None = None
    if extraction is not None:
        extraction_dict = extraction.model_dump()
    elif isinstance(parsed, dict):
        extraction_dict = parsed
    return ExtractResearchResponse(
        extraction=extraction_dict,
        metadata=metadata,
        raw_content=(full_text[:5000] + "...[truncated]") if req.include_raw_content else None,
    )
