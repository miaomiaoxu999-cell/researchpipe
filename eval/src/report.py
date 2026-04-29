"""Render W1 verification report.

Outputs:
  output/W1_eval_<date>.md  — review-ready markdown
  output/readable/<id>.md   — per-report readable view
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTR = ROOT / "output" / "extractions"
READ = ROOT / "output" / "readable"
READ.mkdir(parents=True, exist_ok=True)
MANIFEST = ROOT / "data" / "manifest.json"


SECTOR_LABELS = {
    "embodied_ai": "具身智能",
    "semi_localization": "半导体国产化",
    "biotech_outbound": "创新药出海",
}


def fmt_target_price(tp: dict | None) -> str:
    if not tp:
        return "—"
    v = tp.get("value")
    c = tp.get("currency")
    if v is None and not c:
        return "—"
    return f"{v} {c}" if c else str(v)


def render_one(rec: dict) -> str:
    rid = rec["id"]
    e = rec.get("extraction") or {}
    lines: list[str] = [
        f"# {rid}",
        "",
        f"- **赛道**：{SECTOR_LABELS.get(rec.get('sector'), rec.get('sector', '?'))}",
        f"- **来源 URL**：{rec.get('url', '—')}",
        f"- **耗时**：{rec.get('wall_time_s', '?')}s · "
        f"tokens：{(rec.get('usage') or {}).get('total_tokens', '?')}",
        f"- **schema 校验**：{'✅ pass' if rec.get('schema_ok') else '❌ fail'}",
    ]
    if rec.get("schema_errors"):
        lines.append("- **schema 错误**：" + "；".join(rec["schema_errors"][:3]))
    lines.append("")
    if not e:
        lines.append("> 抽取失败，无可读输出。")
        return "\n".join(lines)

    lines += [
        "## 11 字段输出",
        "",
        f"- **broker**：{e.get('broker', '—')}（country: `{e.get('broker_country', '—')}`，type: `{e.get('source_type', '—')}`）",
        f"- **report_title**：{e.get('report_title', '—')}",
        f"- **report_date**：{e.get('report_date', '—')}",
        f"- **language**：`{e.get('language', '—')}`",
        f"- **target_price**：{fmt_target_price(e.get('target_price'))}",
        f"- **recommendation**：{e.get('recommendation') or '—'}",
        f"- **confidence_score**：`{e.get('confidence_score', '—')}`",
        "",
        "### core_thesis",
        "",
        e.get("core_thesis") or "—",
        "",
        "### key_data_points",
        "",
    ]
    for kp in (e.get("key_data_points") or []):
        m = kp.get("metric", "?")
        v = kp.get("value", "?")
        s = kp.get("source", "?")
        y = kp.get("year") or "?"
        lines.append(f"- **{m}** = {v} _(source: {s}, year: {y})_")
    if not (e.get("key_data_points") or []):
        lines.append("_(空)_")

    lines += ["", "### risks", ""]
    for r in (e.get("risks") or []):
        lines.append(f"- {r}")
    if not (e.get("risks") or []):
        lines.append("_(空)_")

    return "\n".join(lines)


def render_report(date_str: str) -> str:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    summary_path = EXTR / "_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}

    rows = []
    by_sector: dict[str, list[dict]] = {}
    for rec in manifest["reports"]:
        rid = rec["id"]
        p = EXTR / f"{rid}.json"
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        rows.append(data)
        by_sector.setdefault(data["sector"], []).append(data)

        # write readable per-report
        (READ / f"{rid}.md").write_text(render_one(data), encoding="utf-8")

    # Build top-level report
    out: list[str] = []
    out.append(f"# ResearchPipe W1 Prompt 验证报告")
    out.append("")
    out.append(f"**日期**：{date_str}")
    out.append(f"**模型**：deepseek-v4-pro (no-think) · 阿里百炼")
    out.append(f"**端点**：`POST /v1/extract/research`")
    out.append("")
    out.append("## 1. 总览")
    out.append("")
    out.append(f"- 测试样本：{len(rows)} 篇研报，覆盖 {len(by_sector)} 个赛道")
    out.append(f"- Schema 校验通过：{summary.get('n_schema_ok', '?')} / {summary.get('n_total', '?')}")
    out.append(f"- 总 tokens：{summary.get('total_tokens', '?')}")
    out.append(f"- 总耗时：{summary.get('total_wall_s', 0):.0f}s")

    out.append("")
    out.append("## 2. 赛道分布")
    out.append("")
    out.append("| 赛道 | 样本数 | schema OK | 平均 confidence |")
    out.append("|---|---|---|---|")
    for sec, arr in by_sector.items():
        confs = [(r.get("extraction") or {}).get("confidence_score") for r in arr]
        confs = [c for c in confs if isinstance(c, (int, float))]
        avg_c = (sum(confs) / len(confs)) if confs else None
        ok = sum(1 for r in arr if r.get("schema_ok"))
        out.append(
            f"| {SECTOR_LABELS.get(sec, sec)} | {len(arr)} | {ok}/{len(arr)} | "
            f"{avg_c:.2f}" if avg_c is not None else "—" + " |"
        )

    # 自评打分表
    out.append("")
    out.append("## 3. 自评打分（4 维度 × 0-3 分制）")
    out.append("")
    out.append("> 维度：字段覆盖 / 内容准确 / 翻译质量 / 数据点结构。每篇满分 12，≥9 (75%) 算单篇通过。")
    out.append("")
    out.append("| ID | 赛道 | 字段覆盖 | 内容准确 | 翻译 | 数据点 | 总分 | 备注 |")
    out.append("|---|---|---|---|---|---|---|---|")
    for r in rows:
        rid = r["id"]
        sec = SECTOR_LABELS.get(r.get("sector"), r.get("sector"))
        out.append(f"| {rid} | {sec} | _填_ | _填_ | _填_ | _填_ | _合计_ | _填_ |")

    out.append("")
    out.append("## 4. 朋友盲测话术（用户拷贝去微信群 / 即刻发）")
    out.append("")
    out.append("> 复制下面这段话发给 5 个朋友（VC / 投研 / 创业者背景优先），附上 W1_eval_*.md 里的 1-2 篇抽取结果截图。")
    out.append("")
    out.append("---")
    out.append("")
    out.append(
        "Hey，最近在做一个投研垂类 API（叫 **投研派 / ResearchPipe**），"
        "其中一个核心功能是把券商研报 / 海外英文研报一键抽成 11 个结构化字段（"
        "core_thesis / target_price / key_data_points / risks 等），"
        "agent 直接拿来 chain 下一步。"
    )
    out.append("")
    out.append(
        "下面是 9 篇真实研报抽取后的 sample（具身智能 / 半导体国产化 / 创新药出海，含海外 GS / MS）。"
        "想问你两个问题："
    )
    out.append("")
    out.append("1. 看完这些抽取，你觉得**靠谱吗**？哪里你不会信、想自己再核一遍？")
    out.append("2. 假如这是一个 API：5 元一篇 / 10 元一篇 / 20 元一篇，**你愿付哪个档**？为什么？")
    out.append("")
    out.append("不需要写长，1-2 句话就行。谢谢🙏")
    out.append("")
    out.append("---")
    out.append("")
    out.append("## 5. 9 篇详细抽取（点链接看完整 readable 视图）")
    out.append("")
    for r in rows:
        rid = r["id"]
        out.append(f"- [`{rid}`](readable/{rid}.md) — {r.get('url', '')}")

    out.append("")
    out.append("## 6. 决策门")
    out.append("")
    out.append(
        "- ✅ **进入朋友盲测**：自评 ≥ 9/12 平均分（且 schema_ok ≥ 7/9）"
    )
    out.append(
        "- 🔁 **重写 prompt**：自评 < 7 分平均、或 schema_ok < 5 / 9（典型问题：忘字段 / 海外翻译翻车 / 数据点不结构化）"
    )
    out.append(
        "- ⚠️ **调模型**：confidence < 0.5 在 ≥ 3 篇上出现，考虑升 V4-Pro think (L4) 或换 GLM-4.7 对比"
    )
    out.append("")
    out.append("**朋友盲测通过标准**：5 人里 ≥ 3 人愿付 ¥10/篇 → 进入 W2 backend 实现")

    return "\n".join(out)


def main():
    date_str = dt.date.today().isoformat()
    text = render_report(date_str)
    out = ROOT / "output" / f"W1_eval_{date_str}.md"
    out.write_text(text, encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
