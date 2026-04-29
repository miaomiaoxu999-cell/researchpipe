"""C 层验证：30 家券商 + 公开站点的 robots.txt + 主页可访问性 + 一个公开列表页试爬。

每个目标记录：
  - robots.txt 状态（200 / 404 / disallow 关键路径？）
  - 主页能否 200 + 是否含 JS-rendered（看 <script> 占比）
  - 公开列表页 sample 能否拿到（找 research/report/yanbao 链接）
  - 难度分级：✅easy / ⚠️moderate / ❌hard
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
TARGETS = json.loads((ROOT / "data" / "c_layer_targets.json").read_text(encoding="utf-8"))
OUT = ROOT / "output" / "audit" / "c"
OUT.mkdir(parents=True, exist_ok=True)

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
HEADERS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"}
TIMEOUT = 20.0


def fetch(url: str) -> dict:
    t0 = time.time()
    try:
        with httpx.Client(timeout=TIMEOUT, headers=HEADERS, follow_redirects=True, verify=False) as cli:
            r = cli.get(url)
            elapsed = round(time.time() - t0, 2)
            return {
                "url": url,
                "status_code": r.status_code,
                "final_url": str(r.url),
                "elapsed_s": elapsed,
                "content_length": len(r.content),
                "content_type": r.headers.get("content-type", ""),
                "encoding": r.encoding,
                "text_preview": r.text[:1500] if r.status_code == 200 else r.text[:300],
            }
    except Exception as e:
        return {"url": url, "error": type(e).__name__ + ": " + str(e)[:200], "elapsed_s": round(time.time() - t0, 2)}


def js_heaviness(text: str) -> float:
    """Estimate JS-rendered ratio. >0.4 = SPA, hard to scrape without browser."""
    if not text:
        return 0.0
    soup = BeautifulSoup(text, "lxml")
    visible = soup.get_text(strip=True)
    scripts = "".join(s.get_text() for s in soup.find_all("script"))
    total = max(1, len(visible) + len(scripts))
    return round(len(scripts) / total, 2)


def find_research_links(html: str, base_url: str) -> list[str]:
    """Find anchor links plausibly leading to a research/report/yanbao listing."""
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    keywords = ["research", "yanbao", "report", "yanjiu", "yj", "深度", "策略", "研报", "报告"]
    base = urlparse(base_url)
    seen, hits = set(), []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(strip=True)[:30]
        full = href if href.startswith("http") else (f"{base.scheme}://{base.netloc}{href}" if href.startswith("/") else None)
        if not full:
            continue
        if any(kw in (href + " " + text).lower() for kw in keywords) or any(kw in text for kw in keywords):
            if full not in seen:
                seen.add(full)
                hits.append({"href": full, "text": text})
                if len(hits) >= 8:
                    break
    return hits


def assess_target(t: dict) -> dict:
    name = t["name"]
    domain = t["domain"]
    base = f"https://{domain}"
    out: dict = {"name": name, "domain": domain, "tier": t.get("tier") or t.get("category", "")}

    # 1) robots.txt
    robots = fetch(f"{base}/robots.txt")
    out["robots"] = {
        "status_code": robots.get("status_code"),
        "size": robots.get("content_length"),
        "preview": robots.get("text_preview", "")[:600] if robots.get("status_code") == 200 else robots.get("error", ""),
    }

    # 2) 主页
    home = fetch(base)
    out["home"] = {
        "status_code": home.get("status_code"),
        "final_url": home.get("final_url"),
        "content_length": home.get("content_length"),
        "content_type": home.get("content_type"),
        "elapsed_s": home.get("elapsed_s"),
        "error": home.get("error"),
    }

    # 3) JS heaviness + research link discovery
    if home.get("text_preview") and home.get("status_code") == 200:
        # need full HTML for proper analysis — re-fetch with bigger preview
        # (text_preview is truncated to 1500; use it as best-effort sample)
        out["js_heavy_ratio"] = js_heaviness(home["text_preview"])
        out["candidate_links"] = find_research_links(home["text_preview"], home.get("final_url") or base)
    else:
        out["js_heavy_ratio"] = None
        out["candidate_links"] = []

    # 4) 难度分级
    if out["home"]["status_code"] != 200:
        difficulty = "❌hard"
        reason = f"home not 200 ({out['home']['status_code']})"
    elif out["js_heavy_ratio"] and out["js_heavy_ratio"] > 0.5:
        difficulty = "⚠️moderate"
        reason = "SPA / heavy JS — needs Playwright"
    elif not out["candidate_links"]:
        difficulty = "⚠️moderate"
        reason = "home OK but no research-linked anchors found"
    else:
        difficulty = "✅easy"
        reason = "home OK, plain HTML, research links found"
    out["difficulty"] = difficulty
    out["assessment"] = reason

    return out


def main():
    all_targets = (
        [{"_group": "tier1_brokers", **t} for t in TARGETS["tier1_brokers_p0"]]
        + [{"_group": "tier2_brokers", **t} for t in TARGETS["tier2_brokers_p2"]]
        + [{"_group": "tier3_brokers", **t} for t in TARGETS["tier3_brokers_p3"]]
        + [{"_group": "public_orgs", **t} for t in TARGETS["public_orgs"]]
    )
    results = []
    for i, t in enumerate(all_targets, 1):
        print(f"[{i}/{len(all_targets)}] {t['name']} ({t['domain']}) ...")
        attempts = 0
        last = None
        while attempts < 3:
            attempts += 1
            try:
                last = assess_target(t)
                break
            except Exception as e:
                last = {"name": t["name"], "domain": t["domain"], "error": f"attempt {attempts}: {e}"}
                time.sleep(2)
        last["_group"] = t["_group"]
        out_p = OUT / f"{t['domain'].replace('.', '_')}.json"
        out_p.write_text(json.dumps(last, ensure_ascii=False, indent=2), encoding="utf-8")
        results.append(last)
        diff = last.get("difficulty", "?")
        print(f"  → {diff} :: {last.get('assessment', last.get('error', ''))[:80]}")
        time.sleep(0.4)  # gentle

    summary = {
        "n_total": len(results),
        "by_difficulty": {
            "✅easy": sum(1 for r in results if r.get("difficulty") == "✅easy"),
            "⚠️moderate": sum(1 for r in results if r.get("difficulty") == "⚠️moderate"),
            "❌hard": sum(1 for r in results if r.get("difficulty") == "❌hard"),
        },
        "by_group": {},
    }
    for r in results:
        g = r.get("_group", "?")
        summary["by_group"].setdefault(g, {"total": 0, "easy": 0, "mod": 0, "hard": 0})
        summary["by_group"][g]["total"] += 1
        d = r.get("difficulty", "")
        if d == "✅easy":
            summary["by_group"][g]["easy"] += 1
        elif d == "⚠️moderate":
            summary["by_group"][g]["mod"] += 1
        elif d == "❌hard":
            summary["by_group"][g]["hard"] += 1
    (OUT / "_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSUMMARY: {summary}")


if __name__ == "__main__":
    main()
