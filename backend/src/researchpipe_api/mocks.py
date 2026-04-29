"""Mock responses for stub endpoints — same shape as eval/src/lib/mocks/index.ts in frontend."""
from __future__ import annotations

import secrets
from typing import Any


def _req_id() -> str:
    return f"req_{secrets.token_hex(5)}"


SECTOR_MOCK: dict[str, Any] = {
    "industry": "具身智能",
    "snapshot_date": "2026-04-29",
    "executive_summary": "具身智能赛道 2025 年起进入资本加速期，2026 Q1 单季融资额 ¥184 亿，同比 +320%。技术路径分化为 Tesla Optimus 派 / 谷歌 RT-2 派 / 国产 Figure 派三大阵营，国内头部公司估值 $1-3B 区间。",
    "research_views": [
        {"broker": "中信建投", "core_thesis": "2026 是具身智能从 demo 走向小批量交付的关键拐点", "report_date": "2026-03-22"}
    ],
    "deals": {
        "domestic": [{"company": "智元机器人", "amount_cny_m": 1200, "stage": "B+", "date": "2026-03-14"}],
        "summary": {"total_deals": 47, "total_amount_cny_b": 18.4, "yoy_change": "+320%"},
    },
    "key_companies": [{"name": "智元机器人", "stage": "B+", "latest_valuation_usd_b": 2.1}],
    "active_investors": [{"name": "高瓴", "deals_in_sector_24m": 8}],
    "risks": [{"category": "tech", "description": "灵巧手成本未压缩到量产水平", "severity": "high"}],
    "outlook": {"catalysts_12m": ["头部公司小批量交付"], "threats_12m": ["美国出口管制升级"]},
    "citations": [{"id": 1, "source_url": "https://research.example.com/csc-embodied-ai"}],
    "metadata": {"data_sources_used": ["qmp_research", "qmp_deals", "tavily"], "model": "deepseek-v4-flash"},
}

COMPANY_MOCK: dict[str, Any] = {
    "company_basic": {"name": "宁德时代", "ticker": "300750.SZ", "sector": "动力电池", "founded_year": 2011},
    "snapshot_date": "2026-04-29",
    "executive_summary": "宁德时代 2025 年全球动力电池市占率 37.3%，连续 9 年第一。",
    "valuation_anchor": {"pe_ttm": 18.4, "ps_2025": 2.1},
    "red_flags": [{"category": "geo", "description": "北美工厂因 FEOC 暂缓", "severity": "medium"}],
    "metadata": {"data_sources_used": ["qmp_filings", "qmp_deals"], "model": "deepseek-v4-flash"},
}

COMPANY_PROFILE_MOCK: dict[str, Any] = {
    "id": "comp_2x9bka",
    "name": "宁德时代新能源科技股份有限公司",
    "short_name": "宁德时代",
    "sector": {"id": "ind_battery", "name": "动力电池"},
    "products": ["麒麟电池", "神行超充电池", "EnerC"],
    "founders": [{"name": "曾毓群", "title": "董事长"}],
    "funding_rounds": [{"stage": "IPO", "date": "2018-06-11", "market": "深交所创业板"}],
    "latest_valuation": {"value_cny_b": 1080, "as_of": "2026-04-29"},
    "employees": 113000,
    "ipo_status": "listed",
}

DEAL_LIST_MOCK: dict[str, Any] = {
    "total": 47,
    "results": [
        {"id": "deal_8f2", "company": "智元机器人", "industry": "具身智能", "stage": "B+", "amount_cny_m": 1200, "date": "2026-03-14"},
        {"id": "deal_2k9", "company": "宇树科技", "industry": "具身智能", "stage": "C", "amount_cny_m": 800, "date": "2026-02-20"},
    ],
}


def envelope(payload: dict[str, Any], *, credits: float = 1, partial: bool = False) -> dict[str, Any]:
    """Wrap payload with a uniform metadata envelope."""
    md = {
        "request_id": _req_id(),
        "credits_charged": credits,
        "data_sources_used": ["qmp_data"],
        "partial": partial,
    }
    if isinstance(payload, dict) and "metadata" in payload:
        md.update(payload["metadata"])
    payload = dict(payload)
    payload["metadata"] = md
    return payload


# Endpoint id → mock builder
ENDPOINT_MOCKS: dict[str, dict[str, Any]] = {
    # Data — Companies
    "companies-search": {"total": 12, "results": [{"id": "comp_2x9", "name": "宁德时代", "sector": "动力电池"}]},
    "companies-get": COMPANY_PROFILE_MOCK,
    "companies-deals": {"total": 5, "results": [{"id": "deal_a1", "stage": "IPO", "date": "2018-06-11"}]},
    "companies-peers": {"results": [{"id": "comp_3y4", "name": "比亚迪"}]},
    "companies-news": {"total": 12, "results": [{"title": "宁德时代港股上市获聆讯通过", "published_at": "2026-04-22"}]},
    "companies-founders": {"founders": [{"name": "曾毓群", "title": "董事长", "brief": "CATL 创始人"}]},
    # Data — Investors
    "investors-search": {"total": 8, "results": [{"id": "inv_h", "name": "高瓴", "type": "VC"}]},
    "investors-get": {"id": "inv_h", "name": "高瓴", "founded_year": 2005, "aum_usd_b": 100},
    "investors-portfolio": {"total": 234, "results": [{"company": "宁德时代", "stage": "B"}]},
    "investors-preferences": {"top_industries": ["具身智能", "动力电池"], "top_stages": ["B", "C"]},
    "investors-exits": {"results": [{"company": "蔚来", "exit_type": "ipo", "date": "2018-09-12"}]},
    # Data — Deals
    "deals-search": DEAL_LIST_MOCK,
    "deals-get": {"id": "deal_8f2", "company": "智元机器人", "stage": "B+", "amount_cny_m": 1200},
    "deals-timeline": {"company_id": "comp_2x9", "events": [{"date": "2018-06-11", "event": "IPO"}]},
    "deals-overseas": {"results": [{"company": "Figure AI", "amount_usd_m": 700}]},
    "deals-co-investors": {"deal_id": "deal_8f2", "co_investors": [{"name": "高瓴"}, {"name": "红杉中国"}]},
    # Data — Industries
    "industries-search": {"results": [{"id": "ind_embodied", "name": "具身智能"}]},
    "industries-deals": {"total": 47, "results": DEAL_LIST_MOCK["results"]},
    "industries-companies": {"results": [{"id": "comp_zhiyuan", "name": "智元机器人"}]},
    "industries-chain": {"upstream": ["核心零部件"], "midstream": ["本体厂"], "downstream": ["工业 / 消费"]},
    "industries-policies": {"policies": [{"title": "具身智能产业发展实施意见", "date": "2026-03-15"}]},
    "industries-tech-roadmap": {"phases": [{"name": "感知", "maturity": 0.7}, {"name": "决策", "maturity": 0.5}]},
    "industries-key-tech": {"technologies": [{"name": "灵巧手", "domestic_rate": 0.45}]},
    "industries-maturity": {"curve_position": "trough_of_disillusionment", "estimated_years_to_plateau": 4},
    "technologies-compare": {"a": {"name": "Tesla Optimus 派"}, "b": {"name": "国产 Figure 派"}, "verdict": "国产更具成本优势"},
    # Data — Valuations
    "valuations-search": {"results": [{"company": "宁德时代", "ps_2025": 2.1}]},
    "valuations-multiples": {"industry": "动力电池", "ps_median": 1.6, "pe_median": 18.4},
    "valuations-compare": {"markets": ["a-share", "us"], "delta_ps": 0.5},
    "valuations-distribution": {"unicorn_threshold_usd_b": 1.0, "deals_above_threshold": 8},
    # Data — Filings
    "filings-search": {"total": 12, "results": [{"id": "fil_x29", "filing_type": "prospectus"}]},
    "filings-get": {"id": "fil_x29", "filing_type": "prospectus", "company": "示例科技"},
    "filings-extract": {"schema": "prospectus_v1", "fields": {"company_basic": {"name": "示例科技"}}},
    "filings-risks": {"risks": [{"level": "high", "description": "客户集中度风险"}]},
    "filings-financials": {"revenue_5y_cny_m": [120, 180, 245, 310, 405]},
    # Data — News & Events
    "news-search": {"total": 24, "results": [{"title": "具身智能赛道 Q1 融资达新高", "published_at": "2026-04-25"}]},
    "news-recent": {"results": [{"title": "智元机器人完成 B+ 轮", "published_at": "2026-04-28"}]},
    "events-timeline": {"events": [{"date": "2026-03-14", "type": "deal"}]},
    # Data — Tasks
    "screen": {"total": 12, "results": [{"id": "comp_zhiyuan", "name": "智元机器人"}]},
    # Watch
    "watch-create": {"id": "watch_a8f2", "name": "具身智能监控"},
    "watch-digest": {"watchlist_id": "watch_a8f2", "summary": "本周共 3 起新融资", "items": []},
    # Account
    "me": {"api_key_prefix": "rp-dev-xxxx...", "plan": "Pro", "credits_used_this_month": 9847, "credits_limit": 80000, "plan_resets_on": "2026-05-01"},
    "usage": {"items": [{"date": "2026-04-28", "endpoint": "search", "calls": 142, "credits": 142}]},
    "billing": {"month": "2026-04", "plan": "Pro", "plan_fee_cny": 5000, "overage_credits": 0, "overage_fee_cny": 0, "total_due_cny": 5000},
}
