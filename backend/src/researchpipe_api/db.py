"""qmp_data PostgreSQL read-only access layer.

CRITICAL: every txn opens with `START TRANSACTION READ ONLY` to prevent
any accidental writes. The user (muye) explicitly forbade DB modifications.
"""
from __future__ import annotations

from typing import Any

import asyncpg

from .settings import QMP_DB_DSN

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            QMP_DB_DSN,
            min_size=1,
            max_size=4,
            command_timeout=10.0,
            server_settings={"default_transaction_read_only": "on"},
        )
    return _pool


async def close_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def is_alive() -> bool:
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────
# Companies (aggregated from events table)
# ─────────────────────────────────────────────────────────────────────────


async def companies_search(query: str | None, industry: str | None, limit: int) -> list[dict[str, Any]]:
    pool = await get_pool()
    sql = """
        SELECT
            company_name,
            MAX(industry) AS industry,
            MAX(sub_industry) AS sub_industry,
            MAX(region) AS region,
            MAX(city) AS city,
            COUNT(*) AS deal_count,
            MAX(investment_date) AS last_deal_date,
            MAX(round) AS last_round,
            MAX(company_description) AS description
        FROM events
        WHERE 1=1
    """
    params: list[Any] = []
    if query:
        sql += f" AND company_name ILIKE ${len(params) + 1}"
        params.append(f"%{query}%")
    if industry:
        sql += f" AND industry = ${len(params) + 1}"
        params.append(industry)
    sql += f" GROUP BY company_name ORDER BY MAX(investment_date) DESC NULLS LAST LIMIT ${len(params) + 1}"
    params.append(limit)
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    return [dict(r) for r in rows]


async def companies_get(company_name: str) -> dict[str, Any] | None:
    pool = await get_pool()
    sql = """
        SELECT
            company_name,
            MAX(industry) AS industry,
            MAX(sub_industry) AS sub_industry,
            MAX(region) AS region,
            MAX(city) AS city,
            COUNT(*) AS deal_count,
            MAX(investment_date) AS last_deal_date,
            MAX(round) AS last_round,
            MAX(company_description) AS description,
            ARRAY_AGG(DISTINCT round) FILTER (WHERE round IS NOT NULL) AS rounds,
            SUM(CASE WHEN amount IS NOT NULL THEN amount ELSE 0 END) AS total_known_amount
        FROM events
        WHERE company_name = $1
        GROUP BY company_name
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, company_name)
    return dict(row) if row else None


async def company_deals(company_name: str) -> list[dict[str, Any]]:
    pool = await get_pool()
    sql = """
        SELECT e.event_id, e.company_name, e.investment_date, e.round, e.amount, e.currency,
               e.is_lead_investor, e.industry, i.institution_name, i.institution_id
        FROM events e
        LEFT JOIN institutions i ON i.institution_id = e.institution_id
        WHERE e.company_name = $1
        ORDER BY e.investment_date DESC NULLS LAST
        LIMIT 50
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, company_name)
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────
# Investors (institutions table)
# ─────────────────────────────────────────────────────────────────────────


async def investors_search(query: str | None, type_: str | None, limit: int) -> list[dict[str, Any]]:
    pool = await get_pool()
    sql = "SELECT institution_id, institution_name, name_en, headquarters, type, founded_year, investment_count FROM institutions WHERE 1=1"
    params: list[Any] = []
    if query:
        sql += f" AND (institution_name ILIKE ${len(params) + 1} OR name_en ILIKE ${len(params) + 1})"
        params.append(f"%{query}%")
    if type_ and type_ != "any":
        sql += f" AND type = ${len(params) + 1}"
        params.append(type_)
    sql += f" ORDER BY investment_count DESC NULLS LAST LIMIT ${len(params) + 1}"
    params.append(limit)
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    return [dict(r) for r in rows]


async def investors_get(institution_id: int) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT institution_id, institution_name, name_en, headquarters, type,
                   founded_year, stage_preference, aum, investment_count, website, description
            FROM institutions WHERE institution_id = $1
            """,
            institution_id,
        )
    return dict(row) if row else None


async def investor_portfolio(institution_id: int, limit: int = 50) -> list[dict[str, Any]]:
    pool = await get_pool()
    sql = """
        SELECT event_id, company_name, industry, round, amount, currency, investment_date, is_lead_investor
        FROM events
        WHERE institution_id = $1
        ORDER BY investment_date DESC NULLS LAST
        LIMIT $2
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, institution_id, limit)
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────
# Deals (events table directly)
# ─────────────────────────────────────────────────────────────────────────


async def deals_search(
    industry: str | None,
    stage: str | None,
    amount_min_cny_m: float | None,
    time_range_days: int,
    limit: int,
) -> dict[str, Any]:
    """Search events. time_range_days is inlined as int (no SQL injection — int-validated).

    industry uses alias expansion (具身智能 → 人工智能 + 人形机器人 + 关键词).
    """
    from . import aliases

    if not isinstance(time_range_days, int) or time_range_days < 0 or time_range_days > 36500:
        time_range_days = 365
    if not isinstance(limit, int) or limit < 1 or limit > 200:
        limit = 20

    pool = await get_pool()
    where = [f"e.investment_date >= CURRENT_DATE - INTERVAL '{time_range_days} days'"]
    params: list[Any] = []
    if industry:
        ind_clause, ind_params = aliases.build_industry_where_clause(industry, params_offset=len(params))
        where.append(ind_clause)
        params.extend(ind_params)
    if stage and stage != "any":
        where.append(f"e.round ILIKE ${len(params) + 1}")
        params.append(f"%{stage}%")
    if amount_min_cny_m is not None:
        where.append(f"e.amount >= ${len(params) + 1}::numeric")
        params.append(float(amount_min_cny_m) * 1_000_000)

    where_sql = " AND ".join(where)
    sql = f"""
        SELECT e.event_id, e.company_name, e.industry, e.sub_industry,
               e.round, e.amount, e.currency, e.investment_date, e.is_lead_investor,
               i.institution_name, i.institution_id
        FROM events e
        LEFT JOIN institutions i ON i.institution_id = e.institution_id
        WHERE {where_sql}
        ORDER BY e.investment_date DESC NULLS LAST
        LIMIT {limit}
    """
    count_sql = f"SELECT COUNT(*) FROM events e WHERE {where_sql}"
    async with pool.acquire() as conn:
        items = [dict(r) for r in await conn.fetch(sql, *params)]
        total = await conn.fetchval(count_sql, *params)
    return {"total": total or 0, "items": items}


async def deal_get(event_id: int) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT e.event_id, e.company_name, e.industry, e.sub_industry,
                   e.round, e.amount, e.currency, e.investment_date, e.is_lead_investor,
                   e.region, e.city, e.company_description,
                   i.institution_name, i.institution_id
            FROM events e
            LEFT JOIN institutions i ON i.institution_id = e.institution_id
            WHERE e.event_id = $1
            """,
            event_id,
        )
    return dict(row) if row else None


# ─────────────────────────────────────────────────────────────────────────
# Valuations
# ─────────────────────────────────────────────────────────────────────────


async def valuations_search(industry: str | None, stage: str | None, limit: int = 20) -> list[dict[str, Any]]:
    pool = await get_pool()
    sql = """
        SELECT id, company_short_name, company_name, industry, latest_round,
               valuation_date, valuation_amount_cny, currency, ps_ratio
        FROM valuations
        WHERE 1=1
    """
    params: list[Any] = []
    if industry:
        sql += f" AND industry ILIKE ${len(params) + 1}"
        params.append(f"%{industry}%")
    if stage and stage != "any":
        sql += f" AND latest_round ILIKE ${len(params) + 1}"
        params.append(f"%{stage}%")
    sql += f" ORDER BY valuation_date DESC NULLS LAST LIMIT ${len(params) + 1}"
    params.append(limit)
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    return [dict(r) for r in rows]


async def valuations_multiples(industry: str) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT industry,
                   PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ps_ratio) AS ps_median,
                   AVG(ps_ratio) AS ps_mean,
                   COUNT(ps_ratio) AS n,
                   PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY valuation_amount_cny) AS val_median_cny
            FROM valuations
            WHERE industry ILIKE $1 AND ps_ratio IS NOT NULL
            GROUP BY industry
            """,
            f"%{industry}%",
        )
    return dict(row) if row else None


# ─────────────────────────────────────────────────────────────────────────
# Industries — derived from events
# ─────────────────────────────────────────────────────────────────────────


async def industries_search(query: str) -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT industry AS id, industry AS name, COUNT(*) AS deal_count
            FROM events WHERE industry ILIKE $1
            GROUP BY industry ORDER BY deal_count DESC LIMIT 20
            """,
            f"%{query}%",
        )
    return [dict(r) for r in rows]


async def industry_deals(industry: str, time_range_days: int = 365) -> dict[str, Any]:
    """Industry deals lookup — alias-expanded (具身智能 → 人工智能 + 人形机器人 + 关键词)."""
    from . import aliases

    where_sql, params = aliases.build_industry_where_clause(industry, params_offset=0)
    pool = await get_pool()
    sql = f"""
        SELECT e.event_id, e.company_name, e.industry, e.sub_industry,
               e.round, e.amount, e.currency,
               e.investment_date, i.institution_name
        FROM events e
        LEFT JOIN institutions i ON i.institution_id = e.institution_id
        WHERE {where_sql}
          AND e.investment_date >= CURRENT_DATE - INTERVAL '{time_range_days} days'
        ORDER BY e.investment_date DESC NULLS LAST
        LIMIT 50
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    return {
        "total": len(rows),
        "industry": industry,
        "alias_expanded": industry in aliases.ALIASES,
        "items": [dict(r) for r in rows],
    }


async def industry_companies(industry: str, limit: int = 50) -> list[dict[str, Any]]:
    from . import aliases

    where_sql, params = aliases.build_industry_where_clause(industry, params_offset=0)
    n = len(params)
    pool = await get_pool()
    sql = f"""
        SELECT e.company_name, MAX(e.industry) AS industry, MAX(e.sub_industry) AS sub_industry,
               COUNT(*) AS deal_count,
               MAX(e.investment_date) AS last_deal_date, MAX(e.round) AS last_round
        FROM events e WHERE {where_sql}
        GROUP BY e.company_name
        ORDER BY MAX(e.investment_date) DESC NULLS LAST
        LIMIT ${n + 1}
    """
    params.append(limit)
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────
# v3 P1 derived queries
# ─────────────────────────────────────────────────────────────────────────


async def deal_co_investors(event_id: int) -> list[dict[str, Any]]:
    """Find co-investors: same company + same round + same date as the target event."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        target = await conn.fetchrow(
            "SELECT company_name, round, investment_date FROM events WHERE event_id = $1",
            event_id,
        )
        if not target:
            return []
        rows = await conn.fetch(
            """
            SELECT e.event_id, e.is_lead_investor, i.institution_id, i.institution_name, i.type
            FROM events e
            LEFT JOIN institutions i ON i.institution_id = e.institution_id
            WHERE e.company_name = $1
              AND e.round = $2
              AND e.investment_date = $3
              AND e.event_id != $4
            """,
            target["company_name"],
            target["round"],
            target["investment_date"],
            event_id,
        )
    return [dict(r) for r in rows]


async def company_timeline(company_name: str) -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT event_id, investment_date, round, amount, currency, industry,
                   (SELECT institution_name FROM institutions WHERE institution_id = e.institution_id) AS institution_name
            FROM events e
            WHERE company_name = $1
            ORDER BY investment_date ASC NULLS LAST
            """,
            company_name,
        )
    return [dict(r) for r in rows]


async def deals_overseas_qmp(country: str | None = None, industry: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """qmp 暂无国外 deal，返回空 → 走 Tavily 套壳兜底（routes 层处理）."""
    return []


async def screen_companies(
    industry: str,
    *,
    min_funding_cny_m: float | None = None,
    stage: str | None = None,
    geo: str | None = None,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """多条件筛选公司."""
    pool = await get_pool()
    where = ["(e.industry ILIKE $1 OR e.sub_industry ILIKE $1)"]
    params: list[Any] = [f"%{industry}%"]
    if min_funding_cny_m is not None:
        where.append(f"e.amount >= ${len(params) + 1}::numeric")
        params.append(float(min_funding_cny_m) * 1_000_000)
    if stage:
        where.append(f"e.round ILIKE ${len(params) + 1}")
        params.append(f"%{stage}%")
    if geo:
        where.append(f"(e.region ILIKE ${len(params) + 1} OR e.city ILIKE ${len(params) + 1})")
        params.append(f"%{geo}%")
    where_sql = " AND ".join(where)
    sql = f"""
        SELECT e.company_name,
               MAX(e.industry) AS industry,
               MAX(e.region) AS region,
               MAX(e.city) AS city,
               COUNT(*) AS deal_count,
               MAX(e.investment_date) AS last_deal_date,
               MAX(e.round) AS last_round,
               SUM(CASE WHEN e.amount IS NOT NULL THEN e.amount ELSE 0 END) AS total_funding
        FROM events e
        WHERE {where_sql}
        GROUP BY e.company_name
        ORDER BY MAX(e.investment_date) DESC NULLS LAST
        LIMIT {limit}
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    return [dict(r) for r in rows]


async def investor_preferences(institution_id: int) -> dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        ind_rows = await conn.fetch(
            """
            SELECT industry, COUNT(*) AS n
            FROM events WHERE institution_id = $1 AND industry IS NOT NULL
            GROUP BY industry ORDER BY n DESC LIMIT 8
            """,
            institution_id,
        )
        round_rows = await conn.fetch(
            """
            SELECT round, COUNT(*) AS n
            FROM events WHERE institution_id = $1 AND round IS NOT NULL
            GROUP BY round ORDER BY n DESC LIMIT 8
            """,
            institution_id,
        )
        region_rows = await conn.fetch(
            """
            SELECT region, COUNT(*) AS n
            FROM events WHERE institution_id = $1 AND region IS NOT NULL
            GROUP BY region ORDER BY n DESC LIMIT 5
            """,
            institution_id,
        )
    return {
        "institution_id": institution_id,
        "top_industries": [dict(r) for r in ind_rows],
        "top_rounds": [dict(r) for r in round_rows],
        "top_regions": [dict(r) for r in region_rows],
    }


async def investor_exits(institution_id: int) -> list[dict[str, Any]]:
    """qmp events 没有 exit 字段；启发：找该机构投资过的公司，看它们后来有没有 IPO 轮次."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            WITH portfolio AS (
                SELECT DISTINCT company_name FROM events WHERE institution_id = $1
            )
            SELECT DISTINCT e.company_name, e.investment_date AS exit_date, e.round AS exit_round
            FROM events e
            JOIN portfolio p ON p.company_name = e.company_name
            WHERE e.round ILIKE '%IPO%' OR e.round ILIKE '%Pre-IPO%' OR e.round ILIKE '%上市%'
            ORDER BY e.investment_date DESC NULLS LAST
            LIMIT 30
            """,
            institution_id,
        )
    return [dict(r) for r in rows]


async def valuations_distribution(industry: str) -> dict[str, Any]:
    """估值带分布 + 独角兽阈值（按 valuation_amount_cny ≥ 70 亿 ≈ $1B）."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT valuation_amount_cny, latest_round
            FROM valuations
            WHERE industry ILIKE $1 AND valuation_amount_cny IS NOT NULL
            ORDER BY valuation_amount_cny ASC
            """,
            f"%{industry}%",
        )
    vals = [float(r["valuation_amount_cny"]) for r in rows]
    if not vals:
        return {"industry": industry, "n": 0, "warning": "no records"}
    n = len(vals)
    UNICORN_THRESHOLD_CNY = 7_000_000_000
    return {
        "industry": industry,
        "n": n,
        "min_cny": vals[0],
        "p25_cny": vals[n // 4],
        "median_cny": vals[n // 2],
        "p75_cny": vals[(3 * n) // 4],
        "max_cny": vals[-1],
        "unicorn_threshold_cny": UNICORN_THRESHOLD_CNY,
        "unicorn_count": sum(1 for v in vals if v >= UNICORN_THRESHOLD_CNY),
    }


async def valuations_compare(industry: str, markets: list[str]) -> dict[str, Any]:
    """跨市场对标 — 这里以 region 字段近似 market."""
    pool = await get_pool()
    out: dict[str, Any] = {"industry": industry, "by_market": {}}
    async with pool.acquire() as conn:
        for m in markets:
            row = await conn.fetchrow(
                """
                SELECT
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ps_ratio) AS ps_median,
                    AVG(ps_ratio) AS ps_mean,
                    COUNT(*) AS n
                FROM valuations
                WHERE industry ILIKE $1 AND region ILIKE $2 AND ps_ratio IS NOT NULL
                """,
                f"%{industry}%",
                f"%{m}%",
            )
            out["by_market"][m] = dict(row) if row and row["n"] else {"n": 0}
    return out
