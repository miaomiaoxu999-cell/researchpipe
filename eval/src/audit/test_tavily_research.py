"""Tavily Research API test — 验证 PRD research/sector 设计。

跑 2 个 query：
  1. "具身智能 2026 中国一级市场"
  2. "China innovative drug license-out 2026"
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from tavily import TavilyClient

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
OUT = ROOT / "output" / "audit"
OUT.mkdir(parents=True, exist_ok=True)

API_KEY = os.environ["TAVILY_API_KEY"]
client = TavilyClient(api_key=API_KEY)


def run_research(query: str, *, model: str = "auto") -> dict:
    started = time.time()
    try:
        # Try the modern .research() interface (returns request id)
        resp = client.research(input=query)
    except (AttributeError, TypeError):
        # SDK may have different signature; fall back to older interface
        try:
            resp = client.research(query)
        except Exception as e:
            return {"query": query, "error": f"submit: {type(e).__name__}: {e}"}

    rid = (resp or {}).get("request_id") if isinstance(resp, dict) else None
    if not rid:
        # Some SDK versions return result directly
        return {
            "query": query,
            "started_in_s": round(time.time() - started, 1),
            "result": resp,
        }

    # Poll
    polls = 0
    while polls < 20:
        polls += 1
        time.sleep(15)
        try:
            res = client.get_research(rid)
        except Exception as e:
            return {"query": query, "request_id": rid, "polls": polls, "poll_error": str(e)}
        if isinstance(res, dict) and res.get("status") in {"completed", "failed"}:
            return {
                "query": query,
                "request_id": rid,
                "polls": polls,
                "elapsed_s": round(time.time() - started, 1),
                "result": res,
            }
    return {"query": query, "request_id": rid, "polls": polls, "error": "timeout"}


QUERIES = [
    ("embodied_ai", "具身智能 2026 中国一级市场 融资 头部公司"),
    ("biotech_outbound", "China innovative drug license-out 2026 deal volume top players"),
]


def main():
    out = {}
    for tag, q in QUERIES:
        print(f"=== {tag}: {q!r} ===")
        attempts = 0
        last = None
        while attempts < 3:
            attempts += 1
            try:
                last = run_research(q)
                break
            except Exception as e:
                last = {"query": q, "error": f"attempt {attempts}: {type(e).__name__}: {e}"}
                time.sleep(5)
        d = last or {}
        out[tag] = d
        (OUT / f"tavily_research_{tag}.json").write_text(
            json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  → {'OK' if 'result' in d else 'FAIL'} ({d.get('elapsed_s', '?')}s)")
    (OUT / "tavily_research_summary.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
