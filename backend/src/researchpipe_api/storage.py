"""SQLite persistence for v3 P2: Idempotency cache + jobs queue + accounts.

设计：
  - Idempotency cache: 24h TTL, 替代内存 dict（重启不丢）
  - Jobs queue:        request_id → status / kind / result / error / submitted_at
  - Accounts:          api_keys / usage 计数 / billing 月累计
  - Watch:             watchlists + 上次 digest

DB 文件：~/projects/ResearchPipe/backend/researchpipe.db （sqlite3）
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parents[2] / "researchpipe.db"

_lock = asyncio.Lock()


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH, timeout=10.0, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    return c


def init_db():
    """Create tables on startup."""
    DB_PATH.parent.mkdir(exist_ok=True, parents=True)
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS idempotency (
                cache_key TEXT PRIMARY KEY,
                api_key TEXT NOT NULL,
                response_body BLOB NOT NULL,
                status_code INTEGER NOT NULL,
                content_type TEXT,
                created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_idem_created ON idempotency(created_at);

            CREATE TABLE IF NOT EXISTS jobs (
                request_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                result_json TEXT,
                error_json TEXT,
                submitted_at REAL NOT NULL,
                completed_at REAL
            );
            CREATE INDEX IF NOT EXISTS idx_jobs_submit ON jobs(submitted_at DESC);

            CREATE TABLE IF NOT EXISTS accounts (
                api_key TEXT PRIMARY KEY,
                plan TEXT DEFAULT 'Free',
                credits_limit INTEGER DEFAULT 100,
                credits_used_this_month INTEGER DEFAULT 0,
                plan_resets_on TEXT,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                credits_charged REAL NOT NULL,
                ts REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_usage_key_ts ON usage_log(api_key, ts);

            CREATE TABLE IF NOT EXISTS watchlists (
                id TEXT PRIMARY KEY,
                api_key TEXT NOT NULL,
                name TEXT NOT NULL,
                industries_json TEXT,
                company_ids_json TEXT,
                investor_ids_json TEXT,
                cron TEXT,
                last_digest_ts REAL,
                created_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_watchlists_key ON watchlists(api_key);
            """
        )


# ─────────────────────────────────────────────────────────────────────────
# Idempotency
# ─────────────────────────────────────────────────────────────────────────


async def idem_get(cache_key: str, *, ttl_s: int = 86400) -> dict | None:
    async with _lock:
        with _conn() as c:
            row = c.execute(
                "SELECT response_body, status_code, content_type, created_at FROM idempotency WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
    if not row:
        return None
    if time.time() - row["created_at"] > ttl_s:
        return None
    return {
        "body": row["response_body"],
        "status_code": row["status_code"],
        "content_type": row["content_type"],
    }


async def idem_set(cache_key: str, api_key: str, body: bytes, status_code: int, content_type: str):
    async with _lock:
        with _conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO idempotency (cache_key, api_key, response_body, status_code, content_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (cache_key, api_key, body, status_code, content_type, time.time()),
            )


async def idem_sweep(*, ttl_s: int = 86400):
    """Sweep expired entries."""
    cutoff = time.time() - ttl_s
    async with _lock:
        with _conn() as c:
            c.execute("DELETE FROM idempotency WHERE created_at < ?", (cutoff,))


# ─────────────────────────────────────────────────────────────────────────
# Jobs
# ─────────────────────────────────────────────────────────────────────────


async def job_create(request_id: str, kind: str):
    async with _lock:
        with _conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO jobs (request_id, kind, status, submitted_at) VALUES (?, ?, ?, ?)",
                (request_id, kind, "running", time.time()),
            )


async def job_complete(request_id: str, result: Any):
    async with _lock:
        with _conn() as c:
            c.execute(
                "UPDATE jobs SET status='completed', result_json=?, completed_at=? WHERE request_id=?",
                (json.dumps(result, ensure_ascii=False, default=str), time.time(), request_id),
            )


async def job_fail(request_id: str, error: dict):
    async with _lock:
        with _conn() as c:
            c.execute(
                "UPDATE jobs SET status='failed', error_json=?, completed_at=? WHERE request_id=?",
                (json.dumps(error, ensure_ascii=False), time.time(), request_id),
            )


async def job_get(request_id: str) -> dict | None:
    async with _lock:
        with _conn() as c:
            row = c.execute(
                "SELECT request_id, kind, status, result_json, error_json, submitted_at, completed_at FROM jobs WHERE request_id = ?",
                (request_id,),
            ).fetchone()
    if not row:
        return None
    out = dict(row)
    if out.get("result_json"):
        out["result"] = json.loads(out.pop("result_json"))
    if out.get("error_json"):
        out["error"] = json.loads(out.pop("error_json"))
    return out


# ─────────────────────────────────────────────────────────────────────────
# Accounts
# ─────────────────────────────────────────────────────────────────────────


def ensure_dev_account(api_key: str):
    """Insert a default account row if missing."""
    with _conn() as c:
        c.execute(
            """INSERT OR IGNORE INTO accounts (api_key, plan, credits_limit, credits_used_this_month, plan_resets_on, created_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
            (api_key, "Pro", 80000, 0, _next_month_reset(), time.time()),
        )


def _next_month_reset() -> str:
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    if now.month == 12:
        nxt = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        nxt = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return nxt.date().isoformat()


async def account_me(api_key: str) -> dict:
    async with _lock:
        with _conn() as c:
            row = c.execute(
                "SELECT plan, credits_limit, credits_used_this_month, plan_resets_on FROM accounts WHERE api_key = ?",
                (api_key,),
            ).fetchone()
    if not row:
        return {"api_key_prefix": (api_key[:8] + "...") if api_key else "", "plan": "Free", "credits_used_this_month": 0, "credits_limit": 100, "plan_resets_on": _next_month_reset()}
    return {
        "api_key_prefix": (api_key[:8] + "..."),
        "plan": row["plan"],
        "credits_used_this_month": row["credits_used_this_month"],
        "credits_limit": row["credits_limit"],
        "plan_resets_on": row["plan_resets_on"],
    }


async def usage_log(api_key: str, endpoint: str, credits: float):
    async with _lock:
        with _conn() as c:
            c.execute(
                "INSERT INTO usage_log (api_key, endpoint, credits_charged, ts) VALUES (?, ?, ?, ?)",
                (api_key, endpoint, credits, time.time()),
            )
            c.execute(
                "UPDATE accounts SET credits_used_this_month = credits_used_this_month + CAST(? AS INTEGER) WHERE api_key=?",
                (credits, api_key),
            )


async def usage_history(api_key: str, *, days: int = 30) -> list[dict]:
    cutoff = time.time() - days * 86400
    async with _lock:
        with _conn() as c:
            rows = c.execute(
                """SELECT date(ts, 'unixepoch') AS day, endpoint, COUNT(*) AS calls, SUM(credits_charged) AS credits
                FROM usage_log WHERE api_key = ? AND ts >= ?
                GROUP BY day, endpoint ORDER BY day DESC, credits DESC""",
                (api_key, cutoff),
            ).fetchall()
    return [{"date": r["day"], "endpoint": r["endpoint"], "calls": r["calls"], "credits": r["credits"]} for r in rows]


async def billing_estimate(api_key: str) -> dict:
    me = await account_me(api_key)
    PLAN_FEES = {"Free": 0, "Hobby": 99, "Starter": 1500, "Pro": 5000, "Enterprise": 15000, "Flagship": 30000}
    plan_fee = PLAN_FEES.get(me["plan"], 0)
    overage_credits = max(0, me["credits_used_this_month"] - me["credits_limit"])
    overage_fee = overage_credits * 0.05  # ¥0.05 per overage credit
    return {
        "month": _current_month(),
        "plan": me["plan"],
        "plan_fee_cny": plan_fee,
        "overage_credits": overage_credits,
        "overage_fee_cny": round(overage_fee, 2),
        "total_due_cny": round(plan_fee + overage_fee, 2),
    }


def _current_month() -> str:
    from datetime import datetime

    return datetime.utcnow().strftime("%Y-%m")


# ─────────────────────────────────────────────────────────────────────────
# Watchlists
# ─────────────────────────────────────────────────────────────────────────


async def watch_create(api_key: str, *, name: str, industries: list[str] | None, company_ids: list[str] | None, investor_ids: list[str] | None, cron: str | None) -> dict:
    import secrets

    wid = f"watch_{secrets.token_hex(6)}"
    async with _lock:
        with _conn() as c:
            c.execute(
                """INSERT INTO watchlists (id, api_key, name, industries_json, company_ids_json, investor_ids_json, cron, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    wid,
                    api_key,
                    name,
                    json.dumps(industries or [], ensure_ascii=False),
                    json.dumps(company_ids or [], ensure_ascii=False),
                    json.dumps(investor_ids or [], ensure_ascii=False),
                    cron,
                    time.time(),
                ),
            )
    return {"id": wid, "name": name, "cron": cron, "industries": industries or [], "company_ids": company_ids or [], "investor_ids": investor_ids or []}


async def watch_get(watch_id: str) -> dict | None:
    async with _lock:
        with _conn() as c:
            row = c.execute(
                "SELECT id, name, industries_json, company_ids_json, investor_ids_json, cron, last_digest_ts FROM watchlists WHERE id = ?",
                (watch_id,),
            ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "name": row["name"],
        "industries": json.loads(row["industries_json"]) if row["industries_json"] else [],
        "company_ids": json.loads(row["company_ids_json"]) if row["company_ids_json"] else [],
        "investor_ids": json.loads(row["investor_ids_json"]) if row["investor_ids_json"] else [],
        "cron": row["cron"],
        "last_digest_ts": row["last_digest_ts"],
    }


async def watch_mark_digest(watch_id: str):
    async with _lock:
        with _conn() as c:
            c.execute("UPDATE watchlists SET last_digest_ts=? WHERE id=?", (time.time(), watch_id))
