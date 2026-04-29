"""调真后端跑 50 端点，对比 response shape 与 frontend mocks 期望.

输出：~/projects/ResearchPipe/playground_shape_audit.md
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]
BACKEND_URL = "http://localhost:3725"
API_KEY = "rp-demo-public"
TIMEOUT = 90.0

# Read frontend endpoint metadata
FRONTEND_ENDPOINTS_TS = ROOT / "frontend" / "src" / "lib" / "endpoints.ts"


def parse_frontend_endpoints() -> list[dict[str, Any]]:
    """Quick & dirty parse of TS metadata — just need (id, path, method, params)."""
    text = FRONTEND_ENDPOINTS_TS.read_text(encoding="utf-8")
    # Each endpoint has: id: "...", code, name, path: "GET /v1/..." or "POST /v1/..."
    pattern = re.compile(r'\{\s*id:\s*"([^"]+)"[^}]*?path:\s*"([A-Z]+)\s+([^"]+)"', re.DOTALL)
    out = []
    for m in pattern.finditer(text):
        out.append({"id": m.group(1), "method": m.group(2), "path": m.group(3)})
    return out


# Default body for endpoints that need params
DEFAULT_BODIES: dict[str, dict[str, Any]] = {
    "search": {"query": "具身智能 2026", "max_results": 3},
    "extract": {"url": "https://en.wikipedia.org/wiki/Test"},
    "extract-research": {"url": "https://www.goldmansachs.com/insights/articles/china-is-increasing-its-share-of-global-drug-development"},
    "extract-filing": {"url": "https://example.com/prospectus.pdf", "schema": "prospectus_v1"},
    "extract-batch": {"urls": ["https://example.com/a"]},
    "research-sector": {"input": "新能源汽车", "time_range": "12m"},
    "research-company": {"input": "智元机器人"},
    "research-valuation": {"input": "动力电池"},
    "companies-search": {"query": "智元", "limit": 3},
    "companies-peers": {"n": 3},
    "investors-search": {"query": "高瓴", "limit": 3},
    "deals-search": {"industry": "人工智能", "time_range": "30d", "limit": 3},
    "deals-timeline": {"company_id": "智元机器人"},
    "deals-overseas": {"industry": "AI", "country": "us"},
    "industries-search": {"query": "人工智能"},
    "industries-maturity": {"id": "ind_ai"},
    "technologies-compare": {"tech_a": "Tesla Optimus", "tech_b": "Figure 01"},
    "valuations-search": {"industry": "人工智能"},
    "valuations-multiples": {"industry": "人工智能"},
    "valuations-compare": {"industry": "人工智能", "markets": ["a-share"]},
    "valuations-distribution": {"industry": "人工智能"},
    "filings-search": {"company_id": "智元", "filing_type": "any", "time_range": "12m", "limit": 3},
    "filings-extract": {"url": "https://example.com/x.pdf", "schema": "prospectus_v1"},
    "filings-risks": {"url": "https://example.com/x.pdf"},
    "filings-financials": {"url": "https://example.com/x.pdf"},
    "news-search": {"query": "AI 投资", "limit": 3},
    "news-recent": {"industry": "AI", "limit": 3},
    "events-timeline": {"company_id": "智元机器人"},
    "screen": {"industry": "人工智能", "limit": 5},
    "watch-create": {"name": "test", "industries": ["AI"], "cron": "0 8 * * *"},
}


def fill_path(path: str, ep_id: str) -> str:
    """Replace {param} placeholders with sample IDs."""
    samples = {
        "{cid}": "智元机器人",
        "{iid}": "1",
        "{did}": "1",
        "{fid}": "fil_test",
        "{ind}": "人工智能",
        "{wid}": "watch_test",
        "{id}": "test_id",
        "{job_id}": "req_test",
    }
    for placeholder, value in samples.items():
        path = path.replace(placeholder, value)
    return path


def run_one(ep: dict[str, Any], cli: httpx.Client) -> dict[str, Any]:
    """Call one endpoint, return result."""
    path = fill_path(ep["path"], ep["id"])
    method = ep["method"]
    body = DEFAULT_BODIES.get(ep["id"]) if method == "POST" else None
    params = DEFAULT_BODIES.get(ep["id"]) if method == "GET" else None

    started = time.time()
    try:
        if method == "POST":
            resp = cli.post(f"{BACKEND_URL}{path}", json=body or {})
        else:
            resp = cli.get(f"{BACKEND_URL}{path}", params=params)
        elapsed = round((time.time() - started) * 1000, 1)
    except Exception as e:
        return {**ep, "error": f"{type(e).__name__}: {e}", "elapsed_ms": round((time.time() - started) * 1000, 1)}

    status = resp.status_code
    try:
        data = resp.json()
    except Exception:
        data = {"_raw": resp.text[:500]}

    md = (data.get("metadata") if isinstance(data, dict) else None) or {}
    return {
        **ep,
        "status_code": status,
        "elapsed_ms": elapsed,
        "data_sources": md.get("data_sources_used", []),
        "credits_charged": md.get("credits_charged"),
        "has_metadata": "metadata" in (data or {}),
        "top_keys": list((data or {}).keys())[:8],
        "error": None if 200 <= status < 300 else (data if isinstance(data, dict) else str(data)[:200]),
    }


def main():
    endpoints = parse_frontend_endpoints()
    print(f"Found {len(endpoints)} frontend endpoints")

    cli = httpx.Client(
        timeout=TIMEOUT,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    )
    rows = []
    for i, ep in enumerate(endpoints, 1):
        print(f"[{i}/{len(endpoints)}] {ep['method']} {ep['path']}", end=" ... ", flush=True)
        result = run_one(ep, cli)
        ok = result.get("error") is None and 200 <= (result.get("status_code") or 0) < 300
        flag = "✅" if ok else "❌"
        print(f"{flag} {result.get('status_code')} ({result.get('elapsed_ms')}ms)")
        rows.append(result)

    # Summary
    n_total = len(rows)
    n_ok = sum(1 for r in rows if r.get("status_code", 0) and 200 <= r["status_code"] < 300 and r.get("error") is None)

    out = ROOT / "playground_shape_audit.md"
    lines = [
        "# Playground Real Backend 50 端点 audit",
        "",
        f"**日期**: 2026-04-29",
        f"**Backend**: {BACKEND_URL}",
        f"**Total**: {n_total}",
        f"**OK**: {n_ok}",
        f"**Failed**: {n_total - n_ok}",
        "",
        "## 端点矩阵",
        "",
        "| # | Method | Path | Status | ms | Sources | Credits | Top keys | Error |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, 1):
        err_summary = ""
        if r.get("error"):
            err_summary = (str(r["error"])[:80]).replace("|", "/").replace("\n", " ")
        keys = ",".join(r.get("top_keys") or [])[:50]
        sources = ",".join(r.get("data_sources") or []) if isinstance(r.get("data_sources"), list) else "—"
        flag = "✅" if not r.get("error") else "❌"
        lines.append(
            f"| {i} | {r['method']} | `{r['path']}` | {flag} {r.get('status_code', 'ERR')} | "
            f"{r.get('elapsed_ms', '?')} | {sources or '—'} | {r.get('credits_charged', '—')} | "
            f"{keys} | {err_summary} |"
        )

    # Failed details
    failed = [r for r in rows if r.get("error") or (r.get("status_code") or 0) >= 400]
    if failed:
        lines += ["", "## 失败明细", ""]
        for r in failed:
            lines.append(f"### {r['method']} {r['path']}")
            lines.append("```json")
            lines.append(json.dumps(r.get("error") or {"status": r.get("status_code")}, ensure_ascii=False, indent=2)[:2000])
            lines.append("```")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {out}")
    print(f"Summary: {n_ok}/{n_total} ok")
    cli.close()


if __name__ == "__main__":
    main()
