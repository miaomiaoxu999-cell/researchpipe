"""Score UC20 results and produce a markdown report.

Heuristic scoring (no LLM-judge to keep it cheap):
  - completed: did the run finish without error?
  - has_answer: ≥500 chars of content
  - has_citation: contains [1] or [2] markers
  - has_data: contains digits + Chinese text or %
  - tool_efficiency: ratio (n_new_sources) / (n_tool_calls)
  - duration: pass if <90s
  - no_loop: pass if iterations < MAX (8)

Final grade: A (all pass) / B (1-2 fail) / C (3+ fail) / F (no answer)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def grade_one(rec: dict) -> dict:
    out: dict = {"id": rec["id"], "category": rec["category"]}
    text = rec.get("answer_text", "") or ""
    chars = len(text)
    completed = bool(rec.get("completed")) and not rec.get("error")
    # Lower threshold for categories where a brief response is correct behavior.
    min_chars = 200 if rec["category"] in ("ambiguous", "off_topic") else 500
    has_answer = chars >= min_chars
    has_citation = bool(re.search(r"\[\d+\]", text))
    has_digit = bool(re.search(r"\d+(\.\d+)?\s*(%|亿|万|GWh|Wh/kg|MW|元|美元)", text))
    tool_count = rec.get("n_tool_calls", 0) or 0
    new_sources = sum((tr.get("n_new_sources") or 0) for tr in rec.get("tool_results", []))
    tool_eff = round(new_sources / max(tool_count, 1), 2)
    elapsed = rec.get("elapsed_s", 0) or 0
    iterations = rec.get("iterations", 0) or 0

    checks = {
        "completed": completed,
        "has_answer": has_answer,
        "has_citation": has_citation if rec["category"] not in ("ambiguous", "off_topic") else True,
        "has_data": has_digit if rec["category"] not in ("ambiguous", "off_topic", "english") else True,
        "fast_enough": elapsed < 90,
        "no_loop": iterations < 8,
        "tool_efficient": tool_eff >= 0.5 if tool_count > 0 else True,
    }
    n_pass = sum(1 for v in checks.values() if v)
    n_total = len(checks)
    n_fail = n_total - n_pass

    if not has_answer:
        grade = "F"
    elif n_fail == 0:
        grade = "A"
    elif n_fail <= 2:
        grade = "B"
    else:
        grade = "C"

    out.update({
        "grade": grade,
        "completed": completed,
        "chars": chars,
        "n_tool_calls": tool_count,
        "n_new_sources": new_sources,
        "tool_eff": tool_eff,
        "iterations": iterations,
        "elapsed_s": elapsed,
        "checks": checks,
        "error": rec.get("error"),
        "query": rec.get("query"),
    })
    return out


def render_md(scores: list[dict]) -> str:
    n = len(scores)
    grades = {"A": 0, "B": 0, "C": 0, "F": 0}
    for s in scores:
        grades[s["grade"]] += 1

    lines = [
        f"# UC20 Quality Report — {n} cases",
        "",
        f"**Grades**: A={grades['A']}  B={grades['B']}  C={grades['C']}  F={grades['F']}",
        "",
        "| ID | Cat | Grade | Chars | Tools | Sources | Eff | Iters | Time | Issues |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in scores:
        issues = [k for k, v in s["checks"].items() if not v]
        issues_s = ", ".join(issues) if issues else "—"
        if s["error"]:
            issues_s = f"ERR: {s['error']}"
        lines.append(
            f"| {s['id']} | {s['category']} | **{s['grade']}** | {s['chars']} | "
            f"{s['n_tool_calls']} | {s['n_new_sources']} | {s['tool_eff']} | "
            f"{s['iterations']} | {s['elapsed_s']}s | {issues_s} |"
        )

    lines += ["", "## Per-case detail (preview of answer)", ""]
    return "\n".join(lines)


def main() -> int:
    in_path = Path(sys.argv[1] if len(sys.argv) > 1 else "results_uc20.json")
    out_path = Path(sys.argv[2] if len(sys.argv) > 2 else "report.md")
    data = json.loads(in_path.read_text(encoding="utf-8"))
    scores = [grade_one(r) for r in data]

    md = render_md(scores)

    # Append per-case answer preview (first 600 chars)
    detail_lines = []
    for r, s in zip(data, scores):
        detail_lines.append(f"\n### {s['id']} ({s['category']}) — Grade {s['grade']}")
        detail_lines.append(f"- **Q**: {r['query']}")
        detail_lines.append(f"- **expects**: {r.get('expects')}")
        if r.get("error"):
            detail_lines.append(f"- **error**: `{r['error']}`")
        ans = r.get("answer_text", "")
        if ans:
            preview = ans[:800].replace("\n", " ")
            detail_lines.append(f"- **answer head** (800ch): {preview}...")
        else:
            detail_lines.append("- **answer**: (empty)")
        detail_lines.append("")

    md += "\n".join(detail_lines)

    out_path.write_text(md, encoding="utf-8")
    print(f"wrote {out_path}")
    print(f"A={sum(1 for s in scores if s['grade']=='A')}  "
          f"B={sum(1 for s in scores if s['grade']=='B')}  "
          f"C={sum(1 for s in scores if s['grade']=='C')}  "
          f"F={sum(1 for s in scores if s['grade']=='F')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
