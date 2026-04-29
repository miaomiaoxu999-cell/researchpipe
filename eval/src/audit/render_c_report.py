"""Render C-layer audit findings into a markdown report."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
C_DIR = ROOT / "output" / "audit" / "c"
OUT = ROOT / "output" / "c_layer_report.md"


GROUP_LABELS = {
    "tier1_brokers": "第一梯队券商（P0-P1）",
    "tier2_brokers": "第二梯队券商（P2）",
    "tier3_brokers": "第三梯队券商（P3）",
    "public_orgs": "公开站点（信通院 / IDC / 36氪 / 政府）",
}


def main():
    summary = json.loads((C_DIR / "_summary.json").read_text(encoding="utf-8"))
    rows: dict[str, list[dict]] = {}
    for p in C_DIR.glob("*.json"):
        if p.name.startswith("_"):
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        rows.setdefault(d.get("_group", "?"), []).append(d)
    for g in rows:
        rows[g].sort(key=lambda r: r.get("name", ""))

    lines: list[str] = []
    lines.append("# ResearchPipe C 层（自建券商爬虫 + 公开站点）验证报告\n")
    lines.append("**日期**：2026-04-29  \n")
    lines.append(f"**总共**：{summary['n_total']} 个目标 | 全部走 GET + robots.txt（read-only）\n")

    bd = summary["by_difficulty"]
    lines.append("\n## 总览\n")
    lines.append("| 难度分级 | 数量 | 含义 |")
    lines.append("|---|---|---|")
    lines.append(f"| ✅ easy | {bd['✅easy']} | naive HTTP GET 主页 200 + 找到 research/yanbao 链接 |")
    lines.append(f"| ⚠️ moderate | {bd['⚠️moderate']} | 主页 200 但 SPA / heavy JS — 需 Playwright |")
    lines.append(f"| ❌ hard | {bd['❌hard']} | 主页非 200（202 / Cloudflare / DNS / 反爬重定向）|")

    lines.append("\n## 分组细况\n")
    lines.append("| 分组 | 总数 | ✅ | ⚠️ | ❌ |")
    lines.append("|---|---|---|---|---|")
    for g, ginfo in summary["by_group"].items():
        lines.append(
            f"| {GROUP_LABELS.get(g, g)} | {ginfo['total']} | "
            f"{ginfo.get('easy', 0)} | {ginfo.get('mod', 0)} | {ginfo.get('hard', 0)} |"
        )

    for g in ["tier1_brokers", "tier2_brokers", "tier3_brokers", "public_orgs"]:
        items = rows.get(g, [])
        if not items:
            continue
        lines.append(f"\n## {GROUP_LABELS.get(g, g)}\n")
        lines.append("| 名称 | 域名 | 主页 | JS 占比 | 候选研报链接数 | 难度 | 评估 |")
        lines.append("|---|---|---|---|---|---|---|")
        for r in items:
            home = r.get("home", {})
            sc = home.get("status_code") or home.get("error", "?")
            js = r.get("js_heavy_ratio")
            n_links = len(r.get("candidate_links") or [])
            diff = r.get("difficulty", "?")
            assess = r.get("assessment", "")[:60]
            lines.append(
                f"| {r.get('name', '?')} | `{r.get('domain', '?')}` | {sc} | "
                f"{js if js is not None else '—'} | {n_links} | {diff} | {assess} |"
            )

    # Recommendations
    lines.append("\n## 关键发现\n")
    lines.append("1. **0 家券商可用 naive HTTP 直接爬研报**。所有券商主页要么 SPA（vue/react/playwright 才能渲染），要么直接 403 / Cloudflare 拦。")
    lines.append("2. **公开站点也大半 hard**（5/8）。原因：主流 .gov.cn 站点防御机制升级（202 / 重定向 / WAF），中文媒体（36氪 / 亿欧）SPA。")
    lines.append("3. **PRD ch5.3 第三层（30 家券商爬虫）的工作量被低估**：")
    lines.append("   - 不是简单 robots + curl，而是要 Playwright 全家桶 + 反爬代理 + 验证码处理。")
    lines.append('   - 单家从 `能爬` 到 `稳定爬` 工作量 1-2 周，30 家全做 ~半年人年。')
    lines.append("   - **建议：M3 之前**完全跳过 C 层自建，所有研报走 A 线（Tavily / Bocha / Serper）发现 → Tavily Extract / Jina（充值后）抓全文。")

    lines.append("\n## 给 PRD/EDD 的修订建议\n")
    lines.append('- **PRD 5.3** 30 家券商白名单 → 标记 `M5+ 可选，M1-M4 不做`')
    lines.append('- **EDD 5.4** P2 备选 30 家券商爬虫架构 → 加注 `实测主页 100% 反爬，至少 ⚠️moderate 起步，需 Playwright + 代理`')
    lines.append('- **PRD 5.1 第三层** → 改名 `C 层 - 公开站点抓取（兜底）`，明确 M1-M4 主路径走 A 线套壳，不走自爬')

    lines.append("\n## 详细 JSON\n")
    lines.append("每个目标的完整 robots / 主页 / 候选链接 / 评估 在 `output/audit/c/<domain>.json`")
    lines.append("\n```")
    lines.append("output/audit/c/")
    for r in sorted(sum(rows.values(), []), key=lambda x: x.get("domain", "")):
        lines.append(f"  └─ {r.get('domain', '?').replace('.', '_')}.json")
    lines.append("```")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
