"""套壳 + V4 合成 通用层 — 所有 filings/* extract/filing news/* industries/{派生} technologies/* 共用.

设计：每个端点声明 (search_query, schema_type, system_prompt) → 通用 pipeline:
  1. Tavily Search 找 N 个相关 URL
  2. (可选) Tavily Extract 抓全文
  3. V4 抽字段 / 合成 schema
  4. 包装 envelope 返回

输出统一形态 + data_sources_used + credits_charged + partial 容错.
"""
from __future__ import annotations

import asyncio
import json
import time
from datetime import date as _date
from decimal import Decimal
from typing import Any

from . import tavily as tavily_client
from .llm import chat_json


def _ser(o: Any) -> Any:
    if isinstance(o, dict):
        return {k: _ser(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_ser(x) for x in o]
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, _date):
        return o.isoformat()
    return o


# ─────────────────────────────────────────────────────────────────────────
# Filings extraction (5 schemas)
# ─────────────────────────────────────────────────────────────────────────


_FILING_SCHEMAS = {
    "prospectus_v1": """招股说明书字段抽取 schema:
{
  "company_basic":     {"name":"<公司>","ticker":"<代码|null>","industry":"...","province":"...","founded_year":<int|null>},
  "business_overview": "<≤300字主营业务描述>",
  "core_products":     [{"name":"...", "revenue_share":<0-1 number|null>}],
  "financials_5y_summary": {"revenue_cny_m":[<5个年度营收百万>], "net_profit_cny_m":[<5个净利润>], "roe_pct":[<5个 ROE>]},
  "peers_comparison":  [{"name":"...", "ps_2025":<num|null>}],
  "fundraising_projects": [{"name":"...","amount_cny_m":<num>}],
  "controlling_shareholders": [{"name":"...","stake_pct":<num>}],
  "major_risks":       [{"category":"tech|market|regulatory|finance|geo","description":"..."}],
  "core_technology":   "<≤200字>"
}""",
    "inquiry_v1": """问询回复字段抽取 schema:
{
  "company": "...",
  "round": "<问询轮次，如 '第二轮'>",
  "issuing_body": "<上交所|深交所|证监会>",
  "publish_date": "YYYY-MM-DD",
  "questions": [{"id":"<q1.1>","topic":"...","summary":"..."}],
  "responses": [{"id":"<q1.1>","summary":"...","key_data_points":[{"metric":"...","value":"..."}]}]
}""",
    "sponsor_v1": """发行保荐书 schema:
{
  "company":"...",
  "sponsor":"<保荐机构>",
  "publish_date":"YYYY-MM-DD",
  "endorsement_summary":"<≤300字保荐意见>",
  "key_risks_acknowledged": ["..."],
  "compliance_check": [{"item":"...","status":"clear|gray|concern"}]
}""",
    "audit_v1": """审计报告 schema:
{
  "company":"...","auditor":"...","publish_date":"YYYY-MM-DD","period":"YYYY",
  "opinion":"<unqualified|qualified|disclaimer|adverse>",
  "key_audit_matters":["..."],
  "disagreements":[]
}""",
    "legal_v1": """法律意见书 schema:
{
  "company":"...","law_firm":"...","publish_date":"YYYY-MM-DD",
  "legal_opinion_summary":"<≤300字>",
  "qualification_check":[{"item":"...","conclusion":"..."}],
  "outstanding_litigation":[{"case":"...","amount_cny_m":<num|null>,"status":"..."}]
}""",
}


# Schema-specific keywords used to detect if URL content matches the requested schema
_SCHEMA_KEYWORDS: dict[str, list[str]] = {
    "prospectus_v1": ["招股说明书", "首次公开发行", "保荐人", "拟发行股票", "发行人声明"],
    "inquiry_v1": ["问询函", "审核问询", "回复", "问询回复"],
    "sponsor_v1": ["发行保荐书", "保荐机构", "保荐意见"],
    "audit_v1": ["审计报告", "审计意见", "会计师事务所"],
    "legal_v1": ["法律意见书", "律师事务所"],
}


def _detect_filing_type(full_text: str) -> str | None:
    """Best-effort detection: returns the schema key whose keywords most match, or None."""
    head = full_text[:3000]
    best, best_score = None, 0
    for key, kws in _SCHEMA_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in head)
        if score > best_score:
            best, best_score = key, score
    return best if best_score >= 2 else None


async def filings_extract(url: str, schema: str = "prospectus_v1", *, model: str | None = None) -> dict[str, Any]:
    """Tavily Extract → V4 抽 5 套 filings schema 之一.

    新增 (FIX2): 检测全文是否真匹配请求的 schema；不匹配则在 metadata.warnings 加 schema_mismatch_likely。
    """
    if schema not in _FILING_SCHEMAS:
        return {"error": f"unknown schema: {schema}", "supported": list(_FILING_SCHEMAS.keys())}

    started = time.time()
    try:
        ext = await tavily_client.extract(url, extract_depth="advanced")
    except Exception as e:
        return {"error": f"tavily_extract_failed: {type(e).__name__}", "url": url}

    items = ext.get("results") or []
    if not items or not items[0].get("raw_content"):
        return {"error": "extract_empty", "url": url, "hint_for_agent": "URL may be JS-rendered or blocked. Try /v1/search first."}

    full_text = items[0]["raw_content"][:80000]

    # FIX2: Detect if URL content actually matches the requested schema
    detected = _detect_filing_type(full_text)
    schema_warnings: list[dict[str, Any]] = []
    if detected and detected != schema:
        schema_warnings.append(
            {
                "code": "schema_mismatch_likely",
                "message": f"URL content looks more like '{detected}' than '{schema}' — extraction will be best-effort.",
                "hint_for_agent": f"Pass `schema={detected!r}` for better field coverage, or use `/v1/extract/research` for a generic 11-field analyst-report schema.",
                "detected_schema": detected,
            }
        )
    elif detected is None:
        schema_warnings.append(
            {
                "code": "not_a_listing_filing",
                "message": "URL content doesn't look like a listing filing (招股书 / 问询 / 保荐 / 审计 / 法律).",
                "hint_for_agent": "If this is a research / analyst report, prefer `/v1/extract/research`. Filing extraction will return many null fields.",
            }
        )

    sys_msg = f"""你是上市文件字段抽取专家。从下面文件全文中抽取 schema 字段，严格输出 JSON，无任何前后文 / markdown / code fence。
不编造，原文没说的字段填 null 或 []。

输出 schema 严格按以下定义：
{_FILING_SCHEMAS[schema]}"""
    user_msg = f"""[文件全文]
<<<\n{full_text}\n>>>

[源 URL]
{url}

输出 JSON："""

    try:
        parsed, usage = chat_json(sys_msg, user_msg, model=model, max_tokens=8000, enable_thinking=True)
    except Exception as e:
        return {"error": f"llm_failed: {type(e).__name__}", "url": url}

    metadata: dict[str, Any] = {
        "data_sources_used": ["tavily", "deepseek-v4"],
        "model": usage.get("model"),
        "wall_time_ms": round((time.time() - started) * 1000, 1),
        "tokens": {"total": usage.get("total_tokens")},
        "credits_charged": 3,
        "partial": bool(schema_warnings),
    }
    if schema_warnings:
        metadata["warnings"] = schema_warnings
    return {
        "url": url,
        "schema": schema,
        "schema_detected": detected,
        "fields": parsed if isinstance(parsed, dict) else {"raw": str(parsed)[:1000]},
        "metadata": metadata,
    }


# ─────────────────────────────────────────────────────────────────────────
# Filings search (Tavily Search type=filing)
# ─────────────────────────────────────────────────────────────────────────


async def filings_search(
    company_id: str | None = None,
    filing_type: str | None = None,
    time_range: str = "24m",
    *,
    limit: int = 10,
    include_corpus: bool = False,
) -> dict[str, Any]:
    """Tavily Search filtered for filings + optional corpus_2026 augmentation.

    include_corpus:
        False (default) — corpus is a fallback only when Tavily returns ≤3 hits.
        True — always merge corpus results up to `limit`.
    """
    started = time.time()
    type_keyword = ""
    if filing_type and filing_type != "any":
        type_keyword = {
            "prospectus": "招股说明书",
            "inquiry": "问询函回复",
            "sponsor": "发行保荐书",
            "audit": "审计报告",
            "legal": "法律意见书",
        }.get(filing_type, "招股书")
    query_parts = [company_id or "", type_keyword, "上市文件"]
    query = " ".join([q for q in query_parts if q]).strip() or "招股说明书"

    sources: list[str] = []
    warnings: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []

    try:
        resp = await tavily_client.search(
            query=query,
            type_="filing",
            search_depth="advanced",
            max_results=limit,
            time_range=time_range,
        )
        sources.append("tavily")
        for r in (resp.get("results") or [])[:limit]:
            items.append({
                "id": _hash_url(r.get("url", "")),
                "filing_type": filing_type or _guess_filing_type(r.get("title", "")),
                "title": r.get("title"),
                "company_name": company_id,
                "publish_date": r.get("published_date"),
                "source_url": r.get("url"),
                "score": r.get("score"),
                "source": "tavily",
            })
    except Exception as e:
        warnings.append({"code": "upstream_failure", "source": "tavily", "message": str(e)[:120]})

    # Corpus augmentation: explicit (include_corpus=True) or fallback (Tavily ≤3 hits)
    if company_id and (include_corpus or len(items) <= 3):
        try:
            from . import corpus_db
            corpus_res = await corpus_db.corpus_search(query=company_id, limit=max(limit - len(items), 5))
            if corpus_res.get("results"):
                sources.append("corpus_2026")
                seen_ids = {it["id"] for it in items}
                for c in corpus_res["results"]:
                    if len(items) >= limit:
                        break
                    fake_url = f"corpus://2026/{c['file_path']}"
                    fid = _hash_url(fake_url)
                    if fid in seen_ids:
                        continue
                    items.append({
                        "id": fid,
                        "filing_type": "research_report",
                        "title": c["title"],
                        "company_name": company_id,
                        "publish_date": c["report_date"],
                        "source_url": fake_url,
                        "broker": c["broker"],
                        "industry_tags": c["industry_tags"],
                        "score": None,
                        "source": "corpus_2026",
                    })
        except Exception as e:
            warnings.append({"code": "corpus_fallback_failed", "source": "corpus_2026", "message": str(e)[:120]})

    md: dict[str, Any] = {
        "data_sources_used": sources,
        "wall_time_ms": round((time.time() - started) * 1000, 1),
        "credits_charged": 0.5,
    }
    if warnings:
        md["warnings"] = warnings
    return {"total": len(items), "results": items, "metadata": md}


def _hash_url(url: str) -> str:
    import hashlib

    return f"fil_{hashlib.sha1(url.encode()).hexdigest()[:8]}"


def _guess_filing_type(title: str) -> str:
    t = title or ""
    if "招股" in t:
        return "prospectus"
    if "问询" in t:
        return "inquiry"
    if "保荐" in t:
        return "sponsor"
    if "审计" in t:
        return "audit"
    if "法律意见" in t:
        return "legal"
    return "other"


# ─────────────────────────────────────────────────────────────────────────
# Generic V4 synthesis: search → extract → V4 合成 JSON schema
# ─────────────────────────────────────────────────────────────────────────


async def synthesize_with_search(
    *,
    query: str,
    schema_description: str,
    n_search_results: int = 5,
    extract_top_k: int = 0,  # 0 = no extract, just use search snippets
    model: str | None = None,
    extra_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generic: Tavily Search → (optional Tavily Extract) → V4 合成 schema.

    Used by all industries/{派生} + technologies/compare + companies/founders deep + screen + ...
    """
    started = time.time()

    try:
        search_resp = await tavily_client.search(
            query=query,
            type_="research",
            search_depth="advanced",
            max_results=n_search_results,
        )
    except Exception as e:
        return {
            "error": f"upstream_failure: {type(e).__name__}",
            "metadata": {"warnings": [{"code": "data_source_unavailable", "source": "tavily", "message": str(e)[:120]}]},
        }

    search_items = search_resp.get("results") or []
    sources = [{"url": r.get("url"), "title": r.get("title"), "snippet": (r.get("content") or "")[:300]} for r in search_items]

    # optional deep extract
    extracts: list[dict[str, Any]] = []
    if extract_top_k > 0 and search_items:
        urls = [r["url"] for r in search_items[:extract_top_k] if r.get("url")]
        extract_results = await asyncio.gather(*[_safe_extract(u) for u in urls], return_exceptions=False)
        for url, txt in zip(urls, extract_results):
            if txt:
                extracts.append({"url": url, "content": txt[:8000]})

    # V4 synthesis
    sys_msg = f"""你是投研合成专家。基于下面搜索结果（含 snippet 摘要 + 选 top {extract_top_k} 篇全文），合成一份 JSON 输出，严格按下面 schema:

{schema_description}

不编造，原文没说的字段填 null 或 []。严格输出 JSON，无任何前后文 / markdown / code fence。"""

    extra_ctx = json.dumps(_ser(extra_context or {}), ensure_ascii=False)[:2000]
    user_msg = f"""[查询]
{query}

[搜索结果 snippets]
{json.dumps(sources, ensure_ascii=False)[:5000]}

[Top {extract_top_k} 篇全文]
{json.dumps(extracts, ensure_ascii=False)[:8000] if extracts else "(none)"}

[补充上下文]
{extra_ctx}

输出 JSON："""

    try:
        parsed, usage = chat_json(sys_msg, user_msg, model=model, max_tokens=4000, enable_thinking=True)
    except Exception as e:
        return {
            "error": f"llm_failed: {type(e).__name__}",
            "metadata": {"warnings": [{"code": "synthesis_failed", "source": "llm", "message": str(e)[:120]}], "sources": sources},
        }

    if not isinstance(parsed, dict):
        return {"error": "non-dict synthesis output", "raw": str(parsed)[:500]}

    parsed.setdefault("citations", sources)
    parsed["metadata"] = {
        **(parsed.get("metadata") or {}),
        "data_sources_used": ["tavily", "deepseek-v4"],
        "model": usage.get("model"),
        "wall_time_ms": round((time.time() - started) * 1000, 1),
        "tokens": {"total": usage.get("total_tokens")},
    }
    return parsed


async def _safe_extract(url: str) -> str | None:
    try:
        ext = await tavily_client.extract(url, extract_depth="advanced")
        items = ext.get("results") or []
        return items[0].get("raw_content") if items else None
    except Exception:
        return None
