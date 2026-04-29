"""政策库爬取 — 100+ 篇公开政策 PDF.

来源：发改委 / 工信部 / 证监会 公开政策。用 Tavily 搜 + filter .pdf。
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import httpx
import pdfplumber
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
CORPUS = ROOT / "data" / "policy_corpus"
TARGETS = json.loads((ROOT / "data" / "crawl_targets.json").read_text(encoding="utf-8"))

TAVILY_KEY = os.environ["TAVILY_API_KEY"]
UA = "Mozilla/5.0 ResearchPipe-eval/0.2"
HEADERS = {"User-Agent": UA, "Accept": "application/pdf,*/*"}
TIMEOUT = 60.0
PER_TOPIC_TARGET = 15


_NOISE_KEYWORDS = ("股份有限公司", "招股", "问询", "发行股票", "回复", "保荐", "回函")


def _is_real_policy(title: str) -> bool:
    """证监会站点会混入招股书 / 问询函 — title 关键词过滤掉公司文档."""
    t = title or ""
    return not any(k in t for k in _NOISE_KEYWORDS)


def search_policy_pdfs(query: str) -> list[dict]:
    try:
        r = httpx.post(
            "https://api.tavily.com/search",
            headers={"Authorization": f"Bearer {TAVILY_KEY}", "Content-Type": "application/json"},
            json={
                "query": query,
                "search_depth": "advanced",
                "max_results": 30,
                "include_domains": ["miit.gov.cn", "ndrc.gov.cn", "csrc.gov.cn", "gov.cn", "caict.ac.cn", "stcsm.sh.gov.cn", "moe.gov.cn", "most.gov.cn"],
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        results = r.json().get("results") or []
        return [
            x
            for x in results
            if ((x.get("url") or "").lower().endswith(".pdf") or "doc" in (x.get("url") or "").lower())
            and _is_real_policy(x.get("title") or "")
        ]
    except Exception:
        return []


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
            if len(r.content) < 256:
                return False, len(r.content)
            dest.write_bytes(r.content)
            return True, len(r.content)
    except Exception:
        return False, 0


def parse_pdf(pdf_path: Path) -> str:
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages[:30])
    except Exception:
        return ""


def main():
    CORPUS.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    seen: set[str] = set()
    total_ok = 0

    for query in TARGETS["policy_topics"]:
        print(f"\n=== {query!r} ===")
        results = search_policy_pdfs(query)
        topic_count = 0
        for r in results:
            url = r.get("url", "")
            if url in seen:
                continue
            seen.add(url)
            sg = slug(url)
            pdf_path = CORPUS / f"{sg}.pdf"
            ok, size = download(url, pdf_path)
            if not ok:
                continue
            text = ""
            if url.lower().endswith(".pdf"):
                text = parse_pdf(pdf_path)
                (CORPUS / f"{sg}.md").write_text(text, encoding="utf-8")
            manifest.append(
                {
                    "id": sg,
                    "url": url,
                    "title": (r.get("title") or "")[:200],
                    "topic_query": query,
                    "size_bytes": size,
                    "text_chars": len(text),
                }
            )
            total_ok += 1
            topic_count += 1
            print(f"  [OK] {sg}  {size:>8} B  {(r.get('title') or '')[:60]}")
            if topic_count >= PER_TOPIC_TARGET:
                break
            time.sleep(0.4)

    (CORPUS / "manifest.json").write_text(
        json.dumps({"n_total": total_ok, "items": manifest}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nTOTAL: {total_ok} policy PDFs → {CORPUS / 'manifest.json'}")


if __name__ == "__main__":
    main()
