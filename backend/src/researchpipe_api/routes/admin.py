"""Admin console endpoints — protected by X-Admin-Key header.

Auth is intentionally simple: a single env-configured admin key. Per-admin
identity / RBAC can come later. Mounted at /v1/admin/*.
"""
from __future__ import annotations

import logging
import os
import secrets
import time
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, Header, HTTPException

from .. import corpus_db
from ..storage import _conn

log = logging.getLogger(__name__)

ADMIN_KEY = os.environ.get("RP_ADMIN_KEY", "")  # required for any /v1/admin/* call


def require_admin(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> None:
    if not ADMIN_KEY:
        raise HTTPException(503, "RP_ADMIN_KEY not configured on server")
    if not x_admin_key or x_admin_key != ADMIN_KEY:
        raise HTTPException(401, "invalid or missing X-Admin-Key")


router = APIRouter(prefix="/v1/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# ─────────────────────────────────────────────────────────────────────────
# Overview
# ─────────────────────────────────────────────────────────────────────────


@router.get("/overview")
async def overview():
    """Dashboard summary: accounts / usage / corpus / jobs."""
    with _conn() as c:
        n_accounts = c.execute("SELECT count(*) AS n FROM accounts").fetchone()["n"]
        n_usage_total = c.execute("SELECT count(*) AS n FROM usage_log").fetchone()["n"]
        n_usage_24h = c.execute(
            "SELECT count(*) AS n FROM usage_log WHERE ts >= ?", (time.time() - 86400,)
        ).fetchone()["n"]
        credits_24h = c.execute(
            "SELECT COALESCE(SUM(credits_charged), 0) AS s FROM usage_log WHERE ts >= ?",
            (time.time() - 86400,),
        ).fetchone()["s"]
        n_jobs = c.execute("SELECT count(*) AS n FROM jobs").fetchone()["n"]
        jobs_by_status = {
            r["status"]: r["n"]
            for r in c.execute("SELECT status, count(*) AS n FROM jobs GROUP BY status").fetchall()
        }
        n_watchlists = c.execute("SELECT count(*) AS n FROM watchlists").fetchone()["n"]

    # Corpus (PG)
    pool = await corpus_db.get_pool()
    async with pool.acquire() as cn:
        n_files = await cn.fetchval("SELECT count(*) FROM corpus_files")
        n_chunks = await cn.fetchval("SELECT count(*) FROM corpus_chunks")
        embed_status = {
            r["embed_status"]: r["n"]
            for r in await cn.fetch(
                "SELECT embed_status, count(*) AS n FROM corpus_files GROUP BY embed_status"
            )
        }

    return {
        "accounts": {"total": n_accounts},
        "usage": {
            "total_calls": n_usage_total,
            "calls_24h": n_usage_24h,
            "credits_24h": float(credits_24h or 0),
        },
        "jobs": {"total": n_jobs, "by_status": jobs_by_status},
        "watchlists": {"total": n_watchlists},
        "corpus": {
            "files": int(n_files or 0),
            "chunks": int(n_chunks or 0),
            "embed_status": embed_status,
        },
    }


# ─────────────────────────────────────────────────────────────────────────
# Accounts
# ─────────────────────────────────────────────────────────────────────────


@router.get("/accounts")
async def list_accounts():
    with _conn() as c:
        rows = c.execute(
            """
            SELECT a.api_key, a.plan, a.credits_limit, a.credits_used_this_month,
                   a.plan_resets_on, a.created_at,
                   COALESCE(u.calls_24h, 0) AS calls_24h,
                   COALESCE(u.calls_total, 0) AS calls_total
            FROM accounts a
            LEFT JOIN (
                SELECT api_key,
                       SUM(CASE WHEN ts >= ? THEN 1 ELSE 0 END) AS calls_24h,
                       count(*) AS calls_total
                FROM usage_log GROUP BY api_key
            ) u ON a.api_key = u.api_key
            ORDER BY a.created_at DESC
            """,
            (time.time() - 86400,),
        ).fetchall()
    return {"accounts": [_mask_key_in_row(dict(r)) for r in rows]}


@router.post("/accounts")
async def create_account(body: dict):
    """Create a new account with auto-generated key. Body: {plan, credits_limit, label?}."""
    plan = body.get("plan") or "Free"
    credits_limit = int(body.get("credits_limit") or 100)
    new_key = f"rp-{secrets.token_urlsafe(20)}"
    with _conn() as c:
        c.execute(
            """
            INSERT INTO accounts (api_key, plan, credits_limit, credits_used_this_month, plan_resets_on, created_at)
            VALUES (?, ?, ?, 0, date('now', 'start of month', '+1 month'), ?)
            """,
            (new_key, plan, credits_limit, time.time()),
        )
    log.info("admin: created account %s", new_key[:8])
    return {"api_key": new_key, "plan": plan, "credits_limit": credits_limit}


@router.delete("/accounts/{api_key}")
async def delete_account(api_key: str):
    # Protect canonical demo / dev keys from accidental delete.
    from ..settings import RP_DEV_API_KEY, RP_DEMO_API_KEY
    if api_key in {RP_DEV_API_KEY, RP_DEMO_API_KEY}:
        raise HTTPException(400, "cannot delete protected key")
    with _conn() as c:
        n = c.execute("DELETE FROM accounts WHERE api_key = ?", (api_key,)).rowcount
    log.info("admin: deleted account %s (rows=%s)", api_key[:8], n)
    return {"deleted": n}


# ─────────────────────────────────────────────────────────────────────────
# Usage
# ─────────────────────────────────────────────────────────────────────────


@router.get("/usage/by_endpoint")
async def usage_by_endpoint(hours: int = 24):
    since = time.time() - hours * 3600
    with _conn() as c:
        rows = c.execute(
            """
            SELECT endpoint,
                   count(*) AS calls,
                   ROUND(SUM(credits_charged), 2) AS credits
            FROM usage_log WHERE ts >= ?
            GROUP BY endpoint ORDER BY calls DESC LIMIT 50
            """,
            (since,),
        ).fetchall()
    return {"hours": hours, "rows": [dict(r) for r in rows]}


@router.get("/usage/by_day")
async def usage_by_day(days: int = 14):
    since = time.time() - days * 86400
    with _conn() as c:
        rows = c.execute(
            """
            SELECT date(ts, 'unixepoch') AS day,
                   count(*) AS calls,
                   ROUND(SUM(credits_charged), 2) AS credits
            FROM usage_log WHERE ts >= ?
            GROUP BY day ORDER BY day DESC
            """,
            (since,),
        ).fetchall()
    return {"days": days, "rows": [dict(r) for r in rows]}


@router.get("/usage/recent")
async def usage_recent(limit: int = 100):
    with _conn() as c:
        rows = c.execute(
            """
            SELECT api_key, endpoint, credits_charged, ts FROM usage_log
            ORDER BY ts DESC LIMIT ?
            """,
            (min(int(limit), 500),),
        ).fetchall()
    return {"rows": [_mask_key_in_row(dict(r)) for r in rows]}


# ─────────────────────────────────────────────────────────────────────────
# Jobs
# ─────────────────────────────────────────────────────────────────────────


@router.get("/jobs/recent")
async def jobs_recent(limit: int = 50):
    with _conn() as c:
        rows = c.execute(
            """
            SELECT request_id, kind, status, submitted_at, completed_at,
                   substr(COALESCE(error_json, ''), 1, 200) AS error_preview
            FROM jobs ORDER BY submitted_at DESC LIMIT ?
            """,
            (min(int(limit), 200),),
        ).fetchall()
    return {"rows": [dict(r) for r in rows]}


# ─────────────────────────────────────────────────────────────────────────
# Corpus
# ─────────────────────────────────────────────────────────────────────────


@router.get("/corpus/health")
async def corpus_health():
    pool = await corpus_db.get_pool()
    async with pool.acquire() as cn:
        files_total = await cn.fetchval("SELECT count(*) FROM corpus_files")
        embed_status = {
            r["embed_status"]: r["n"]
            for r in await cn.fetch(
                "SELECT embed_status, count(*) AS n FROM corpus_files GROUP BY embed_status"
            )
        }
        chunks_total = await cn.fetchval("SELECT count(*) FROM corpus_chunks")
        broker_top10 = [
            {"broker": r["broker"], "n": r["n"]}
            for r in await cn.fetch(
                "SELECT broker, count(*) AS n FROM corpus_files WHERE broker IS NOT NULL GROUP BY broker ORDER BY n DESC LIMIT 10"
            )
        ]
        recent_failed = [
            {"id": r["id"], "title": r["title"], "embed_error": r["embed_error"]}
            for r in await cn.fetch(
                "SELECT id, title, embed_error FROM corpus_files WHERE embed_status = 'failed' ORDER BY embedded_at DESC LIMIT 20"
            )
        ]
        # Pattern distribution
        patterns = {
            r["filename_pattern"]: r["n"]
            for r in await cn.fetch(
                "SELECT filename_pattern, count(*) AS n FROM corpus_files GROUP BY filename_pattern ORDER BY n DESC"
            )
        }
    return {
        "files_total": int(files_total or 0),
        "chunks_total": int(chunks_total or 0),
        "embed_status": embed_status,
        "broker_top10": broker_top10,
        "recent_failed": recent_failed,
        "filename_patterns": patterns,
    }


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────


def _mask_key_in_row(row: dict) -> dict:
    """Mask api_key middle for safer display: rp-abc...xyz"""
    if "api_key" in row and isinstance(row["api_key"], str):
        k = row["api_key"]
        if len(k) > 12:
            row["api_key_masked"] = f"{k[:6]}...{k[-4:]}"
            row["api_key"] = row.get("api_key_masked")
        else:
            row["api_key_masked"] = k
    return row
