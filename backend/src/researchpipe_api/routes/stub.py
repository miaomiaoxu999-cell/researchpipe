"""Stub routes for the remaining 47 endpoints — return mock data with the proper envelope.

Each stub uses uniform metadata: request_id, credits_charged, data_sources_used, partial.
Routes documented to match PRD ch6.2-6.6.
"""
from __future__ import annotations

import secrets
import time
from typing import Any

from fastapi import APIRouter, Depends

from ..auth import require_api_key
from ..mocks import ENDPOINT_MOCKS, envelope
from ..schemas import (
    BillingResponse,
    GenericEnvelope,
    JobAccepted,
    JobResult,
    MeResponse,
    ResearchCompanyRequest,
    ResearchSectorRequest,
    ResearchValuationRequest,
    UsageResponse,
)

router = APIRouter(prefix="/v1", tags=["stub"], dependencies=[Depends(require_api_key)])

_req_id = lambda: f"req_{secrets.token_hex(5)}"


# Async job registry — in-memory, M1 stub only. M2 swaps to Redis/BullMQ.
_JOBS: dict[str, dict[str, Any]] = {}


async def _new_job_persisted(kind: str, payload: dict[str, Any]) -> JobAccepted:
    """Create a job in SQLite + immediately mark complete with the given payload."""
    from .. import storage

    rid = f"req_{secrets.token_hex(8)}"
    await storage.job_create(rid, kind)
    await storage.job_complete(rid, payload)
    return JobAccepted(request_id=rid, status="completed")


def _new_job(kind: str, payload: dict[str, Any]) -> JobAccepted:
    """Sync compatibility shim — still writes to in-memory dict for legacy tests."""
    rid = f"req_{secrets.token_hex(8)}"
    _JOBS[rid] = {
        "request_id": rid,
        "status": "completed",
        "kind": kind,
        "submitted_at": time.time(),
        "result": payload,
    }
    return JobAccepted(request_id=rid, status="completed")


def _stub(endpoint_id: str, *, credits: float = 1) -> dict[str, Any]:
    """Lookup mock + wrap with envelope."""
    payload = ENDPOINT_MOCKS.get(endpoint_id, {"endpoint": endpoint_id, "note": "stub"})
    return envelope(payload, credits=credits)


# ─────────────────────────────────────────────────────────────────────────
# Search line — extract/filing, extract/batch, jobs (search are real in routes/search.py)
# ─────────────────────────────────────────────────────────────────────────


@router.post("/extract/filing")
async def extract_filing(body: dict):
    """Real: Tavily Extract → V4 抽 5 套 schema 之一."""
    from .. import web_combined

    url = body.get("url") or body.get("filing_id") or ""
    schema = body.get("schema") or "prospectus_v1"
    if not url:
        return _stub("filings-extract", credits=3)
    try:
        result = await web_combined.filings_extract(url, schema)
    except Exception:
        return _stub("filings-extract", credits=3)
    return result


@router.post("/extract/batch")
async def extract_batch(body: dict):
    return JobAccepted(request_id=f"req_{secrets.token_hex(8)}", status="pending")


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Read job state — first check SQLite (persistent), fall back to in-memory dict."""
    from .. import storage

    # SQLite first (survives restart)
    try:
        job = await storage.job_get(job_id)
    except Exception:
        job = None

    # In-memory fallback (legacy)
    if job is None:
        job = _JOBS.get(job_id)
        if job is None:
            # Synthesize a generic completed job for unknown ids (M1 stub behavior)
            return JobResult(
                request_id=job_id,
                status="completed",
                result={"note": "stub job result"},
                metadata={"credits_charged": 0, "data_sources_used": []},
            )

    # Normalize result/error shape (SQLite returns dict with result/error already parsed)
    return JobResult(
        request_id=job.get("request_id", job_id),
        status=job.get("status", "completed"),
        result=job.get("result"),
        error=job.get("error"),
        metadata={
            "kind": job.get("kind"),
            "credits_charged": 0,
            "submitted_at": job.get("submitted_at"),
            "completed_at": job.get("completed_at"),
        },
    )


# ─────────────────────────────────────────────────────────────────────────
# Research line — sector / company / valuation (async, mock immediate-complete)
# ─────────────────────────────────────────────────────────────────────────


@router.post("/research/sector", response_model=JobAccepted)
async def research_sector(req: ResearchSectorRequest):
    """Real orchestrator: Tavily Search → 5 Tavily Extract → V4 抽 11 字段 → V4 合成 16 字段."""
    import asyncio

    from ..research_sector import run_sector_research

    from .. import storage

    rid = f"req_{secrets.token_hex(8)}"
    await storage.job_create(rid, "sector")
    _JOBS[rid] = {"request_id": rid, "status": "running", "kind": "sector"}  # in-memory shadow

    async def _bg():
        try:
            result = await run_sector_research(req.input, time_range=req.time_range)
            await storage.job_complete(rid, result)
            _JOBS[rid] = {"request_id": rid, "status": "completed", "kind": "sector", "result": result}
        except Exception as e:
            err = {"message": str(e)[:200], "hint_for_agent": "Retry; or use /v1/research/company instead."}
            await storage.job_fail(rid, err)
            _JOBS[rid] = {"request_id": rid, "status": "failed", "kind": "sector", "error": err}

    asyncio.create_task(_bg())
    return JobAccepted(request_id=rid, status="running")


@router.post("/research/company", response_model=JobAccepted)
async def research_company(req: ResearchCompanyRequest):
    """Real orchestrator: Tavily + qmp_data → V4 合成 16 字段公司尽调."""
    import asyncio

    from ..research_sector import run_company_research

    from .. import storage

    rid = f"req_{secrets.token_hex(8)}"
    await storage.job_create(rid, "company")
    _JOBS[rid] = {"request_id": rid, "status": "running", "kind": "company"}

    async def _bg():
        try:
            result = await run_company_research(req.input, focus=req.focus)
            await storage.job_complete(rid, result)
            _JOBS[rid] = {"request_id": rid, "status": "completed", "kind": "company", "result": result}
        except Exception as e:
            err = {"message": str(e)[:200]}
            await storage.job_fail(rid, err)
            _JOBS[rid] = {"request_id": rid, "status": "failed", "kind": "company", "error": err}

    asyncio.create_task(_bg())
    return JobAccepted(request_id=rid, status="running")


@router.post("/research/valuation", response_model=JobAccepted)
async def research_valuation(req: ResearchValuationRequest):
    """Real orchestrator: qmp valuations + Tavily → V4 估值锚 schema."""
    import asyncio

    from ..research_sector import run_valuation_research

    from .. import storage

    rid = f"req_{secrets.token_hex(8)}"
    await storage.job_create(rid, "valuation")
    _JOBS[rid] = {"request_id": rid, "status": "running", "kind": "valuation"}

    async def _bg():
        try:
            result = await run_valuation_research(req.input, regions=req.regions)
            await storage.job_complete(rid, result)
            _JOBS[rid] = {"request_id": rid, "status": "completed", "kind": "valuation", "result": result}
        except Exception as e:
            err = {"message": str(e)[:200]}
            await storage.job_fail(rid, err)
            _JOBS[rid] = {"request_id": rid, "status": "failed", "kind": "valuation", "error": err}

    asyncio.create_task(_bg())
    return JobAccepted(request_id=rid, status="running")


# ─────────────────────────────────────────────────────────────────────────
# Data — Companies (6)
# ─────────────────────────────────────────────────────────────────────────


@router.post("/companies/search")
async def companies_search(body: dict):
    return _stub("companies-search", credits=0.5)


@router.get("/companies/{cid}")
async def companies_get(cid: str):
    return _stub("companies-get", credits=0.5)


@router.get("/companies/{cid}/deals")
async def companies_deals(cid: str):
    return _stub("companies-deals", credits=1)


@router.post("/companies/{cid}/peers")
async def companies_peers(cid: str, body: dict):
    return _stub("companies-peers", credits=2)


@router.get("/companies/{cid}/news")
async def companies_news(cid: str):
    return _stub("companies-news", credits=1)


@router.get("/companies/{cid}/founders")
async def companies_founders(cid: str, deep: bool = False):
    return _stub("companies-founders", credits=3 if deep else 1)


# ─────────────────────────────────────────────────────────────────────────
# Data — Investors (5)
# ─────────────────────────────────────────────────────────────────────────


@router.post("/investors/search")
async def investors_search(body: dict):
    return _stub("investors-search", credits=0.5)


@router.get("/investors/{iid}")
async def investors_get(iid: str):
    return _stub("investors-get", credits=0.5)


@router.get("/investors/{iid}/portfolio")
async def investors_portfolio(iid: str):
    return _stub("investors-portfolio", credits=1)


@router.get("/investors/{iid}/preferences")
async def investors_preferences(iid: str):
    return _stub("investors-preferences", credits=0.5)


@router.get("/investors/{iid}/exits")
async def investors_exits(iid: str):
    return _stub("investors-exits", credits=1)


# ─────────────────────────────────────────────────────────────────────────
# Data — Deals (5)
# ─────────────────────────────────────────────────────────────────────────


@router.post("/deals/search")
async def deals_search(body: dict):
    return _stub("deals-search", credits=1)


@router.get("/deals/{did}")
async def deals_get(did: str):
    return _stub("deals-get", credits=0.5)


@router.post("/deals/timeline")
async def deals_timeline(body: dict):
    return _stub("deals-timeline", credits=2)


@router.post("/deals/overseas")
async def deals_overseas(body: dict):
    return _stub("deals-overseas", credits=2)


@router.get("/deals/{did}/co_investors")
async def deals_co_investors(did: str):
    return _stub("deals-co-investors", credits=2)


# ─────────────────────────────────────────────────────────────────────────
# Data — Industries (9)
# ─────────────────────────────────────────────────────────────────────────


@router.post("/industries/search")
async def industries_search(body: dict):
    return _stub("industries-search", credits=0.5)


@router.get("/industries/{ind}/deals")
async def industries_deals(ind: str):
    return _stub("industries-deals", credits=1)


@router.get("/industries/{ind}/companies")
async def industries_companies(ind: str):
    return _stub("industries-companies", credits=1)


@router.get("/industries/{ind}/chain")
async def industries_chain(ind: str):
    return _stub("industries-chain", credits=2)


@router.get("/industries/{ind}/policies")
async def industries_policies(ind: str):
    return _stub("industries-policies", credits=1)


@router.get("/industries/{ind}/tech_roadmap")
async def industries_tech_roadmap(ind: str):
    return _stub("industries-tech-roadmap", credits=3)


@router.get("/industries/{ind}/key_technologies")
async def industries_key_tech(ind: str):
    return _stub("industries-key-tech", credits=2)


@router.post("/industries/{ind}/maturity")
async def industries_maturity(ind: str, body: dict):
    return _stub("industries-maturity", credits=5)


@router.post("/technologies/compare")
async def technologies_compare(body: dict):
    return _stub("technologies-compare", credits=5)


# ─────────────────────────────────────────────────────────────────────────
# Data — Valuations (4)
# ─────────────────────────────────────────────────────────────────────────


@router.post("/valuations/search")
async def valuations_search(body: dict):
    return _stub("valuations-search", credits=1)


@router.post("/valuations/multiples")
async def valuations_multiples(body: dict):
    return _stub("valuations-multiples", credits=1)


@router.post("/valuations/compare")
async def valuations_compare(body: dict):
    return _stub("valuations-compare", credits=3)


@router.post("/valuations/distribution")
async def valuations_distribution(body: dict):
    return _stub("valuations-distribution", credits=2)


# ─────────────────────────────────────────────────────────────────────────
# Data — Filings (5) — extract is in stub above for now
# ─────────────────────────────────────────────────────────────────────────


@router.post("/filings/search")
async def filings_search(body: dict):
    return _stub("filings-search", credits=0.5)


@router.get("/filings/{fid}")
async def filings_get(fid: str):
    return _stub("filings-get", credits=0.5)


@router.post("/filings/{fid}/extract")
async def filings_extract(fid: str, body: dict):
    return _stub("filings-extract", credits=3)


@router.post("/filings/{fid}/risks")
async def filings_risks(fid: str, body: dict):
    return _stub("filings-risks", credits=2)


@router.post("/filings/{fid}/financials")
async def filings_financials(fid: str, body: dict):
    return _stub("filings-financials", credits=2)


# ─────────────────────────────────────────────────────────────────────────
# Data — News & Events (3)
# ─────────────────────────────────────────────────────────────────────────


@router.post("/news/search")
async def news_search(body: dict):
    return _stub("news-search", credits=1)


@router.post("/news/recent")
async def news_recent(body: dict):
    return _stub("news-recent", credits=0.5)


@router.post("/events/timeline")
async def events_timeline(body: dict):
    return _stub("events-timeline", credits=2)


# ─────────────────────────────────────────────────────────────────────────
# Data — Tasks (1)
# ─────────────────────────────────────────────────────────────────────────


@router.post("/screen")
async def screen(body: dict):
    return _stub("screen", credits=5)


# ─────────────────────────────────────────────────────────────────────────
# Watch (2)
# ─────────────────────────────────────────────────────────────────────────


@router.post("/watch/create")
async def watch_create(body: dict):
    return _stub("watch-create", credits=0)


@router.get("/watch/{wid}/digest")
async def watch_digest(wid: str):
    return _stub("watch-digest", credits=10)


# ─────────────────────────────────────────────────────────────────────────
# Account (3)
# ─────────────────────────────────────────────────────────────────────────


@router.get("/me", response_model=MeResponse)
async def me():
    return MeResponse(**ENDPOINT_MOCKS["me"])


@router.get("/usage", response_model=UsageResponse)
async def usage():
    return UsageResponse(items=ENDPOINT_MOCKS["usage"]["items"])


@router.get("/billing", response_model=BillingResponse)
async def billing():
    return BillingResponse(**ENDPOINT_MOCKS["billing"])
