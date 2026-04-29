"""Run extract/research extraction over all parsed reports."""
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
EXTRACTIONS = ROOT / "output" / "extractions"
EXTRACTIONS.mkdir(parents=True, exist_ok=True)
MAX_INPUT_CHARS = 80000  # ~ keep under 60K tokens for Chinese


def run_one(rec: dict) -> dict:
    rid = rec["id"]
    src = PARSED / f"{rid}.md"
    if not src.exists():
        raise FileNotFoundError(f"Parsed source missing for {rid}")

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
    raw, usage = chat(sys_msg, user_msg, max_tokens=8000)
    elapsed = time.time() - started

    parsed_json = None
    schema_ok = False
    schema_errors: list[str] = []
    try:
        parsed_json = extract_json(raw)
    except json.JSONDecodeError as e:
        schema_errors.append(f"json_decode: {e}")

    if parsed_json is not None:
        try:
            ExtractResearchOutput.model_validate(parsed_json)
            schema_ok = True
        except ValidationError as e:
            schema_errors.extend(str(err) for err in e.errors())

    record = {
        "id": rid,
        "sector": rec["sector"],
        "url": rec.get("url"),
        "input_chars": len(full_text),
        "input_truncated": truncated,
        "wall_time_s": round(elapsed, 1),
        "usage": usage,
        "schema_ok": schema_ok,
        "schema_errors": schema_errors,
        "raw_response": raw if not schema_ok else None,
        "extraction": parsed_json,
    }
    return record


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    results = []
    for rec in manifest["reports"]:
        rid = rec["id"]
        out = EXTRACTIONS / f"{rid}.json"
        if out.exists() and out.stat().st_size > 100:
            print(f"SKIP {rid} (already extracted)")
            results.append(json.loads(out.read_text(encoding="utf-8")))
            continue
        print(f"\n=== Extracting {rid} ===")
        try:
            record = run_one(rec)
        except Exception as e:
            print(f"ERR {rid}: {e}")
            continue
        out.write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        flag = "OK" if record["schema_ok"] else "SCHEMA-FAIL"
        print(
            f"{flag} {rid}: {record['wall_time_s']}s, "
            f"in={record['input_chars']}, tokens={record['usage'].get('total_tokens')}, "
            f"errs={len(record['schema_errors'])}"
        )
        results.append(record)

    # Aggregate
    summary = {
        "n_total": len(results),
        "n_schema_ok": sum(1 for r in results if r["schema_ok"]),
        "total_tokens": sum((r["usage"].get("total_tokens") or 0) for r in results),
        "total_wall_s": sum(r["wall_time_s"] for r in results),
    }
    (EXTRACTIONS / "_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nSUMMARY: {summary}")


if __name__ == "__main__":
    main()
