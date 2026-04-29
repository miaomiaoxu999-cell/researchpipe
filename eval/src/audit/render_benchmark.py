"""Render the full 6-档 LLM benchmark comparison."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "llm_benchmark_full.md"

SUMMARIES = [
    ("V4-Pro no-think (L3)", ROOT / "output" / "extractions" / "_summary.json", "deepseek-v4-pro", False),
    ("V4-Flash think (L2)", ROOT / "output" / "ab" / "v4flash_think" / "_summary.json", "deepseek-v4-flash", True),
    ("V4-Flash no-think (L1)", ROOT / "output" / "ab" / "v4flash_nothink" / "_summary.json", "deepseek-v4-flash", False),
    ("V4-Pro think (L4)", ROOT / "output" / "ab" / "v4pro_think" / "_summary.json", "deepseek-v4-pro", True),
    ("GLM-4.7", ROOT / "output" / "ab" / "glm47" / "_summary.json", "glm-4.7", False),
    ("Kimi-K2.5", ROOT / "output" / "ab" / "kimi25" / "_summary.json", "kimi-k2.5", False),
]


def main():
    rows = []
    for label, path, model, think in SUMMARIES:
        if not path.exists():
            rows.append({"label": label, "model": model, "think": think, "error": "missing"})
            continue
        s = json.loads(path.read_text(encoding="utf-8"))
        rows.append({"label": label, "model": model, "think": think, **s})

    lines: list[str] = []
    lines.append("# ResearchPipe LLM 6 档完整 Benchmark\n")
    lines.append("**日期**：2026-04-29")
    lines.append("**任务**：从 9 篇研报（中文 7 + 英文 2）抽取 11 字段，schema = pydantic strict 校验\n")

    lines.append("## 总览矩阵\n")
    lines.append("| 档位 | 模型 + 思考 | 9 篇耗时 | 平均/篇 | total tokens | schema OK | avg conf | 1000 篇成本估算 |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        if r.get("error"):
            lines.append(f"| {r['label']} | {r['model']} | _missing_ | — | — | — | — | — |")
            continue
        wall = r.get("total_wall_s", 0)
        avg = wall / max(1, r.get("n_total", 9))
        # naive 成本估算 — 真实价格按账单为准
        cost_per_1000 = (r["total_tokens"] / 9) * 1000 / 1000 * (
            0.02 if "pro" in r["model"] else 0.002
        )
        lines.append(
            f"| {r['label']} | `{r['model']}` think={r['think']} | "
            f"{wall:.0f}s | {avg:.0f}s | {r['total_tokens']:,} | "
            f"{r['n_schema_ok']}/{r['n_total']} | {r.get('avg_confidence', 0)} | "
            f"~¥{cost_per_1000:.0f} |"
        )

    lines.append("\n## 关键发现\n")
    lines.append("### 1. 5/6 档 9/9 schema OK；Kimi 失败 6/9")
    lines.append("- V4-Flash / V4-Pro × think/no-think 四档全 9/9。")
    lines.append("- GLM-4.7 9/9（速度 85s 最快）。")
    lines.append("- **Kimi-K2.5 失败 6/9**：失败原因都是 `key_data_points[0].value` 输出为 number 而非 string（如 `value: 340` 或 `value: 1330`）。schema 要求 string 因为要保留 `'30%'` `'¥1.2亿'` 这种带单位字符串。Kimi 不遵守这个约束。")
    lines.append("- **结论**：Kimi 不适合做 extract/research 严格 schema 任务，可作为 search 兜底。\n")

    lines.append("### 2. 速度排序（快 → 慢）")
    lines.append("- GLM-4.7: 85s（最快，且 9/9）⭐")
    lines.append("- V4-Flash no-think: 89s")
    lines.append("- V4-Flash think: 136s")
    lines.append("- Kimi-K2.5: 195s（仅 3/9 OK）")
    lines.append("- V4-Pro no-think: 217s")
    lines.append("- V4-Pro think: 575s（最慢，思考最深）\n")

    lines.append("### 3. 成本档（粗估，实际百炼月账单为准）")
    lines.append("- V4-Flash 系列 + GLM + Kimi: ~¥30 / 1000 篇（**便宜档**）")
    lines.append("- V4-Pro 系列: ~¥250 / 1000 篇（**高级档**，~10× 价差）\n")

    lines.append("### 4. 推荐 ResearchPipe 模型分工\n")
    lines.append("| ResearchPipe 端点 | 推荐档 | 理由 |")
    lines.append("|---|---|---|")
    lines.append("| `extract/research` 默认 | **L2 V4-Flash think** | 9/9 准确 + 快 + 便宜，性价比最高 |")
    lines.append("| `extract/research` mini 档（如开放） | **L1 V4-Flash no-think** | 89s + ¥30/1000，agent 流式应用 |")
    lines.append("| `extract/research` pro 档 | **L3 V4-Pro no-think** | 217s + ¥250/1000，付费客户深度版 |")
    lines.append("| `research/sector` / `research/company` 默认 | **L2** | 同上 |")
    lines.append("| `research/*` pro 档 | **L3** | 同上 |")
    lines.append("| IC / 投决场景（M3+） | **L4 V4-Pro think** | 575s 思考最深 |")
    lines.append("| 实时短答（`/v1/search` `include_answer=basic`） | **L1** | 21s on 1K 字 per VIA benchmark |")
    lines.append("| **Fallback** 当 V4 不可用 | **GLM-4.7** | 85s + 9/9 schema OK，最快替补 |")
    lines.append("| **不用** | Kimi-K2.5 | 仅 3/9 schema OK，schema 遵从性差 |\n")

    lines.append("### 5. enable_thinking 隐式陷阱\n")
    lines.append("V4 系列默认 `enable_thinking=true`，必须显式 `false` 才走快通道（VIA cautions 已警告）。")
    lines.append("实测对比：")
    lines.append("- V4-Flash no-think: 89s")
    lines.append("- V4-Flash think:    136s（+50%）")
    lines.append("- V4-Pro no-think:   217s")
    lines.append("- V4-Pro think:      575s（+165%）")
    lines.append("\n建议 ResearchPipe backend 默认强制传 `enable_thinking=true` 走 L2（**think 模式但 Flash 体量，质量速度平衡**）。pro 档手动传 `enable_thinking=false` 走 L3。\n")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
