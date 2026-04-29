"""Real-data routes — read from qmp_data postgres (192.168.1.23, READ-ONLY).

Falls back to mocks in stub.py if DB is unreachable. Marked `data_sources_used: ["qmp_data"]`
in metadata when real data is returned.
"""
from __future__ import annotations

import secrets
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from .. import db
from ..auth import require_api_key
from ..mocks import ENDPOINT_MOCKS, envelope

router = APIRouter(prefix="/v1", tags=["data"], dependencies=[Depends(require_api_key)])


def _req_id() -> str:
    return f"req_{secrets.token_hex(5)}"


def _md(*, credits: float, sources: list[str], ms: float, partial: bool = False, **extra) -> dict[str, Any]:
    md: dict[str, Any] = {
        "request_id": _req_id(),
        "credits_charged": credits,
        "data_sources_used": sources,
        "wall_time_ms": round(ms, 1),
        "partial": partial,
    }
    md.update(extra)
    return md


def _serialize(o: Any) -> Any:
    """Make asyncpg Records JSON-friendly: Decimal → float, datetime → iso, etc."""
    from datetime import date, datetime
    from decimal import Decimal

    if isinstance(o, dict):
        return {k: _serialize(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_serialize(x) for x in o]
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    return o


# ─────────────────────────────────────────────────────────────────────────
# Companies (real from events)
# ─────────────────────────────────────────────────────────────────────────


@router.post("/companies/search")
async def companies_search_real(body: dict):
    started = time.time()
    try:
        q = body.get("query")
        ind = body.get("industry")
        limit = int(body.get("limit") or 20)
        rows = await db.companies_search(q, ind, limit)
    except Exception:
        return envelope(ENDPOINT_MOCKS["companies-search"], credits=0.5)
    return {
        "total": len(rows),
        "results": _serialize(rows),
        "metadata": _md(credits=0.5, sources=["qmp_data"], ms=(time.time() - started) * 1000),
    }


@router.get("/companies/{cid}")
async def companies_get_real(cid: str):
    started = time.time()
    try:
        # cid 可以是 company_name（字符串）；不支持 numeric id
        row = await db.companies_get(cid)
    except Exception:
        return envelope(ENDPOINT_MOCKS["companies-get"], credits=0.5)
    if row is None:
        # try fuzzy, return up to 5 candidates
        try:
            cands = await db.companies_search(cid, None, 5)
        except Exception:
            cands = []
        if not cands:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "quota_resource_not_found",
                    "message": f"company '{cid}' not found",
                    "hint_for_agent": "Try POST /v1/companies/search with a partial name first.",
                },
            )
        return {
            "candidates": _serialize(cands),
            "metadata": _md(
                credits=0.5,
                sources=["qmp_data"],
                ms=(time.time() - started) * 1000,
                requires_disambiguation=True,
            ),
        }
    payload = _serialize(row)
    payload["metadata"] = _md(credits=0.5, sources=["qmp_data"], ms=(time.time() - started) * 1000)
    return payload


@router.get("/companies/{cid}/deals")
async def companies_deals_real(cid: str):
    started = time.time()
    try:
        rows = await db.company_deals(cid)
    except Exception:
        return envelope(ENDPOINT_MOCKS["companies-deals"], credits=1)
    return {
        "company_name": cid,
        "total": len(rows),
        "results": _serialize(rows),
        "metadata": _md(credits=1, sources=["qmp_data"], ms=(time.time() - started) * 1000),
    }


# ─────────────────────────────────────────────────────────────────────────
# Investors (real)
# ─────────────────────────────────────────────────────────────────────────


@router.post("/investors/search")
async def investors_search_real(body: dict):
    started = time.time()
    try:
        rows = await db.investors_search(body.get("query"), body.get("type"), int(body.get("limit") or 20))
    except Exception:
        return envelope(ENDPOINT_MOCKS["investors-search"], credits=0.5)
    return {
        "total": len(rows),
        "results": _serialize(rows),
        "metadata": _md(credits=0.5, sources=["qmp_data"], ms=(time.time() - started) * 1000),
    }


@router.get("/investors/{iid}")
async def investors_get_real(iid: str):
    started = time.time()
    try:
        # iid is institution_id (int)
        row = await db.investors_get(int(iid))
    except (ValueError, Exception):
        return envelope(ENDPOINT_MOCKS["investors-get"], credits=0.5)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "quota_resource_not_found",
                "message": f"investor {iid} not found",
                "hint_for_agent": "Use /v1/investors/search to find institution_id first.",
            },
        )
    payload = _serialize(row)
    payload["metadata"] = _md(credits=0.5, sources=["qmp_data"], ms=(time.time() - started) * 1000)
    return payload


@router.get("/investors/{iid}/portfolio")
async def investors_portfolio_real(iid: str):
    started = time.time()
    try:
        rows = await db.investor_portfolio(int(iid), 50)
    except (ValueError, Exception):
        return envelope(ENDPOINT_MOCKS["investors-portfolio"], credits=1)
    return {
        "institution_id": int(iid),
        "total": len(rows),
        "results": _serialize(rows),
        "metadata": _md(credits=1, sources=["qmp_data"], ms=(time.time() - started) * 1000),
    }


# ─────────────────────────────────────────────────────────────────────────
# Deals (real)
# ─────────────────────────────────────────────────────────────────────────


@router.post("/deals/search")
async def deals_search_real(body: dict):
    started = time.time()
    try:
        ind = body.get("industry")
        stage = body.get("stage")
        amt = body.get("amount_min")
        time_range = body.get("time_range") or "365d"
        days = int(time_range.rstrip("dDmM")) if time_range and time_range[-1] in "dD" else 365
        if time_range and time_range[-1] in "mM":
            days = int(time_range.rstrip("mM")) * 30
        result = await db.deals_search(ind, stage, float(amt) if amt else None, days, int(body.get("limit") or 20))
    except Exception as e:
        return envelope({**ENDPOINT_MOCKS["deals-search"], "error_hint": str(e)[:80]}, credits=1)
    return {
        "total": result["total"],
        "results": _serialize(result["items"]),
        "metadata": _md(credits=1, sources=["qmp_data"], ms=(time.time() - started) * 1000),
    }


@router.get("/deals/{did}")
async def deals_get_real(did: str):
    started = time.time()
    try:
        row = await db.deal_get(int(did))
    except (ValueError, Exception):
        return envelope(ENDPOINT_MOCKS["deals-get"], credits=0.5)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "quota_resource_not_found",
                "message": f"deal {did} not found",
                "hint_for_agent": "Use /v1/deals/search to discover event_ids first.",
            },
        )
    payload = _serialize(row)
    payload["metadata"] = _md(credits=0.5, sources=["qmp_data"], ms=(time.time() - started) * 1000)
    return payload


# ─────────────────────────────────────────────────────────────────────────
# Valuations (real)
# ─────────────────────────────────────────────────────────────────────────


@router.post("/valuations/search")
async def valuations_search_real(body: dict):
    started = time.time()
    try:
        rows = await db.valuations_search(body.get("industry"), body.get("stage"), int(body.get("limit") or 20))
    except Exception:
        return envelope(ENDPOINT_MOCKS["valuations-search"], credits=1)
    return {
        "total": len(rows),
        "results": _serialize(rows),
        "metadata": _md(credits=1, sources=["qmp_data"], ms=(time.time() - started) * 1000),
    }


@router.post("/valuations/multiples")
async def valuations_multiples_real(body: dict):
    started = time.time()
    ind = (body or {}).get("industry")
    if not ind:
        # Falling back to mock — no industry filter means we can't compute meaningfully
        return envelope(ENDPOINT_MOCKS["valuations-multiples"], credits=1)
    try:
        row = await db.valuations_multiples(ind)
    except HTTPException:
        raise
    except Exception:
        return envelope(ENDPOINT_MOCKS["valuations-multiples"], credits=1)
    if row is None:
        return envelope(
            {"industry": body.get("industry"), "ps_median": None, "n": 0, "warning": "no records"}, credits=1
        )
    payload = _serialize(row)
    payload["metadata"] = _md(credits=1, sources=["qmp_data"], ms=(time.time() - started) * 1000)
    return payload


# ─────────────────────────────────────────────────────────────────────────
# Industries (real, derived from events)
# ─────────────────────────────────────────────────────────────────────────


@router.post("/industries/search")
async def industries_search_real(body: dict):
    started = time.time()
    try:
        rows = await db.industries_search(body.get("query") or "")
    except Exception:
        return envelope(ENDPOINT_MOCKS["industries-search"], credits=0.5)
    return {
        "results": _serialize(rows),
        "metadata": _md(credits=0.5, sources=["qmp_data"], ms=(time.time() - started) * 1000),
    }


@router.get("/industries/{ind}/deals")
async def industries_deals_real(ind: str):
    started = time.time()
    try:
        result = await db.industry_deals(ind, 365)
    except Exception:
        return envelope(ENDPOINT_MOCKS["industries-deals"], credits=1)
    return {
        **_serialize(result),
        "metadata": _md(credits=1, sources=["qmp_data"], ms=(time.time() - started) * 1000),
    }


@router.get("/industries/{ind}/companies")
async def industries_companies_real(ind: str):
    started = time.time()
    try:
        rows = await db.industry_companies(ind, 50)
    except Exception:
        return envelope(ENDPOINT_MOCKS["industries-companies"], credits=1)
    return {
        "industry": ind,
        "total": len(rows),
        "results": _serialize(rows),
        "metadata": _md(credits=1, sources=["qmp_data"], ms=(time.time() - started) * 1000),
    }
