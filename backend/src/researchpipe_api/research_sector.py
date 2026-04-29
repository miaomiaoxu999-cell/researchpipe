"""Real /v1/research/sector orchestrator.

Steps:
  1. Tavily Search (type=research) → up to 5 PDF/HTML URLs
  2. For each URL: Tavily Extract → DeepSeek V4-Flash think → 11-field summary (parallel)
  3. qmp_data → recent deals + key companies + valuation multiples (parallel)
  4. DeepSeek V4-Flash think synthesizes the 16-field sector report from all inputs
  5. Return JobResult with `result` populated

This is a SLOW endpoint (~ 30-90s). The HTTP route puts the job in `_JOBS`
and returns the request_id immediately; the actual work runs in a background task.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from . import db
from . import tavily as tavily_client
from .llm import chat_json


SECTOR_SYSTEM = """你是一个中国一级市场投研分析师助理。
任务：基于（1）多篇研报字段抽取、（2）qmp_data 一级市场 deal 实记录、（3）行业估值倍数，
合成一份 16 字段的赛道全景研究报告 JSON 对象。严格输出 JSON，不要任何前后文。

输出 schema：
{
  "industry":            "<赛道名>",
  "snapshot_date":       "YYYY-MM-DD",
  "executive_summary":   "≤300 字 中文，基于输入综合，不编造",
  "research_views":      [<透传输入的 research_views，最多 8 条>],
  "deals":               { "domestic": [<最多 10 条最近 deals>], "summary": {<total_deals/total_amount_cny_b/yoy_change>} },
  "valuation_anchors":   { "ps_median": <number|null>, "n": <int>, "val_median_cny": <number|null>, "latest_priced_rounds": [...] },
  "key_companies":       [<最多 10 条头部公司, 含 latest_round / latest_valuation>],
  "active_investors":    [<最多 5 条机构 + 该赛道 deal 数>],
  "risks":               [<{category, description, severity}>] (≥3 条),
  "outlook":             { "catalysts_12m": [...], "threats_12m": [...] },
  "citations":           [<透传 sources 列表>],
  "metadata":            { "data_sources_used": [...], "model": "...", "generated_in_seconds": <number> },
  "filings":             [],
  "policy_signals":      [],
  "industry_chain":      { "upstream": [], "midstream": [], "downstream": [] },
  "news_pulse":          []
}

不编造。某字段无可用数据就给 [] 或 null。"""


SECTOR_USER_TEMPLATE = """[赛道]
{industry}

[研报字段抽取（来自 Tavily Extract + V4 抽 11 字段）]
{research_views_json}

[qmp_data 一级 deals - 最近 24 个月]
{deals_json}

[qmp_data 头部公司]
{companies_json}

[qmp_data 行业估值倍数]
{valuation_json}

[qmp_data 活跃机构]
{investors_json}

[Tavily citations / sources]
{citations_json}

请按 system 中的 16 字段 schema 综合输出 JSON。"""


EXTRACT_RESEARCH_SYSTEM = """你是投资研究字段抽取专家。从研报全文中精确提取 11 字段（broker / broker_country / source_type / source_name / report_title / report_date / source_url / language / core_thesis / target_price / recommendation），输出 JSON 不要任何前后文。海外英文一步翻译为中文。"""


async def _extract_view(url: str, full_text: str) -> dict[str, Any] | None:
    """Use V4-Flash think to extract 11 fields from one research report."""
    if not full_text or len(full_text) < 500:
        return None
    sys_msg = EXTRACT_RESEARCH_SYSTEM
    user_msg = f"研报全文：\n<<<\n{full_text[:50000]}\n>>>\n\n源 URL：{url}\n\n输出 JSON："
    try:
        parsed, _ = chat_json(sys_msg, user_msg, max_tokens=2000, enable_thinking=False)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


async def _fetch_and_extract_one(url: str) -> dict[str, Any] | None:
    """Tavily Extract one URL → 11-field view."""
    try:
        ext = await tavily_client.extract(url, extract_depth="advanced")
        items = ext.get("results") or []
        if not items or not items[0].get("raw_content"):
            return None
        return await _extract_view(url, items[0]["raw_content"])
    except Exception:
        return None


async def run_sector_research(industry: str, *, time_range: str = "24m") -> dict[str, Any]:
    """Main orchestrator. Returns the 16-field result dict."""
    started = time.time()
    days = 24 * 30
    if time_range.endswith("m"):
        days = int(time_range[:-1]) * 30
    elif time_range.endswith("d"):
        days = int(time_range[:-1])

    # Step 1+2 parallel with Step 3 qmp queries
    # Step 1: Tavily Search
    async def get_research_views() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        try:
            search_resp = await tavily_client.search(
                query=f"{industry} 行业 深度研究 报告 2026",
                type_="research",
                search_depth="advanced",
                max_results=8,
            )
        except Exception:
            return [], []
        results = search_resp.get("results") or []
        urls = [r["url"] for r in results if r.get("url") and r["url"].lower().endswith(".pdf")][:5]
        if not urls:
            urls = [r["url"] for r in results if r.get("url")][:5]
        # Step 2: parallel extract
        extracted = await asyncio.gather(*[_fetch_and_extract_one(u) for u in urls], return_exceptions=False)
        views = [v for v in extracted if v]
        sources = [{"url": r.get("url"), "title": r.get("title")} for r in results[:8]]
        return views, sources

    async def get_qmp_data():
        try:
            deals = await db.industry_deals(industry, days)
            companies = await db.industry_companies(industry, 30)
            multiples = await db.valuations_multiples(industry)
            valuations_recent = await db.valuations_search(industry, None, 10)
            return {"deals": deals, "companies": companies, "multiples": multiples, "valuations_recent": valuations_recent}
        except Exception as e:
            return {"deals": {"items": []}, "companies": [], "multiples": None, "valuations_recent": [], "_error": str(e)[:80]}

    async def get_active_investors():
        # Top investors in industry (event count by institution)
        try:
            from . import db as _db
            pool = await _db.get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    f"""
                    SELECT i.institution_id, i.institution_name, COUNT(*) AS deal_count
                    FROM events e
                    JOIN institutions i ON i.institution_id = e.institution_id
                    WHERE (e.industry ILIKE $1 OR e.sub_industry ILIKE $1)
                      AND e.investment_date >= CURRENT_DATE - INTERVAL '{days} days'
                    GROUP BY i.institution_id, i.institution_name
                    ORDER BY deal_count DESC LIMIT 5
                    """,
                    f"%{industry}%",
                )
            return [dict(r) for r in rows]
        except Exception:
            return []

    views_sources_t = asyncio.create_task(get_research_views())
    qmp_t = asyncio.create_task(get_qmp_data())
    investors_t = asyncio.create_task(get_active_investors())
    (views, sources), qmp, active_investors = await asyncio.gather(views_sources_t, qmp_t, investors_t)

    # Step 4: synthesis
    from datetime import date
    from decimal import Decimal

    def _ser(o):
        if isinstance(o, dict):
            return {k: _ser(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_ser(x) for x in o]
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, date):
            return o.isoformat()
        return o

    deals_items = (qmp.get("deals") or {}).get("items") or []
    user_msg = SECTOR_USER_TEMPLATE.format(
        industry=industry,
        research_views_json=json.dumps(views[:5], ensure_ascii=False)[:6000],
        deals_json=json.dumps(_ser(deals_items[:20]), ensure_ascii=False)[:5000],
        companies_json=json.dumps(_ser(qmp.get("companies") or [])[:20], ensure_ascii=False)[:3000],
        valuation_json=json.dumps(_ser({"multiples": qmp.get("multiples"), "recent": qmp.get("valuations_recent")}), ensure_ascii=False)[:3000],
        investors_json=json.dumps(_ser(active_investors), ensure_ascii=False)[:1500],
        citations_json=json.dumps(sources, ensure_ascii=False)[:2000],
    )

    try:
        result, usage = chat_json(SECTOR_SYSTEM, user_msg, max_tokens=8000, enable_thinking=True)
    except Exception as e:
        # Soft-fail: return raw inputs as the result so caller can salvage
        return {
            "industry": industry,
            "snapshot_date": date.today().isoformat(),
            "research_views": views,
            "deals": {"domestic": _ser(deals_items[:10]), "summary": {"total_deals": (qmp.get("deals") or {}).get("total")}},
            "key_companies": _ser((qmp.get("companies") or [])[:10]),
            "active_investors": _ser(active_investors),
            "valuation_anchors": _ser({"multiples": qmp.get("multiples"), "recent_priced_rounds": qmp.get("valuations_recent")}),
            "citations": sources,
            "metadata": {
                "data_sources_used": ["tavily", "qmp_data"],
                "model": "synthesis_failed",
                "error": str(e)[:200],
                "generated_in_seconds": round(time.time() - started, 1),
            },
        }

    # Annotate metadata
    if isinstance(result, dict):
        meta = result.setdefault("metadata", {})
        meta.setdefault("data_sources_used", ["tavily", "qmp_data", "deepseek-v4"])
        meta["generated_in_seconds"] = round(time.time() - started, 1)
        meta["model"] = usage.get("model")
        meta["tokens"] = {"total": usage.get("total_tokens")}
    return result if isinstance(result, dict) else {"error": "synthesis returned non-dict"}


# ─────────────────────────────────────────────────────────────────────────
# research/company orchestrator
# ─────────────────────────────────────────────────────────────────────────


COMPANY_SYSTEM = """你是一个中国一级市场投研分析师助理。
任务：基于（1）该公司全部融资事件、（2）多篇相关研报字段抽取、（3）行业估值倍数，
合成一份 16 字段的公司尽调研究报告 JSON 对象。严格输出 JSON，不要任何前后文。

输出 schema：
{
  "company_basic":      { "name": "<公司>", "industry": "<...>", "founded_year": <int|null>, "region": "<...>" },
  "snapshot_date":      "YYYY-MM-DD",
  "executive_summary":  "≤300 字 中文综合，不编造",
  "business_profile":   { "model": "...", "products": [...], "stage": "..." },
  "peers_dd":           [<最多 5 条同赛道头部公司，含 stage 和 valuation>],
  "valuation_anchor":   { "latest_round": "...", "latest_valuation_cny": <number|null>, "industry_ps_median": <number|null> },
  "filing_risks":       { "ipo_status": "...", "key_risks": [...] },
  "financials_summary": { "deal_count": <int>, "total_funding_cny_m": <number>, "rounds": [...] },
  "founders_background": [],
  "patent_portfolio":   {},
  "major_investors":    [<最多 8 条，含 institution_name + 是否 lead>],
  "recent_news":        [],
  "red_flags":          [<{category, description, severity}>],
  "outlook":            { "short_term": "...", "mid_term": "...", "long_term": "..." },
  "citations":          [<透传 sources>],
  "metadata":           {}
}

无可用数据的字段给 [] / null / "" 即可。"""


COMPANY_USER_TEMPLATE = """[公司]
{company_name}

[qmp_data 该公司全部融资事件]
{deals_json}

[研报字段抽取（5 篇相关研报）]
{research_views_json}

[同赛道头部公司]
{peers_json}

[行业估值倍数]
{valuation_json}

[Tavily citations / sources]
{citations_json}

按 system 中的 16 字段 schema 综合输出 JSON。"""


async def run_company_research(company_name: str, *, focus: list[str] | None = None) -> dict[str, Any]:
    """research/company orchestrator. ~30-60s."""
    started = time.time()

    async def get_research_views() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        try:
            search_resp = await tavily_client.search(
                query=f"{company_name} 公司 研究报告 2026",
                type_="research",
                search_depth="advanced",
                max_results=8,
            )
        except Exception:
            return [], []
        results = search_resp.get("results") or []
        urls = [r["url"] for r in results if r.get("url") and r["url"].lower().endswith(".pdf")][:5]
        if not urls:
            urls = [r["url"] for r in results if r.get("url")][:5]
        extracted = await asyncio.gather(*[_fetch_and_extract_one(u) for u in urls], return_exceptions=False)
        views = [v for v in extracted if v]
        sources = [{"url": r.get("url"), "title": r.get("title")} for r in results[:8]]
        return views, sources

    async def get_qmp_data():
        try:
            company = await db.companies_get(company_name)
            deals = await db.company_deals(company_name)
            ind = (company or {}).get("industry") or ""
            peers = await db.industry_companies(ind, 6) if ind else []
            multiples = await db.valuations_multiples(ind) if ind else None
            return {"company": company, "deals": deals, "peers": peers, "multiples": multiples, "industry": ind}
        except Exception as e:
            return {"company": None, "deals": [], "peers": [], "multiples": None, "industry": "", "_error": str(e)[:120]}

    views_sources_t = asyncio.create_task(get_research_views())
    qmp_t = asyncio.create_task(get_qmp_data())
    (views, sources), qmp = await asyncio.gather(views_sources_t, qmp_t)

    from datetime import date
    from decimal import Decimal

    def _ser(o):
        if isinstance(o, dict):
            return {k: _ser(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_ser(x) for x in o]
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, date):
            return o.isoformat()
        return o

    user_msg = COMPANY_USER_TEMPLATE.format(
        company_name=company_name,
        deals_json=json.dumps(_ser(qmp.get("deals") or [])[:30], ensure_ascii=False)[:5000],
        research_views_json=json.dumps(views[:5], ensure_ascii=False)[:6000],
        peers_json=json.dumps(_ser(qmp.get("peers") or [])[:5], ensure_ascii=False)[:2000],
        valuation_json=json.dumps(_ser({"multiples": qmp.get("multiples"), "industry": qmp.get("industry")}), ensure_ascii=False)[:1500],
        citations_json=json.dumps(sources, ensure_ascii=False)[:2000],
    )

    try:
        result, usage = chat_json(COMPANY_SYSTEM, user_msg, max_tokens=8000, enable_thinking=True)
    except Exception as e:
        return {
            "company_basic": _ser(qmp.get("company") or {"name": company_name}),
            "snapshot_date": date.today().isoformat(),
            "research_views": views,
            "financials_summary": {"deal_count": len(qmp.get("deals") or [])},
            "peers_dd": _ser((qmp.get("peers") or [])[:5]),
            "citations": sources,
            "metadata": {
                "data_sources_used": ["tavily", "qmp_data"],
                "model": "synthesis_failed",
                "error": str(e)[:200],
                "generated_in_seconds": round(time.time() - started, 1),
            },
        }

    if isinstance(result, dict):
        meta = result.setdefault("metadata", {})
        meta.setdefault("data_sources_used", ["tavily", "qmp_data", "deepseek-v4"])
        meta["generated_in_seconds"] = round(time.time() - started, 1)
        meta["model"] = usage.get("model")
        meta["tokens"] = {"total": usage.get("total_tokens")}
    return result if isinstance(result, dict) else {"error": "synthesis returned non-dict"}


# ─────────────────────────────────────────────────────────────────────────
# research/valuation orchestrator
# ─────────────────────────────────────────────────────────────────────────


VALUATION_SYSTEM = """你是一个中国一级市场估值分析师助理。
任务：基于（1）行业 PS 倍数 + 估值带分布、（2）近期 priced rounds、（3）海外可比公司，
合成一份估值锚研究报告 JSON 对象。严格输出 JSON，不要任何前后文。

输出 schema：
{
  "input":               "<sector or company>",
  "snapshot_date":       "YYYY-MM-DD",
  "summary":             "≤200 字 估值现状综合",
  "industry_multiples":  { "ps_median": <num|null>, "ps_mean": <num|null>, "n": <int>, "val_median_cny": <num|null> },
  "recent_priced_rounds":[<最多 8 条最新一轮估值数据>],
  "valuation_band":      { "low": <num>, "median": <num>, "high": <num>, "outlier_threshold": <num>, "unicorn_count": <int> },
  "drivers":             ["<量化或定性驱动因素>"],
  "risks":               ["<估值压制因素>"],
  "outlook":             { "12m_direction": "up|flat|down", "rationale": "..." },
  "citations":           [<透传 sources>],
  "metadata":            {}
}"""


VALUATION_USER_TEMPLATE = """[赛道 / 公司]
{input}

[行业估值倍数]
{multiples_json}

[近期 priced rounds]
{recent_json}

[Tavily citations]
{citations_json}

按 schema 输出 JSON。"""


async def run_valuation_research(input_: str, regions: list[str] | None = None) -> dict[str, Any]:
    """research/valuation orchestrator. ~20-40s."""
    started = time.time()

    async def get_qmp():
        try:
            multiples = await db.valuations_multiples(input_)
            recent = await db.valuations_search(input_, None, 10)
            return {"multiples": multiples, "recent": recent}
        except Exception as e:
            return {"multiples": None, "recent": [], "_error": str(e)[:120]}

    async def get_search_sources():
        try:
            r = await tavily_client.search(
                query=f"{input_} 估值 PS PE 2026 行业平均",
                type_="research",
                max_results=6,
            )
            return [{"url": x.get("url"), "title": x.get("title")} for x in (r.get("results") or [])[:6]]
        except Exception:
            return []

    qmp, sources = await asyncio.gather(get_qmp(), get_search_sources())

    from datetime import date
    from decimal import Decimal

    def _ser(o):
        if isinstance(o, dict):
            return {k: _ser(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_ser(x) for x in o]
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, date):
            return o.isoformat()
        return o

    user_msg = VALUATION_USER_TEMPLATE.format(
        input=input_,
        multiples_json=json.dumps(_ser(qmp.get("multiples") or {}), ensure_ascii=False)[:1500],
        recent_json=json.dumps(_ser(qmp.get("recent") or [])[:10], ensure_ascii=False)[:3000],
        citations_json=json.dumps(sources, ensure_ascii=False)[:1500],
    )

    try:
        result, usage = chat_json(VALUATION_SYSTEM, user_msg, max_tokens=4000, enable_thinking=False)
    except Exception as e:
        return {
            "input": input_,
            "snapshot_date": date.today().isoformat(),
            "industry_multiples": _ser(qmp.get("multiples") or {}),
            "recent_priced_rounds": _ser((qmp.get("recent") or [])[:10]),
            "citations": sources,
            "metadata": {"data_sources_used": ["tavily", "qmp_data"], "error": str(e)[:200], "generated_in_seconds": round(time.time() - started, 1)},
        }

    if isinstance(result, dict):
        meta = result.setdefault("metadata", {})
        meta.setdefault("data_sources_used", ["tavily", "qmp_data", "deepseek-v4"])
        meta["generated_in_seconds"] = round(time.time() - started, 1)
        meta["model"] = usage.get("model")
        meta["tokens"] = {"total": usage.get("total_tokens")}
    return result if isinstance(result, dict) else {"error": "synthesis returned non-dict"}
