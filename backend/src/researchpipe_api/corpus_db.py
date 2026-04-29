"""researchpipe_postgres access layer — corpus_files queries.

Separate pool from qmp_data (different DSN, different DB).
"""
from __future__ import annotations

from datetime import date
from typing import Any

import asyncpg

from .aliases import build_industry_where_clause, expand
from .settings import RP_PG_DSN

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(RP_PG_DSN, min_size=1, max_size=4, command_timeout=10.0)
    return _pool


async def close_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def _escape_like(s: str) -> str:
    """Escape % and _ to prevent ILIKE wildcard scanning by malicious input."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def is_alive() -> bool:
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────
# Corpus search
# ─────────────────────────────────────────────────────────────────────────


async def corpus_search(
    *,
    query: str | None = None,
    broker: str | None = None,
    industry: str | None = None,
    week: str | None = None,
    library: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Filter + rank corpus_files. Title uses pg_trgm similarity for ranking when query provided."""
    pool = await get_pool()
    where_clauses: list[str] = []
    params: list[Any] = []

    if query:
        # ILIKE for filtering (uses gin_trgm_ops index for partial matches);
        # similarity() used in ORDER BY for ranking.
        # Escape % and _ so users / LLM can't pass wildcards to scan the table.
        params.append(f"%{_escape_like(query)}%")
        where_clauses.append(f"title ILIKE ${len(params)}")

    if broker:
        params.append(broker)
        where_clauses.append(f"broker = ${len(params)}")

    if industry:
        # Try alias expansion: if "具身智能" → match any of {"具身智能","机器人",...}
        exp = expand(industry)
        candidates = list({industry, *exp.get("industries", []), *exp.get("sub_industries", [])})
        params.append(candidates)
        where_clauses.append(f"industry_tags && ${len(params)}::text[]")

    if week:
        params.append(week)
        where_clauses.append(f"week = ${len(params)}")

    if library:
        params.append(f"%{_escape_like(library)}%")
        where_clauses.append(f"library ILIKE ${len(params)}")

    if date_from:
        params.append(date_from)
        where_clauses.append(f"report_date >= ${len(params)}")

    if date_to:
        params.append(date_to)
        where_clauses.append(f"report_date <= ${len(params)}")

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # Snapshot count_params BEFORE appending ranking/limit/offset — fragility-free.
    count_params: list[Any] = list(params)

    # Ranking: trigram similarity first (when query), then date desc
    order_sql = "ORDER BY report_date DESC NULLS LAST, id DESC"
    if query:
        params.append(query)
        order_sql = (
            f"ORDER BY similarity(title, ${len(params)}::text) DESC, "
            "report_date DESC NULLS LAST, id DESC"
        )

    params.append(limit)
    params.append(offset)
    sql = f"""
        SELECT id, week, library, title, broker, report_date, pages,
               industry_tags, file_path, file_size, filename_pattern
        FROM corpus_files
        {where_sql}
        {order_sql}
        LIMIT ${len(params) - 1} OFFSET ${len(params)}
    """
    count_sql = f"SELECT count(*) FROM corpus_files {where_sql}"

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
        total = await conn.fetchval(count_sql, *count_params)

    return {
        "total": int(total or 0),
        "results": [_row_to_dict(r) for r in rows],
    }


def _row_to_dict(r: asyncpg.Record) -> dict[str, Any]:
    return {
        "id": r["id"],
        "week": r["week"],
        "library": r["library"],
        "title": r["title"],
        "broker": r["broker"],
        "report_date": r["report_date"].isoformat() if r["report_date"] else None,
        "pages": r["pages"],
        "industry_tags": list(r["industry_tags"] or []),
        "file_path": r["file_path"],
        "file_size": r["file_size"],
        "filename_pattern": r["filename_pattern"],
    }


# ─────────────────────────────────────────────────────────────────────────
# Stats
# ─────────────────────────────────────────────────────────────────────────


async def semantic_search(
    query_embedding: list[float],
    *,
    candidate_top_k: int = 50,
    industry: str | None = None,
    broker: str | None = None,
    week: str | None = None,
) -> list[dict[str, Any]]:
    """ANN search via pgvector cosine. Returns candidate_top_k chunks with file metadata."""
    pool = await get_pool()

    # Build optional WHERE on join with corpus_files
    where_clauses: list[str] = []
    params: list[Any] = []
    if industry:
        exp = expand(industry)
        candidates = list({industry, *exp.get("industries", []), *exp.get("sub_industries", [])})
        params.append(candidates)
        where_clauses.append(f"f.industry_tags && ${len(params)}::text[]")
    if broker:
        params.append(broker)
        where_clauses.append(f"f.broker = ${len(params)}")
    if week:
        params.append(week)
        where_clauses.append(f"f.week = ${len(params)}")
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # Embedding param goes last (so positional indexing matches)
    vec_literal = "[" + ",".join(f"{x:.6f}" for x in query_embedding) + "]"
    params.append(vec_literal)
    params.append(candidate_top_k)

    sql = f"""
        SELECT
            c.id AS chunk_id, c.file_id, c.chunk_idx, c.page_no, c.content, c.token_count,
            f.title, f.broker, f.report_date, f.pages, f.industry_tags, f.file_path,
            f.week, f.library,
            1 - (c.embedding <=> ${len(params) - 1}::vector) AS cosine_sim
        FROM corpus_chunks c
        JOIN corpus_files f ON c.file_id = f.id
        {where_sql}
        ORDER BY c.embedding <=> ${len(params) - 1}::vector
        LIMIT ${len(params)}
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)
    return [
        {
            "chunk_id": r["chunk_id"],
            "file_id": r["file_id"],
            "chunk_idx": r["chunk_idx"],
            "page_no": r["page_no"],
            "content": r["content"],
            "token_count": r["token_count"],
            "title": r["title"],
            "broker": r["broker"],
            "report_date": r["report_date"].isoformat() if r["report_date"] else None,
            "pages": r["pages"],
            "industry_tags": list(r["industry_tags"] or []),
            "file_path": r["file_path"],
            "week": r["week"],
            "library": r["library"],
            "cosine_sim": float(r["cosine_sim"]),
        }
        for r in rows
    ]


async def corpus_stats() -> dict[str, Any]:
    """Aggregate counts: total / by broker / by industry / by week / by library."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT count(*) FROM corpus_files")
        n_broker = await conn.fetchval(
            "SELECT count(*) FROM corpus_files WHERE broker IS NOT NULL"
        )
        n_dated = await conn.fetchval(
            "SELECT count(*) FROM corpus_files WHERE report_date IS NOT NULL"
        )
        brokers = await conn.fetch(
            """
            SELECT broker, count(*) AS n FROM corpus_files
            WHERE broker IS NOT NULL
            GROUP BY broker ORDER BY n DESC LIMIT 20
            """
        )
        industries = await conn.fetch(
            """
            SELECT unnest(industry_tags) AS tag, count(*) AS n FROM corpus_files
            GROUP BY tag ORDER BY n DESC
            """
        )
        weeks = await conn.fetch(
            "SELECT week, count(*) AS n FROM corpus_files GROUP BY week ORDER BY week"
        )
        libraries = await conn.fetch(
            "SELECT library, count(*) AS n FROM corpus_files GROUP BY library ORDER BY n DESC"
        )

    return {
        "total": int(total or 0),
        "with_broker": int(n_broker or 0),
        "with_date": int(n_dated or 0),
        "top_brokers": [{"broker": r["broker"], "count": r["n"]} for r in brokers],
        "industries": [{"tag": r["tag"], "count": r["n"]} for r in industries],
        "weeks": [{"week": r["week"], "count": r["n"]} for r in weeks],
        "libraries": [{"library": r["library"], "count": r["n"]} for r in libraries],
    }
