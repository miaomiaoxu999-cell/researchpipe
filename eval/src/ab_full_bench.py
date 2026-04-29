"""6 档 LLM 完整 benchmark — 跑同 9 篇研报。

档位：
  L1 deepseek-v4-flash  no-think
  L2 deepseek-v4-flash  think           (已跑，复用 output/ab/v4flash_think/)
  L3 deepseek-v4-pro    no-think        (已跑，复用 output/extractions/)
  L4 deepseek-v4-pro    think
  L5 glm-4.7
  L6 kimi-k2.5
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from pydantic import ValidationError

from src.llm import chat, extract_json
from src.prompts.extract_research import build_messages
from src.schemas import ExtractResearchOutput

ROOT = Path(__file__).resolve().parents[1]
PARSED = ROOT / "data" / "parsed"
MANIFEST = ROOT / "data" / "manifest.json"
MAX_INPUT_CHARS = 80000

BENCHMARKS: list[tuple[str, str, bool]] = [
    # tag, model, enable_thinking
    ("v4flash_nothink", "deepseek-v4-flash", False),
    ("v4pro_think", "deepseek-v4-pro", True),
    ("glm47", "glm-4.7", False),
    ("kimi25", "kimi-k2.5", False),
]


def run_one(rec: dict, model: str, think: bool) -> dict:
    rid = rec["id"]
    src = PARSED / f"{rid}.md"
    full_text = src.read_text(encoding="utf-8")
    if len(full_text) > MAX_INPUT_CHARS:
        full_text = full_text[:MAX_INPUT_CHARS]

    sys_msg, user_msg = build_messages(
        full_text=full_text,
        source_url=rec.get("url", ""),
        hint_title=rec.get("title_hint", ""),
        sector_hint=rec.get("sector", ""),
    )
    started = time.time()
    raw, usage = chat(sys_msg, user_msg, model=model, enable_thinking=think, max_tokens=8000)
    elapsed = time.time() - started

    parsed_json = None
    schema_errors: list[str] = []
    schema_ok = False
    try:
        parsed_json = extract_json(raw)
    except json.JSONDecodeError as e:
        schema_errors.append(f"json_decode: {e}")
    if parsed_json is not None:
        try:
            ExtractResearchOutput.model_validate(parsed_json)
            schema_ok = True
        except ValidationError as ve:
            schema_errors.extend(str(x) for x in ve.errors())

    return {
        "id": rid,
        "sector": rec["sector"],
        "model": model,
        "enable_thinking": think,
        "wall_time_s": round(elapsed, 1),
        "usage": usage,
        "schema_ok": schema_ok,
        "schema_errors": schema_errors,
        "extraction": parsed_json,
        "raw_response": raw if not schema_ok else None,
    }


def run_bench(tag: str, model: str, think: bool):
    out_dir = ROOT / "output" / "ab" / tag
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = []
    for rec in manifest["reports"]:
        rid = rec["id"]
        out = out_dir / f"{rid}.json"
        if out.exists() and out.stat().st_size > 100:
            print(f"  SKIP {rid}")
            rows.append(json.loads(out.read_text(encoding="utf-8")))
            continue
        attempts = 0
        d = None
        while attempts < 3:
            attempts += 1
            try:
                d = run_one(rec, model, think)
                break
            except Exception as e:
                print(f"  ERR {rid} attempt {attempts}: {e}")
                time.sleep(3)
        if d is None:
            print(f"  SKIP {rid} after 3 attempts")
            continue
        out.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        flag = "OK" if d["schema_ok"] else "FAIL"
        print(f"  {flag} {rid}: {d['wall_time_s']}s, tokens={d['usage'].get('total_tokens')}")
        rows.append(d)

    summary = {
        "tag": tag,
        "model": model,
        "enable_thinking": think,
        "n_total": len(rows),
        "n_schema_ok": sum(1 for r in rows if r["schema_ok"]),
        "total_tokens": sum((r["usage"].get("total_tokens") or 0) for r in rows),
        "total_wall_s": round(sum(r["wall_time_s"] for r in rows), 1),
    }
    confs = [(r.get("extraction") or {}).get("confidence_score") for r in rows]
    confs = [c for c in confs if isinstance(c, (int, float))]
    if confs:
        summary["avg_confidence"] = round(sum(confs) / len(confs), 3)
    (out_dir / "_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  SUMMARY {tag}: {summary}")
    return summary


def main():
    summaries = []
    for tag, model, think in BENCHMARKS:
        out_dir = ROOT / "output" / "ab" / tag
        existing = out_dir / "_summary.json"
        if existing.exists():
            summaries.append(json.loads(existing.read_text(encoding="utf-8")))
            print(f"=== {tag} (cached) ===")
            continue
        print(f"\n=== {tag} :: {model} think={think} ===")
        try:
            s = run_bench(tag, model, think)
            summaries.append(s)
        except Exception as e:
            print(f"  FATAL {tag}: {e}")
            summaries.append({"tag": tag, "error": str(e)})
    (ROOT / "output" / "ab" / "_all_summaries.json").write_text(
        json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
