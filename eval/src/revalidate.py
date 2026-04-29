"""Re-validate already-extracted JSONs against current schema (no LLM calls)."""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from src.schemas import ExtractResearchOutput

ROOT = Path(__file__).resolve().parents[1]
EXTR = ROOT / "output" / "extractions"


def main():
    n_total = 0
    n_ok = 0
    total_tokens = 0
    total_wall = 0.0
    for p in sorted(EXTR.glob("*.json")):
        if p.name.startswith("_"):
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        n_total += 1
        e = d.get("extraction")
        errs: list[str] = []
        ok = False
        if e is not None:
            try:
                ExtractResearchOutput.model_validate(e)
                ok = True
            except ValidationError as ve:
                errs = [str(x) for x in ve.errors()]
        d["schema_ok"] = ok
        d["schema_errors"] = errs
        if ok:
            n_ok += 1
        total_tokens += (d.get("usage") or {}).get("total_tokens") or 0
        total_wall += d.get("wall_time_s") or 0.0
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        flag = "OK" if ok else "FAIL"
        print(f"{flag} {d['id']}: errs={len(errs)}")

    summary = {
        "n_total": n_total,
        "n_schema_ok": n_ok,
        "total_tokens": total_tokens,
        "total_wall_s": round(total_wall, 1),
    }
    (EXTR / "_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nSUMMARY: {summary}")


if __name__ == "__main__":
    main()
