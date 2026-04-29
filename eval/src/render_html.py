"""Render W1 eval markdown bundle into one self-contained HTML for browser viewing."""
from __future__ import annotations

from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "output"
HTML_OUT = OUT_DIR / "W1_eval_view.html"

REPORTS = [
    ("🌙 OVERNIGHT_RESULTS_3（v3 全套壳真化，最新）", ROOT.parent / "OVERNIGHT_RESULTS_3.md"),
    ("🌙 OVERNIGHT_RESULTS（起床先看这个）", ROOT.parent / "OVERNIGHT_RESULTS.md"),
    ("🔍 QUALITY_AUDIT（22 任务质量复查 + 修复）", ROOT.parent / "QUALITY_AUDIT.md"),
    ("Code Review (Step 11)", ROOT.parent / "CODE_REVIEW.md"),
    ("PRD/EDD 修订建议", ROOT.parent / "PRD_EDD_REVISIONS.md"),
    ("🌙 OVERNIGHT_RESULTS_2（第二夜）", ROOT.parent / "OVERNIGHT_RESULTS_2.md"),
    ("🌙 OVERNIGHT_RESULTS（第一夜）", ROOT.parent / "OVERNIGHT_RESULTS.md"),
    ("SDK / OpenAPI 一致性 check", ROOT.parent / "sdk_consistency_check.md"),
    ("数据获取层审计", OUT_DIR / "data_audit_2026-04-29.md"),
    ("C 层 30 家券商 + 公开站点", OUT_DIR / "c_layer_report.md"),
    ("LLM 6 档完整 benchmark", OUT_DIR / "llm_benchmark_full.md"),
    ("Tavily Research 端点实测", OUT_DIR / "tavily_research_report.md"),
    ("Tavily Extract vs pdfplumber A/B", OUT_DIR / "extract_ab_report.md"),
    ("W1 prompt 验证总报告", OUT_DIR / "W1_eval_2026-04-29.md"),
    ("V4-Pro no-think vs V4-Flash think A/B", OUT_DIR / "ab_compare.md"),
]

READABLE_ORDER = [
    "ea_36kr_2026",
    "ea_taiping_2026",
    "ea_kaiyuan_2026",
    "semi_dongwu_2026",
    "semi_dongxing_2025",
    "semi_dongwu_top10_2026",
    "bio_strategy_2026",
    "bio_gs_2025",
    "bio_ms_2025",
]

CSS = """
:root { --ink: #051C2C; --accent: #2251FF; --line: #E6E2DA; --cream: #FBFBF7; --muted: #6B7280; }
* { box-sizing: border-box; }
html { -webkit-font-smoothing: antialiased; }
body {
  margin: 0; color: var(--ink); background: #fff;
  font: 15px/1.6 -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}
.layout { display: grid; grid-template-columns: 240px 1fr; min-height: 100vh; }
nav {
  position: sticky; top: 0; height: 100vh; overflow-y: auto;
  background: var(--cream); border-right: 1px solid var(--line); padding: 24px 16px;
}
nav h2 { font-size: 11px; letter-spacing: .15em; text-transform: uppercase; color: var(--muted); margin: 24px 0 8px; }
nav h2:first-child { margin-top: 0; }
nav a {
  display: block; padding: 6px 8px; color: var(--ink); text-decoration: none;
  font-size: 13.5px; border-left: 2px solid transparent;
}
nav a:hover { border-left-color: var(--accent); color: var(--accent); }
nav .brand { font-weight: 600; font-size: 18px; margin-bottom: 4px; font-family: Georgia, "Noto Serif SC", serif; }
nav .sub { font-size: 12px; color: var(--muted); margin-bottom: 24px; letter-spacing: .04em; }
main { max-width: 920px; padding: 48px 56px; }
section { margin-bottom: 64px; padding-bottom: 32px; border-bottom: 1px solid var(--line); scroll-margin-top: 24px; }
section:last-child { border-bottom: 0; }
section.section-head h1 { font-family: Georgia, "Noto Serif SC", serif; font-size: 36px; letter-spacing: -.02em; margin: 0 0 6px; }
h1, h2, h3 { font-family: Georgia, "Noto Serif SC", serif; letter-spacing: -.01em; color: var(--ink); }
h1 { font-size: 30px; margin: 8px 0 18px; }
h2 { font-size: 22px; margin: 32px 0 12px; }
h3 { font-size: 17px; margin: 22px 0 8px; }
p, li { font-size: 14.5px; }
table { border-collapse: collapse; width: 100%; margin: 14px 0; font-size: 13.5px; }
th, td { border: 1px solid var(--line); padding: 8px 12px; text-align: left; vertical-align: top; }
th { background: var(--cream); font-weight: 600; }
code { background: var(--cream); padding: 2px 6px; border-radius: 3px; font-size: 12.5px; font-family: "JetBrains Mono", "Menlo", monospace; }
pre { background: var(--cream); padding: 14px; border-radius: 4px; overflow-x: auto; }
pre code { background: transparent; padding: 0; }
blockquote { border-left: 3px solid var(--accent); margin: 14px 0; padding: 6px 0 6px 16px; color: var(--ink); background: rgba(34,81,255,.04); }
hr { border: 0; border-top: 1px solid var(--line); margin: 24px 0; }
.tag { display: inline-block; font-size: 11px; padding: 2px 8px; background: var(--cream); border-radius: 999px; margin-left: 6px; color: var(--muted); }
.toc-section { margin-bottom: 12px; }
"""


def md_to_html(text: str) -> str:
    return markdown.markdown(text, extensions=["tables", "fenced_code", "toc"])


def main():
    sections: list[tuple[str, str, str]] = []  # (anchor, title, html)

    for title, path in REPORTS:
        if not path.exists():
            continue
        anchor = path.stem
        sections.append((anchor, title, md_to_html(path.read_text(encoding="utf-8"))))

    for rid in READABLE_ORDER:
        p = OUT_DIR / "readable" / f"{rid}.md"
        if not p.exists():
            continue
        sections.append((rid, f"📄 {rid}", md_to_html(p.read_text(encoding="utf-8"))))

    # Build TOC
    toc_html: list[str] = []
    toc_html.append('<div class="brand">ResearchPipe</div>')
    toc_html.append('<div class="sub">W1 prompt 验证 · 2026-04-29</div>')

    toc_html.append('<h2>报告</h2>')
    for anc, title, _ in sections[:2]:
        toc_html.append(f'<a href="#{anc}">{title}</a>')

    toc_html.append('<h2>9 篇 readable</h2>')
    for anc, title, _ in sections[2:]:
        toc_html.append(f'<a href="#{anc}">{title}</a>')

    body_parts: list[str] = []
    for anc, title, html in sections:
        body_parts.append(f'<section id="{anc}" class="section-head"><h1>{title}</h1>{html}</section>')

    full = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>ResearchPipe W1 eval</title>
<style>{CSS}</style>
</head>
<body>
<div class="layout">
  <nav>{''.join(toc_html)}</nav>
  <main>{''.join(body_parts)}</main>
</div>
</body>
</html>
"""
    HTML_OUT.write_text(full, encoding="utf-8")
    print(f"Wrote {HTML_OUT}")


if __name__ == "__main__":
    main()
