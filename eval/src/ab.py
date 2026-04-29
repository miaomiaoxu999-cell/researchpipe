"""A/B variant runner: re-run extraction over the same 9 reports with a different
model + thinking flag, into a tagged output dir.

Usage:
  uv run python -m src.ab --tag v4flash_think --model deepseek-v4-flash --think true
  uv run python -m src.ab --tag v4pro_think    --model deepseek-v4-pro    --think true
"""
from __future__ import annotations

import argparse
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


def run_one(rec: dict, model: str, think: bool) -> dict:
    rid = rec["id"]
    src = PARSED / f"{rid}.md"
    full_text = src.read_text(encoding="utf-8")
    truncated = False
    if len(full_text) > MAX_INPUT_CHARS:
        full_text = full_text[:MAX_INPUT_CHARS]
        truncated = True

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
        "url": rec.get("url"),
        "model": model,
        "enable_thinking": think,
        "input_chars": len(full_text),
        "input_truncated": truncated,
        "wall_time_s": round(elapsed, 1),
        "usage": usage,
        "schema_ok": schema_ok,
        "schema_errors": schema_errors,
        "raw_response": raw if not schema_ok else None,
        "extraction": parsed_json,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tag", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--think", choices=["true", "false"], required=True)
    args = p.parse_args()
    think = args.think == "true"

    out_dir = ROOT / "output" / "ab" / args.tag
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = []
    for rec in manifest["reports"]:
        rid = rec["id"]
        out = out_dir / f"{rid}.json"
        if out.exists() and out.stat().st_size > 100:
            print(f"SKIP {rid}")
            rows.append(json.loads(out.read_text(encoding="utf-8")))
            continue
        print(f"\n=== {args.tag} :: {rid} ===")
        try:
            d = run_one(rec, args.model, think)
        except Exception as e:
            print(f"ERR {rid}: {e}")
            continue
        out.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        flag = "OK" if d["schema_ok"] else "SCHEMA-FAIL"
        print(
            f"{flag} {rid}: {d['wall_time_s']}s, in={d['input_chars']}, "
            f"tokens={d['usage'].get('total_tokens')}"
        )
        rows.append(d)

    summary = {
        "tag": args.tag,
        "model": args.model,
        "enable_thinking": think,
        "n_total": len(rows),
        "n_schema_ok": sum(1 for r in rows if r["schema_ok"]),
        "total_tokens": sum((r["usage"].get("total_tokens") or 0) for r in rows),
        "total_wall_s": round(sum(r["wall_time_s"] for r in rows), 1),
        "avg_confidence": round(
            sum(
                (r.get("extraction") or {}).get("confidence_score", 0)
                for r in rows
                if (r.get("extraction") or {}).get("confidence_score") is not None
            ) / max(1, sum(1 for r in rows if r.get("extraction"))),
            3,
        ),
    }
    (out_dir / "_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nSUMMARY: {summary}")


if __name__ == "__main__":
    main()
