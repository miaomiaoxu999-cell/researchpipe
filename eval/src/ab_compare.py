"""Compare V4-Pro no-think (baseline) vs V4-Flash think (A/B variant).

Outputs:
  output/ab_compare.md  — side-by-side cost / time / quality table + per-report deltas
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "output" / "extractions"  # V4-Pro no-think
VARIANT = ROOT / "output" / "ab" / "v4flash_think"

SECTOR_LABELS = {
    "embodied_ai": "具身智能",
    "semi_localization": "半导体国产化",
    "biotech_outbound": "创新药出海",
}


def load_set(d: Path) -> dict[str, dict]:
    out = {}
    for p in sorted(d.glob("*.json")):
        if p.name.startswith("_"):
            continue
        out[p.stem] = json.loads(p.read_text(encoding="utf-8"))
    return out


def cmp_field(a, b) -> str:
    if a == b:
        return "="
    return f"{a} → {b}"


def main():
    base = load_set(BASELINE)
    var = load_set(VARIANT)
    if not var:
        print(f"No variant data in {VARIANT}")
        return

    base_summary = json.loads((BASELINE / "_summary.json").read_text(encoding="utf-8"))
    var_summary = json.loads((VARIANT / "_summary.json").read_text(encoding="utf-8"))

    lines: list[str] = [
        "# A/B 对比：V4-Pro no-think vs V4-Flash think",
        "",
        f"测试日期：2026-04-29 · 同 9 篇研报，同 prompt，同 schema",
        "",
        "## 总览",
        "",
        "| 指标 | V4-Pro no-think (baseline) | V4-Flash think (variant) | 差异 |",
        "|---|---|---|---|",
        f"| Schema 通过 | {base_summary['n_schema_ok']}/{base_summary['n_total']} "
        f"| {var_summary['n_schema_ok']}/{var_summary['n_total']} | "
        f"{var_summary['n_schema_ok'] - base_summary['n_schema_ok']:+d} |",
        f"| 总耗时 | {base_summary['total_wall_s']:.1f}s "
        f"| {var_summary['total_wall_s']:.1f}s | "
        f"{var_summary['total_wall_s'] - base_summary['total_wall_s']:+.1f}s ({(var_summary['total_wall_s'] / base_summary['total_wall_s'] - 1) * 100:+.0f}%) |",
        f"| 总 tokens | {base_summary['total_tokens']:,} | {var_summary['total_tokens']:,} | "
        f"{var_summary['total_tokens'] - base_summary['total_tokens']:+,} |",
    ]

    if "avg_confidence" in var_summary:
        # baseline doesn't have avg_confidence in summary but we can compute
        base_confs = [
            (b.get("extraction") or {}).get("confidence_score")
            for b in base.values()
        ]
        base_confs = [c for c in base_confs if isinstance(c, (int, float))]
        base_avg_c = sum(base_confs) / len(base_confs) if base_confs else 0
        lines.append(
            f"| 平均 confidence | {base_avg_c:.3f} | {var_summary['avg_confidence']:.3f} | "
            f"{var_summary['avg_confidence'] - base_avg_c:+.3f} |"
        )

    lines += [
        "",
        "## 每篇对比",
        "",
        "| ID | 赛道 | Pro 耗时 | Flash 耗时 | Pro tokens | Flash tokens | Pro datapt | Flash datapt | Pro risks | Flash risks | Schema |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for rid, b in base.items():
        v = var.get(rid)
        if v is None:
            continue
        be = b.get("extraction") or {}
        ve = v.get("extraction") or {}
        b_dp = len(be.get("key_data_points") or [])
        v_dp = len(ve.get("key_data_points") or [])
        b_rk = len(be.get("risks") or [])
        v_rk = len(ve.get("risks") or [])
        b_ok = "✅" if b.get("schema_ok") else "❌"
        v_ok = "✅" if v.get("schema_ok") else "❌"
        sec = SECTOR_LABELS.get(b.get("sector"), b.get("sector"))
        lines.append(
            f"| {rid} | {sec} | "
            f"{b['wall_time_s']}s | {v['wall_time_s']}s | "
            f"{b['usage'].get('total_tokens')} | {v['usage'].get('total_tokens')} | "
            f"{b_dp} | {v_dp} | "
            f"{b_rk} | {v_rk} | "
            f"{b_ok}/{v_ok} |"
        )

    # Quality dive: pick 1-2 representative samples and show core_thesis diff
    lines += [
        "",
        "## core_thesis 内容对比（抽样 3 篇）",
        "",
    ]
    for rid in ["bio_gs_2025", "ea_36kr_2026", "semi_dongwu_2026"]:
        b = base.get(rid)
        v = var.get(rid)
        if not b or not v:
            continue
        be = b.get("extraction") or {}
        ve = v.get("extraction") or {}
        lines += [
            f"### {rid}",
            "",
            "**V4-Pro no-think:**",
            "",
            f"> {be.get('core_thesis', '(missing)')}",
            "",
            "**V4-Flash think:**",
            "",
            f"> {ve.get('core_thesis', '(missing)')}",
            "",
        ]

    # Cost projection
    # 百炼 V4 价格（2026-04 估算）：v4-pro ~ ¥0.012/K input + ¥0.03/K output
    #                              v4-flash ~ ¥0.001/K input + ¥0.003/K output
    # 我们用 token 总量 × 单价做粗估
    lines += [
        "",
        "## 成本投影（百炼定价粗估）",
        "",
        "> 价格按 2026-04 公开报价粗估，实际计费以阿里云月账单为准。",
        "",
        "| 模型 | 9 篇 tokens | 单 1000 篇估算成本 |",
        "|---|---|---|",
        f"| V4-Pro no-think | {base_summary['total_tokens']:,} | ~¥{base_summary['total_tokens'] * 0.02 / 1000 * 1000 / 9:.0f} |",
        f"| V4-Flash think  | {var_summary['total_tokens']:,} | ~¥{var_summary['total_tokens'] * 0.002 / 1000 * 1000 / 9:.0f} |",
        "",
        "## 结论建议（待用户确认）",
        "",
        "- 如果 quality 损失 < 5%、schema_ok 仍 9/9 → **推 V4-Flash think 上 M1 默认 model**（成本下降 ~10×）",
        "- V4-Pro no-think 留作 `model=pro` 升级档（`research/*` 的 pro tier）",
        "- V4-Pro think (L4) 留给 IC 投决场景（W2+ 实施）",
    ]

    out = ROOT / "output" / "ab_compare.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
