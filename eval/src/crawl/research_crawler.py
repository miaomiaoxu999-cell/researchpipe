"""扩量爬研报 — 5 赛道 × 10+ 篇 = 50+ PDFs.

策略：
  1. 用 Tavily Search 搜每个赛道 → 拿 50 条结果（含 PDF URL）
  2. 过滤 .pdf URL → 去重
  3. httpx 下载 → eval/data/research_corpus/<sector>/<sha8>.pdf
  4. pdfplumber 转文本 → eval/data/research_corpus/<sector>/<sha8>.md
  5. 出 manifest.json
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
import pdfplumber
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
CORPUS = ROOT / "data" / "research_corpus"
TARGETS = json.loads((ROOT / "data" / "crawl_targets.json").read_text(encoding="utf-8"))

TAVILY_KEY = os.environ["TAVILY_API_KEY"]
UA = "Mozilla/5.0 ResearchPipe-eval/0.2"
HEADERS = {"User-Agent": UA, "Accept": "application/pdf,*/*"}
TIMEOUT = 60.0
PER_SECTOR_TARGET = 10
MAX_RESULTS_PER_QUERY = 30


def search_pdfs(query: str) -> list[dict]:
    """Tavily Search → return PDF URLs."""
    try:
        r = httpx.post(
            "https://api.tavily.com/search",
            headers={"Authorization": f"Bearer {TAVILY_KEY}", "Content-Type": "application/json"},
            json={
                "query": query,
                "search_depth": "advanced",
                "max_results": MAX_RESULTS_PER_QUERY,
                "include_domains": ["dfcfw.com", "pdf.dfcfw.com", "caict.ac.cn", "miit.gov.cn", "ndrc.gov.cn", "cesi.cn", "csrc.gov.cn"],
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        results = r.json().get("results") or []
    except Exception:
        # fallback: no domain filter
        try:
            r = httpx.post(
                "https://api.tavily.com/search",
                headers={"Authorization": f"Bearer {TAVILY_KEY}", "Content-Type": "application/json"},
                json={"query": query, "search_depth": "advanced", "max_results": MAX_RESULTS_PER_QUERY},
                timeout=TIMEOUT,
            )
            r.raise_for_status()
            results = r.json().get("results") or []
        except Exception:
            return []
    return [r for r in results if (r.get("url") or "").lower().endswith(".pdf")]


def slug(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:8]


def download(url: str, dest: Path) -> tuple[bool, int]:
    if dest.exists() and dest.stat().st_size > 1024:
        return True, dest.stat().st_size
    try:
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers=HEADERS) as cli:
            r = cli.get(url)
            if r.status_code != 200:
                return False, r.status_code
            if len(r.content) < 1024:
                return False, len(r.content)
            dest.write_bytes(r.content)
            return True, len(r.content)
    except Exception:
        return False, 0


def parse_pdf(pdf_path: Path) -> str:
    chunks = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Cap at 50 pages to bound time
            for page in pdf.pages[:50]:
                t = page.extract_text() or ""
                chunks.append(t)
        return "\n\n".join(chunks)
    except Exception:
        return ""


def main():
    manifest: dict[str, list[dict]] = {}
    total_ok = 0
    for sector, query in TARGETS["research_sectors"].items():
        sec_dir = CORPUS / sector
        sec_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n=== {sector} :: {query!r} ===")
        # Multiple queries to get ~10 PDFs per sector
        results: list[dict] = []
        seen: set[str] = set()
        for q_variant in [query, query.split(" ")[0] + " 行业研究 PDF", query.replace("PDF", "深度报告")]:
            for r in search_pdfs(q_variant):
                u = r.get("url")
                if u and u not in seen:
                    seen.add(u)
                    results.append(r)
            if len(results) >= PER_SECTOR_TARGET:
                break

        sec_records = []
        for r in results[: PER_SECTOR_TARGET * 2]:  # try up to 2x to allow for download failures
            url = r["url"]
            sg = slug(url)
            pdf_path = sec_dir / f"{sg}.pdf"
            md_path = sec_dir / f"{sg}.md"
            ok, size = download(url, pdf_path)
            if not ok:
                print(f"  [FAIL DL] {url[:80]} ({size})")
                continue
            text = parse_pdf(pdf_path)
            md_path.write_text(text, encoding="utf-8")
            sec_records.append(
                {
                    "id": sg,
                    "url": url,
                    "title": r.get("title", "")[:200],
                    "score": r.get("score"),
                    "size_bytes": size,
                    "text_chars": len(text),
                }
            )
            total_ok += 1
            print(f"  [OK] {sg} {size:>8} B {len(text):>7} chars  {r.get('title', '')[:50]}")
            if len(sec_records) >= PER_SECTOR_TARGET:
                break
            time.sleep(0.5)

        manifest[sector] = sec_records

    out_path = CORPUS / "manifest.json"
    out_path.write_text(
        json.dumps(
            {
                "n_total": total_ok,
                "by_sector": {k: len(v) for k, v in manifest.items()},
                "items": manifest,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nTOTAL: {total_ok} PDFs across {len(manifest)} sectors → {out_path}")


if __name__ == "__main__":
    main()
