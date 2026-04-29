"""A 线渠道 smoke test —— 同 query 横向跑 Tavily / Bocha / Serper / Jina。

每个渠道拉 5 条结果 + 1 个 PDF extract（如 Tavily）。
输出 output/audit/a_layer_<channel>.json。
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
OUT_DIR = ROOT / "output" / "audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TAVILY_KEY = os.environ["TAVILY_API_KEY"]
BOCHA_KEY = os.environ["BOCHA_API_KEY"]
SERPER_KEY = os.environ["SERPER_API_KEY"]
JINA_KEY = os.environ.get("JINA_API_KEY")

QUERY_CN = "具身智能 融资 2026"
QUERY_EN = "China innovative drug license-out 2026"
PDF_URL = "https://pdf.dfcfw.com/pdf/H3_AP202602051819786211_1.pdf"
HTML_URL = "https://www.goldmansachs.com/insights/articles/china-is-increasing-its-share-of-global-drug-development"

UA = "Mozilla/5.0 ResearchPipe-eval/0.1"
TIMEOUT = 60.0


def _save(name: str, payload: dict):
    p = OUT_DIR / f"a_{name}.json"
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def tavily_search(query: str, *, depth: str = "basic") -> dict:
    t0 = time.time()
    r = httpx.post(
        "https://api.tavily.com/search",
        headers={"Authorization": f"Bearer {TAVILY_KEY}", "Content-Type": "application/json"},
        json={
            "query": query,
            "search_depth": depth,
            "max_results": 5,
            "include_answer": True,
        },
        timeout=TIMEOUT,
    )
    elapsed = round(time.time() - t0, 2)
    return {
        "channel": "tavily-search",
        "query": query,
        "depth": depth,
        "status_code": r.status_code,
        "elapsed_s": elapsed,
        "body": r.json() if r.status_code == 200 else r.text,
    }


def tavily_extract(url: str) -> dict:
    t0 = time.time()
    r = httpx.post(
        "https://api.tavily.com/extract",
        headers={"Authorization": f"Bearer {TAVILY_KEY}", "Content-Type": "application/json"},
        json={"urls": [url], "extract_depth": "advanced"},
        timeout=TIMEOUT,
    )
    elapsed = round(time.time() - t0, 2)
    body = r.json() if r.status_code == 200 else r.text
    # Truncate huge content for readability
    if isinstance(body, dict) and "results" in body:
        for it in body.get("results") or []:
            if isinstance(it.get("raw_content"), str) and len(it["raw_content"]) > 3000:
                it["raw_content_full_chars"] = len(it["raw_content"])
                it["raw_content"] = it["raw_content"][:3000] + "...[truncated]"
    return {
        "channel": "tavily-extract",
        "url": url,
        "status_code": r.status_code,
        "elapsed_s": elapsed,
        "body": body,
    }


def bocha_search(query: str) -> dict:
    t0 = time.time()
    r = httpx.post(
        "https://api.bochaai.com/v1/web-search",
        headers={"Authorization": f"Bearer {BOCHA_KEY}", "Content-Type": "application/json"},
        json={"query": query, "freshness": "noLimit", "summary": True, "count": 5},
        timeout=TIMEOUT,
    )
    elapsed = round(time.time() - t0, 2)
    return {
        "channel": "bocha",
        "query": query,
        "status_code": r.status_code,
        "elapsed_s": elapsed,
        "body": r.json() if r.status_code == 200 else r.text,
    }


def serper_search(query: str, gl: str = "cn", hl: str = "zh-cn") -> dict:
    t0 = time.time()
    r = httpx.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
        json={"q": query, "num": 5, "gl": gl, "hl": hl},
        timeout=TIMEOUT,
    )
    elapsed = round(time.time() - t0, 2)
    return {
        "channel": "serper",
        "query": query,
        "gl": gl,
        "status_code": r.status_code,
        "elapsed_s": elapsed,
        "body": r.json() if r.status_code == 200 else r.text,
    }


def jina_reader(url: str) -> dict:
    t0 = time.time()
    headers = {"Accept": "application/json", "User-Agent": UA}
    if JINA_KEY:
        headers["Authorization"] = f"Bearer {JINA_KEY}"
    r = httpx.get(f"https://r.jina.ai/{url}", headers=headers, timeout=TIMEOUT, follow_redirects=True)
    elapsed = round(time.time() - t0, 2)
    body = None
    try:
        body = r.json()
        if isinstance(body, dict) and "data" in body:
            d = body["data"]
            if isinstance(d, dict) and isinstance(d.get("content"), str) and len(d["content"]) > 3000:
                d["content_full_chars"] = len(d["content"])
                d["content"] = d["content"][:3000] + "...[truncated]"
    except Exception:
        body = r.text[:1500]
    return {
        "channel": "jina-reader",
        "url": url,
        "status_code": r.status_code,
        "elapsed_s": elapsed,
        "body": body,
    }


def main():
    runs = [
        ("tavily_search_cn", lambda: tavily_search(QUERY_CN)),
        ("tavily_search_en", lambda: tavily_search(QUERY_EN)),
        ("tavily_search_advanced_cn", lambda: tavily_search(QUERY_CN, depth="advanced")),
        ("tavily_extract_pdf", lambda: tavily_extract(PDF_URL)),
        ("tavily_extract_html", lambda: tavily_extract(HTML_URL)),
        ("bocha_cn", lambda: bocha_search(QUERY_CN)),
        ("bocha_en", lambda: bocha_search(QUERY_EN)),
        ("serper_cn", lambda: serper_search(QUERY_CN, gl="cn", hl="zh-cn")),
        ("serper_en", lambda: serper_search(QUERY_EN, gl="us", hl="en")),
        ("jina_html", lambda: jina_reader(HTML_URL)),
    ]
    summary = []
    for name, fn in runs:
        print(f"=== {name} ===")
        try:
            out = fn()
        except Exception as e:
            out = {"channel": name, "error": str(e)}
        p = _save(name, out)
        sc = out.get("status_code", "ERR")
        el = out.get("elapsed_s", "?")
        flag = "OK" if sc == 200 else f"FAIL {sc}"
        print(f"  {flag} {el}s → {p.name}")
        summary.append({"name": name, "status_code": sc, "elapsed_s": el})
    _save("_summary", {"runs": summary})


if __name__ == "__main__":
    main()
