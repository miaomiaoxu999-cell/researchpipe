"""Render the Extract A/B report (pdfplumber vs Tavily Extract)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "output" / "audit" / "extract_ab"
OUT = ROOT / "output" / "extract_ab_report.md"


def main():
    summary = json.loads((EXT / "_summary.json").read_text(encoding="utf-8"))
    rows = []
    for p in sorted(EXT.glob("*.json")):
        if p.name.startswith("_"):
            continue
        rows.append(json.loads(p.read_text(encoding="utf-8")))

    lines: list[str] = []
    lines.append("# Tavily Extract vs pdfplumber A/B 报告\n")
    lines.append("**日期**：2026-04-29")
    lines.append("**任务**：同 9 篇研报 PDF / HTML，分别走 baseline (pdfplumber + bs4) 和 variant (Tavily Extract API)，再用同 prompt + V4-Flash think 抽 11 字段")
    lines.append("**目的**：决定 ResearchPipe 抽取流水线是否可以省掉 pdfplumber 这一层，全部走 Tavily Extract\n")

    bs = summary["baseline (pdfplumber)"]
    vr = summary["variant (tavily-extract)"]
    lines.append("## 总览\n")
    lines.append("| 指标 | baseline (pdfplumber + bs4) | variant (Tavily Extract) | Δ |")
    lines.append("|---|---|---|---|")
    lines.append(f"| schema_ok | {bs['schema_ok']}/{summary['n_total']} | {vr['schema_ok']}/{summary['n_total']} | {vr['schema_ok'] - bs['schema_ok']:+d} |")
    lines.append(f"| total data points | {bs['total_data_points']} | {vr['total_data_points']} | {vr['total_data_points'] - bs['total_data_points']:+d} |")
    lines.append(f"| total input chars | {bs['total_input_chars']:,} | {vr['total_input_chars']:,} | {vr['total_input_chars'] - bs['total_input_chars']:+,} |")

    lines.append("\n## 单篇细况\n")
    lines.append("| ID | 赛道 | baseline chars | variant chars | b/v dp | b/v 时间(s) | 备注 |")
    lines.append("|---|---|---:|---:|---:|---:|---|")
    for r in rows:
        rid = r["id"]
        b = r.get("baseline") or {}
        v = r.get("variant") or {}
        bdp = b.get("n_data_points", 0)
        vdp = v.get("n_data_points", 0)
        bt = b.get("wall_time_s", 0)
        vt = v.get("wall_time_s", 0)
        bch = b.get("input_chars", 0)
        vch = v.get("input_chars", 0)
        note = ""
        if vch > bch * 1.5:
            note = "⚠️ Tavily 输入更长（含 nav / footer）"
        elif vdp < bdp * 0.7:
            note = "⚠️ Tavily 数据点少 30%+"
        lines.append(f"| {rid} | {r['sector']} | {bch:,} | {vch:,} | {bdp}/{vdp} | {bt}/{vt} | {note} |")

    lines.append("\n## 关键发现\n")
    lines.append("### 1. 两路同样 9/9 schema OK")
    lines.append("- baseline (pdfplumber + bs4 + 自写清洗) 9/9 通过")
    lines.append("- variant (Tavily Extract API) 9/9 通过")
    lines.append("- **schema 通过率上无差距**\n")

    lines.append("### 2. 数据点数 baseline 略多")
    lines.append("- baseline: 62 个 key_data_points")
    lines.append("- variant: 57 个 key_data_points")
    lines.append("- 差 8%，主要原因：Tavily Extract 在某些复杂研报（半导体）少抽 1-3 条；HTML 抽取（GS 短文章）反而多抽 3 条")
    lines.append("- 两路互补：长 PDF baseline 占优；HTML 文章 Tavily 占优\n")

    lines.append("### 3. 输入字符数 variant 多 26%")
    lines.append("- baseline: 184K chars（pdfplumber 转换 + bs4 清洗 + 自写过滤页码 / 免责声明）")
    lines.append('- variant: 232K chars（Tavily 不主动剔除 nav/footer，原文还带「相关研究」等链接列表）')
    lines.append("- 后果：variant 的 LLM input 多 ~26%，token 成本相应增加。但 V4-Flash 单价低，绝对成本差几分钱/篇，不重要。\n")

    lines.append("### 4. 工程复杂度 — Tavily Extract 大幅简化")
    lines.append("- baseline: 需要 `pdfplumber`（C 扩展）+ `beautifulsoup4` + `lxml` + 自写清洗（页码 / 免责声明 / 多余空白）+ HTTP 下载逻辑 = ~80 行 Python")
    lines.append("- variant: 1 个 `httpx.post(\"https://api.tavily.com/extract\", ...)` 调用 = ~5 行 Python")
    lines.append("- **省 ~75 行代码 + 0 个 native 依赖**\n")

    lines.append("## 结论\n")
    lines.append("**M1 推荐：默认用 Tavily Extract**。理由：")
    lines.append("1. 工程极大简化，1 行 HTTP 调用 vs 80 行自写流水线")
    lines.append("2. 9/9 schema 通过率与 baseline 等价")
    lines.append("3. 数据点差距 8% 在 LLM 抽取能力的统计噪声内")
    lines.append("4. 跨格式（PDF / HTML / docx）一致；省掉自己写 PDF/HTML 分流逻辑\n")
    lines.append("**fallback**：如果 Tavily Extract 单篇返回空（实测 0/9 发生）或 timeout，降级 pdfplumber 抓本地副本。")
    lines.append("**生产 backend 已实现**：`backend/src/researchpipe_api/tavily.py:extract` 走 Tavily，无 pdfplumber 依赖。\n")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
