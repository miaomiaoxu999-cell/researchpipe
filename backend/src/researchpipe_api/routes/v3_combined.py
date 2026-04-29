"""v3 套壳 + 组合层路由 — 把 33 个 mock 端点真化.

注册顺序：main.py 优先注册本路由 → data.py（qmp 真）→ stub.py（mock 兜底）.
FastAPI 第一匹配生效。每个端点有 try/except → fallback 到 mock。
"""
from __future__ import annotations

import secrets
import time
from typing import Any

from fastapi import APIRouter, Depends, Request

from .. import db, multi_search, storage, web_combined
from ..auth import require_api_key
from ..mocks import ENDPOINT_MOCKS, envelope

router = APIRouter(prefix="/v1", tags=["v3"], dependencies=[Depends(require_api_key)])


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


def _ser(o: Any) -> Any:
    return web_combined._ser(o)


# ─────────────────────────────────────────────────────────────────────────
# Filings (4 endpoints) — Tavily Search + Tavily Extract + V4
# ─────────────────────────────────────────────────────────────────────────


@router.post("/filings/search")
async def filings_search_v3(body: dict):
    started = time.time()
    try:
        result = await web_combined.filings_search(
            company_id=body.get("company_id"),
            filing_type=body.get("filing_type"),
            time_range=body.get("time_range") or "24m",
            limit=int(body.get("limit") or 10),
            include_corpus=bool(body.get("include_corpus", False)),
        )
        return result
    except Exception:
        return envelope(ENDPOINT_MOCKS["filings-search"], credits=0.5)


@router.get("/filings/{fid}")
async def filings_get_v3(fid: str):
    return envelope(ENDPOINT_MOCKS["filings-get"], credits=0.5)


@router.post("/filings/{fid}/extract")
async def filings_extract_v3(fid: str, body: dict):
    started = time.time()
    url = body.get("url") or fid
    schema = body.get("schema") or "prospectus_v1"
    try:
        result = await web_combined.filings_extract(url, schema=schema)
        return result
    except Exception:
        return envelope(ENDPOINT_MOCKS["filings-extract"], credits=3)


@router.post("/filings/{fid}/risks")
async def filings_risks_v3(fid: str, body: dict):
    """Subset extraction: extract full prospectus then keep only major_risks field."""
    url = body.get("url") or fid
    try:
        full = await web_combined.filings_extract(url, schema="prospectus_v1")
        risks = (full.get("fields") or {}).get("major_risks") or []
        return {
            "filing_id": fid,
            "risks": [{"level": r.get("category", "?"), "description": r.get("description", "")} for r in risks],
            "metadata": {**(full.get("metadata") or {}), "credits_charged": 2},
        }
    except Exception:
        return envelope(ENDPOINT_MOCKS["filings-risks"], credits=2)


@router.post("/filings/{fid}/financials")
async def filings_financials_v3(fid: str, body: dict):
    url = body.get("url") or fid
    try:
        full = await web_combined.filings_extract(url, schema="prospectus_v1")
        f5y = (full.get("fields") or {}).get("financials_5y_summary") or {}
        return {
            "filing_id": fid,
            "financials_5y": f5y,
            "metadata": {**(full.get("metadata") or {}), "credits_charged": 2},
        }
    except Exception:
        return envelope(ENDPOINT_MOCKS["filings-financials"], credits=2)


# ─────────────────────────────────────────────────────────────────────────
# News (2 endpoints) — multi_search + Tavily news type
# ─────────────────────────────────────────────────────────────────────────


@router.post("/news/search")
async def news_search_v3(body: dict):
    started = time.time()
    query = body.get("query") or "财经新闻"
    time_range = body.get("time_range") or "30d"
    try:
        result = await multi_search.combined_search(
            query=query,
            max_results=int(body.get("limit") or 20),
            languages=body.get("languages") or ["zh", "en"],
            search_depth="basic",
        )
        result["metadata"]["credits_charged"] = 1
        result["metadata"]["request_id"] = _req_id()
        return result
    except Exception:
        return envelope(ENDPOINT_MOCKS["news-search"], credits=1)


@router.post("/news/recent")
async def news_recent_v3(body: dict):
    started = time.time()
    parts = []
    if body.get("industry"):
        parts.append(body["industry"])
    if body.get("company_id"):
        parts.append(body["company_id"])
    query = " ".join(parts) + " 新闻 最新"
    try:
        result = await multi_search.combined_search(
            query=query.strip() or "投资 财经 最新",
            max_results=int(body.get("limit") or 20),
            languages=["zh"],
        )
        result["metadata"]["credits_charged"] = 0.5
        result["metadata"]["request_id"] = _req_id()
        return result
    except Exception:
        return envelope(ENDPOINT_MOCKS["news-recent"], credits=0.5)


# ─────────────────────────────────────────────────────────────────────────
# Industries derivatives (5 endpoints) — V4 synthesis from Tavily search
# ─────────────────────────────────────────────────────────────────────────


@router.get("/industries/{ind}/policies")
async def industries_policies_v3(ind: str):
    schema = """{"industry":"...","policies":[{"title":"...","date":"YYYY-MM-DD","issuing_body":"...","summary":"≤200字","impact_assessment":{"direction":"positive|neutral|negative","intensity":"high|medium|low","time_horizon":"short|medium|long","rationale":"..."}}]}"""
    try:
        result = await web_combined.synthesize_with_search(
            query=f"{ind} 行业 政策 十五五 工信部 发改委 2025 2026",
            schema_description=schema,
            n_search_results=8,
            extract_top_k=0,
            extra_context={"industry": ind},
        )
        if "metadata" in result:
            result["metadata"]["credits_charged"] = 1
        return result
    except Exception:
        return envelope(ENDPOINT_MOCKS["industries-policies"], credits=1)


@router.get("/industries/{ind}/chain")
async def industries_chain_v3(ind: str):
    schema = """{"industry":"...","upstream":["..."],"midstream":["..."],"downstream":["..."],"key_companies_per_layer":{"upstream":[...],"midstream":[...],"downstream":[...]},"summary":"≤200字"}"""
    try:
        result = await web_combined.synthesize_with_search(
            query=f"{ind} 产业链 上中下游 头部公司",
            schema_description=schema,
            n_search_results=6,
            extract_top_k=0,
            extra_context={"industry": ind},
        )
        if "metadata" in result:
            result["metadata"]["credits_charged"] = 2
        return result
    except Exception:
        return envelope(ENDPOINT_MOCKS["industries-chain"], credits=2)


@router.get("/industries/{ind}/tech_roadmap")
async def industries_tech_roadmap_v3(ind: str):
    schema = """{"industry":"...","phases":[{"name":"...","period":"YYYY-YYYY","key_technologies":["..."],"maturity":<0-1>,"milestones":["..."]}],"current_phase":"...","summary":"≤200字"}"""
    try:
        result = await web_combined.synthesize_with_search(
            query=f"{ind} 技术路线图 2026 发展阶段",
            schema_description=schema,
            n_search_results=6,
        )
        if "metadata" in result:
            result["metadata"]["credits_charged"] = 3
        return result
    except Exception:
        return envelope(ENDPOINT_MOCKS["industries-tech-roadmap"], credits=3)


@router.get("/industries/{ind}/key_technologies")
async def industries_key_tech_v3(ind: str):
    schema = """{"industry":"...","technologies":[{"name":"...","description":"...","domestic_rate":<0-1|null>,"key_players":["..."],"bottleneck":"..."}],"summary":"≤200字"}"""
    try:
        result = await web_combined.synthesize_with_search(
            query=f"{ind} 核心技术 国产化率 卡脖子",
            schema_description=schema,
            n_search_results=6,
        )
        if "metadata" in result:
            result["metadata"]["credits_charged"] = 2
        return result
    except Exception:
        return envelope(ENDPOINT_MOCKS["industries-key-tech"], credits=2)


@router.post("/industries/{ind}/maturity")
async def industries_maturity_v3(ind: str, body: dict):
    schema = """{"industry":"...","curve_position":"trigger|peak_of_inflated_expectations|trough_of_disillusionment|slope_of_enlightenment|plateau_of_productivity","estimated_years_to_plateau":<int>,"reasoning":"≤300字","key_indicators":["..."]}"""
    try:
        result = await web_combined.synthesize_with_search(
            query=f"{ind} 技术成熟度 Gartner Hype Cycle 2026",
            schema_description=schema,
            n_search_results=5,
        )
        if "metadata" in result:
            result["metadata"]["credits_charged"] = 5
        return result
    except Exception:
        return envelope(ENDPOINT_MOCKS["industries-maturity"], credits=5)


@router.post("/technologies/compare")
async def technologies_compare_v3(body: dict):
    a = body.get("tech_a") or "技术 A"
    b = body.get("tech_b") or "技术 B"
    schema = """{"tech_a":{"name":"...","strengths":["..."],"weaknesses":["..."],"key_players":["..."]},"tech_b":{"name":"...","strengths":["..."],"weaknesses":["..."],"key_players":["..."]},"comparison_table":[{"dimension":"...","a":"...","b":"...","verdict":"..."}],"verdict":"≤200字 综合判断","outlook":"..."}"""
    try:
        result = await web_combined.synthesize_with_search(
            query=f"{a} vs {b} 技术对比 优劣",
            schema_description=schema,
            n_search_results=8,
            extract_top_k=2,
        )
        if "metadata" in result:
            result["metadata"]["credits_charged"] = 5
        return result
    except Exception:
        return envelope(ENDPOINT_MOCKS["technologies-compare"], credits=5)


# ─────────────────────────────────────────────────────────────────────────
# Companies derivatives (3 endpoints)
# ─────────────────────────────────────────────────────────────────────────


@router.post("/companies/{cid}/peers")
async def companies_peers_v3(cid: str, body: dict):
    started = time.time()
    n = int(body.get("n") or 5)
    try:
        company = await db.companies_get(cid)
        ind = (company or {}).get("industry") or ""
        if not ind:
            return envelope(ENDPOINT_MOCKS["companies-peers"], credits=2)
        # qmp same-industry top n companies
        peers = await db.industry_companies(ind, n + 1)
        peers = [p for p in peers if p.get("company_name") != cid][:n]
        return {
            "company_name": cid,
            "industry": ind,
            "peers": _ser(peers),
            "metadata": _md(credits=2, sources=["qmp_data"], ms=(time.time() - started) * 1000),
        }
    except Exception:
        return envelope(ENDPOINT_MOCKS["companies-peers"], credits=2)


@router.get("/companies/{cid}/news")
async def companies_news_v3(cid: str):
    started = time.time()
    try:
        result = await multi_search.combined_search(
            query=f"{cid} 公司 最新动态",
            max_results=10,
            languages=["zh"],
        )
        result["metadata"]["credits_charged"] = 1
        result["metadata"]["request_id"] = _req_id()
        result["company_name"] = cid
        return result
    except Exception:
        return envelope(ENDPOINT_MOCKS["companies-news"], credits=1)


@router.get("/companies/{cid}/founders")
async def companies_founders_v3(cid: str, deep: bool = False):
    if not deep:
        # 简模式：从 qmp company description 拆出（如有）+ 简短 V4 抽
        started = time.time()
        try:
            comp = await db.companies_get(cid)
            return {
                "company_name": cid,
                "founders": [{"name": "?", "title": "?", "brief": (comp or {}).get("description", "")[:200] if comp else ""}],
                "metadata": _md(credits=1, sources=["qmp_data"], ms=(time.time() - started) * 1000),
            }
        except Exception:
            return envelope(ENDPOINT_MOCKS["companies-founders"], credits=1)

    # deep=True：Tavily Search 创始人 + V4 抽履历
    schema = """{"company":"...","founders":[{"name":"...","title":"...","brief":"...","education":"...","previous_roles":["..."],"controversies":[],"media_links":[]}]}"""
    try:
        result = await web_combined.synthesize_with_search(
            query=f"{cid} 创始人 履历 创业经历",
            schema_description=schema,
            n_search_results=8,
            extract_top_k=2,
        )
        if "metadata" in result:
            result["metadata"]["credits_charged"] = 3
        return result
    except Exception:
        return envelope(ENDPOINT_MOCKS["companies-founders"], credits=3)


# ─────────────────────────────────────────────────────────────────────────
# Deals derivatives (3 endpoints)
# ─────────────────────────────────────────────────────────────────────────


@router.post("/deals/timeline")
async def deals_timeline_v3(body: dict):
    started = time.time()
    company = body.get("company_id") or body.get("company") or ""
    if not company:
        return envelope(ENDPOINT_MOCKS["deals-timeline"], credits=2)
    try:
        events = await db.company_timeline(company)
        return {
            "company_name": company,
            "events": _ser(events),
            "metadata": _md(credits=2, sources=["qmp_data"], ms=(time.time() - started) * 1000),
        }
    except Exception:
        return envelope(ENDPOINT_MOCKS["deals-timeline"], credits=2)


@router.post("/deals/overseas")
async def deals_overseas_v3(body: dict):
    started = time.time()
    industry = body.get("industry") or ""
    country = body.get("country") or "us"
    schema = """{"industry":"...","country":"...","deals":[{"company":"...","amount_usd_m":<num|null>,"stage":"...","date":"YYYY-MM-DD","lead_investors":["..."]}],"summary":"≤200字"}"""
    try:
        result = await web_combined.synthesize_with_search(
            query=f"{industry} {country} venture funding 2025 2026",
            schema_description=schema,
            n_search_results=8,
            extract_top_k=2,
        )
        if "metadata" in result:
            result["metadata"]["credits_charged"] = 2
        return result
    except Exception:
        return envelope(ENDPOINT_MOCKS["deals-overseas"], credits=2)


@router.get("/deals/{did}/co_investors")
async def deals_co_investors_v3(did: str):
    started = time.time()
    try:
        co = await db.deal_co_investors(int(did))
        return {
            "deal_id": did,
            "co_investors": _ser(co),
            "metadata": _md(credits=2, sources=["qmp_data"], ms=(time.time() - started) * 1000),
        }
    except (ValueError, Exception):
        return envelope(ENDPOINT_MOCKS["deals-co-investors"], credits=2)


# ─────────────────────────────────────────────────────────────────────────
# Events / Screen
# ─────────────────────────────────────────────────────────────────────────


@router.post("/events/timeline")
async def events_timeline_v3(body: dict):
    started = time.time()
    company = body.get("company_id") or body.get("company") or ""
    industry = body.get("industry") or ""
    try:
        events: list[dict[str, Any]] = []
        if company:
            for e in await db.company_timeline(company):
                events.append({"date": e.get("investment_date"), "type": "deal", "summary": f"{e.get('round')} {e.get('amount')}"})
        # multi-source news as additional events
        news = await multi_search.combined_search(query=f"{company or industry}", max_results=6, languages=["zh"])
        for n in (news.get("results") or [])[:6]:
            events.append({"date": n.get("published_at"), "type": "news", "summary": n.get("title")})
        return {
            "company_name": company,
            "industry": industry,
            "events": _ser(sorted(events, key=lambda x: str(x.get("date") or ""), reverse=True)),
            "metadata": _md(credits=2, sources=["qmp_data", "tavily"], ms=(time.time() - started) * 1000),
        }
    except Exception:
        return envelope(ENDPOINT_MOCKS["events-timeline"], credits=2)


@router.post("/screen")
async def screen_v3(body: dict):
    started = time.time()
    industry = body.get("industry") or ""
    if not industry:
        return envelope(ENDPOINT_MOCKS["screen"], credits=5)
    try:
        rows = await db.screen_companies(
            industry=industry,
            min_funding_cny_m=body.get("min_funding"),
            stage=body.get("stage"),
            geo=body.get("geo"),
            limit=int(body.get("limit") or 30),
        )
        return {
            "industry": industry,
            "filters": {k: body.get(k) for k in ("min_funding", "stage", "geo")},
            "total": len(rows),
            "results": _ser(rows),
            "metadata": _md(credits=5, sources=["qmp_data"], ms=(time.time() - started) * 1000),
        }
    except Exception:
        return envelope(ENDPOINT_MOCKS["screen"], credits=5)


# ─────────────────────────────────────────────────────────────────────────
# Valuations & Investors derivatives
# ─────────────────────────────────────────────────────────────────────────


@router.post("/valuations/compare")
async def valuations_compare_v3(body: dict):
    started = time.time()
    industry = body.get("industry") or ""
    markets = body.get("markets") or ["a-share", "hk", "us"]
    if not industry:
        return envelope(ENDPOINT_MOCKS["valuations-compare"], credits=3)
    try:
        result = await db.valuations_compare(industry, markets)
        return {
            **_ser(result),
            "metadata": _md(credits=3, sources=["qmp_data"], ms=(time.time() - started) * 1000),
        }
    except Exception:
        return envelope(ENDPOINT_MOCKS["valuations-compare"], credits=3)


@router.post("/valuations/distribution")
async def valuations_distribution_v3(body: dict):
    started = time.time()
    industry = body.get("industry") or ""
    if not industry:
        return envelope(ENDPOINT_MOCKS["valuations-distribution"], credits=2)
    try:
        result = await db.valuations_distribution(industry)
        return {
            **_ser(result),
            "metadata": _md(credits=2, sources=["qmp_data"], ms=(time.time() - started) * 1000),
        }
    except Exception:
        return envelope(ENDPOINT_MOCKS["valuations-distribution"], credits=2)


@router.get("/investors/{iid}/preferences")
async def investors_preferences_v3(iid: str):
    started = time.time()
    try:
        result = await db.investor_preferences(int(iid))
        return {
            **_ser(result),
            "metadata": _md(credits=0.5, sources=["qmp_data"], ms=(time.time() - started) * 1000),
        }
    except (ValueError, Exception):
        return envelope(ENDPOINT_MOCKS["investors-preferences"], credits=0.5)


@router.get("/investors/{iid}/exits")
async def investors_exits_v3(iid: str):
    started = time.time()
    try:
        rows = await db.investor_exits(int(iid))
        return {
            "institution_id": int(iid),
            "results": _ser(rows),
            "metadata": _md(credits=1, sources=["qmp_data"], ms=(time.time() - started) * 1000),
        }
    except (ValueError, Exception):
        return envelope(ENDPOINT_MOCKS["investors-exits"], credits=1)


# ─────────────────────────────────────────────────────────────────────────
# Account (real SQLite)
# ─────────────────────────────────────────────────────────────────────────


@router.get("/me")
async def me_v3(request: Request):
    api_key = getattr(request.state, "api_key", "rp-dev")
    return await storage.account_me(api_key)


@router.get("/usage")
async def usage_v3(request: Request, days: int = 30):
    api_key = getattr(request.state, "api_key", "rp-dev")
    items = await storage.usage_history(api_key, days=days)
    return {"items": items, "metadata": {"data_sources_used": ["sqlite"], "credits_charged": 0, "request_id": _req_id()}}


@router.get("/billing")
async def billing_v3(request: Request):
    api_key = getattr(request.state, "api_key", "rp-dev")
    return await storage.billing_estimate(api_key)


# ─────────────────────────────────────────────────────────────────────────
# Watch (real SQLite)
# ─────────────────────────────────────────────────────────────────────────


@router.post("/watch/create")
async def watch_create_v3(body: dict, request: Request):
    api_key = getattr(request.state, "api_key", "rp-dev")
    if not body.get("name"):
        return envelope(ENDPOINT_MOCKS["watch-create"], credits=0)
    try:
        result = await storage.watch_create(
            api_key,
            name=body.get("name") or "Untitled",
            industries=body.get("industries"),
            company_ids=body.get("company_ids"),
            investor_ids=body.get("investor_ids"),
            cron=body.get("cron"),
        )
        return {**result, "metadata": {"data_sources_used": ["sqlite"], "credits_charged": 0, "request_id": _req_id()}}
    except Exception:
        return envelope(ENDPOINT_MOCKS["watch-create"], credits=0)


@router.get("/watch/{wid}/digest")
async def watch_digest_v3(wid: str):
    started = time.time()
    try:
        wl = await storage.watch_get(wid)
        if not wl:
            return envelope(ENDPOINT_MOCKS["watch-digest"], credits=10)
        items: list[dict] = []
        for ind in (wl.get("industries") or [])[:3]:
            try:
                deals = await db.industry_deals(ind, 7)
                for d in (deals.get("items") or [])[:5]:
                    items.append({"type": "deal", "industry": ind, "summary": f"{d.get('company_name')} {d.get('round')} {d.get('amount')}"})
            except Exception:
                pass
        await storage.watch_mark_digest(wid)
        return {
            "watchlist_id": wid,
            "name": wl.get("name"),
            "summary": f"过去 7 天 {len(items)} 条 deal 动态",
            "items": _ser(items),
            "metadata": _md(credits=10, sources=["qmp_data"], ms=(time.time() - started) * 1000),
        }
    except Exception:
        return envelope(ENDPOINT_MOCKS["watch-digest"], credits=10)
