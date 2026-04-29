"""Tavily Extract vs pdfplumber A/B — 同 9 篇 PDF / HTML 对比抽取质量。

baseline = data/parsed/<id>.md (pdfplumber + bs4)
variant  = Tavily Extract → raw_content
然后用同一个 prompt + V4-Flash think 各跑一次抽取，对比：
  - 字符数
  - schema_ok
  - key_data_points 数量
  - confidence_score
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from pydantic import ValidationError

from src.llm import chat, extract_json
from src.prompts.extract_research import build_messages
from src.schemas import ExtractResearchOutput

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

PARSED = ROOT / "data" / "parsed"
MANIFEST = ROOT / "data" / "manifest.json"
OUT = ROOT / "output" / "audit" / "extract_ab"
OUT.mkdir(parents=True, exist_ok=True)

import os

TAVILY_KEY = os.environ["TAVILY_API_KEY"]
MODEL = "deepseek-v4-flash"


def fetch_tavily_extract(url: str) -> str:
    r = httpx.post(
        "https://api.tavily.com/extract",
        headers={"Authorization": f"Bearer {TAVILY_KEY}", "Content-Type": "application/json"},
        json={"urls": [url], "extract_depth": "advanced"},
        timeout=60.0,
    )
    r.raise_for_status()
    items = r.json().get("results") or []
    return items[0].get("raw_content") or "" if items else ""


def run_extract(text: str, rec: dict) -> dict:
    sys_msg, user_msg = build_messages(
        full_text=text[:80000],
        source_url=rec.get("url", ""),
        hint_title=rec.get("title_hint", ""),
        sector_hint=rec.get("sector", ""),
    )
    started = time.time()
    raw, usage = chat(sys_msg, user_msg, model=MODEL, enable_thinking=True, max_tokens=8000)
    elapsed = time.time() - started
    parsed = None
    schema_ok = False
    try:
        parsed = extract_json(raw)
        ExtractResearchOutput.model_validate(parsed)
        schema_ok = True
    except (json.JSONDecodeError, ValidationError):
        pass
    return {
        "input_chars": len(text[:80000]),
        "wall_time_s": round(elapsed, 1),
        "tokens": usage.get("total_tokens"),
        "schema_ok": schema_ok,
        "extraction": parsed,
        "n_data_points": len((parsed or {}).get("key_data_points") or []) if parsed else 0,
        "n_risks": len((parsed or {}).get("risks") or []) if parsed else 0,
        "confidence": (parsed or {}).get("confidence_score") if parsed else None,
    }


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = []
    for rec in manifest["reports"]:
        rid = rec["id"]
        cache_p = OUT / f"{rid}.json"
        if cache_p.exists():
            rows.append(json.loads(cache_p.read_text(encoding="utf-8")))
            continue

        # baseline = pdfplumber/parsed
        baseline_text = (PARSED / f"{rid}.md").read_text(encoding="utf-8")
        # variant = Tavily Extract
        try:
            variant_text = fetch_tavily_extract(rec["url"])
        except Exception as e:
            variant_text = ""
            tavily_err = str(e)[:200]
        else:
            tavily_err = None

        print(f"=== {rid} (baseline {len(baseline_text)} chars / variant {len(variant_text)} chars) ===")
        result = {
            "id": rid,
            "sector": rec["sector"],
            "url": rec["url"],
            "tavily_error": tavily_err,
        }

        for tag, text in [("baseline", baseline_text), ("variant", variant_text)]:
            if not text:
                result[tag] = {"error": "empty input"}
                continue
            attempts = 0
            d = None
            while attempts < 3:
                attempts += 1
                try:
                    d = run_extract(text, rec)
                    break
                except Exception as e:
                    print(f"  {tag} attempt {attempts} failed: {e}")
                    time.sleep(3)
            result[tag] = d or {"error": "all 3 attempts failed"}

        cache_p.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        rows.append(result)

        b = result.get("baseline", {})
        v = result.get("variant", {})
        print(
            f"  baseline: schema_ok={b.get('schema_ok')} dp={b.get('n_data_points')} t={b.get('wall_time_s')}s | "
            f"variant: schema_ok={v.get('schema_ok')} dp={v.get('n_data_points')} t={v.get('wall_time_s')}s"
        )

    # Aggregate
    total = len(rows)
    base_ok = sum(1 for r in rows if (r.get("baseline") or {}).get("schema_ok"))
    var_ok = sum(1 for r in rows if (r.get("variant") or {}).get("schema_ok"))
    base_dp = sum((r.get("baseline") or {}).get("n_data_points", 0) for r in rows)
    var_dp = sum((r.get("variant") or {}).get("n_data_points", 0) for r in rows)
    base_chars = sum((r.get("baseline") or {}).get("input_chars", 0) for r in rows)
    var_chars = sum((r.get("variant") or {}).get("input_chars", 0) for r in rows)
    summary = {
        "n_total": total,
        "baseline (pdfplumber)": {"schema_ok": base_ok, "total_data_points": base_dp, "total_input_chars": base_chars},
        "variant (tavily-extract)": {"schema_ok": var_ok, "total_data_points": var_dp, "total_input_chars": var_chars},
    }
    (OUT / "_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSUMMARY: {summary}")


if __name__ == "__main__":
    main()
