"""Parse PDFs / HTMLs in data/raw/ into clean text in data/parsed/."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pdfplumber
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PARSED = ROOT / "data" / "parsed"
PARSED.mkdir(parents=True, exist_ok=True)
MANIFEST = ROOT / "data" / "manifest.json"


def clean_pdf_text(text: str) -> str:
    # Strip page numbers / running headers patterns common in 中文研报
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        # drop pure-page-number lines
        if re.fullmatch(r"\d{1,3}", s):
            continue
        # drop common boilerplate
        if "请务必阅读正文之后的免责声明" in s and len(s) < 60:
            continue
        if re.fullmatch(r"[-\—_\s]+", s):
            continue
        lines.append(s)
    out = "\n".join(lines)
    # collapse 4+ blank lines
    out = re.sub(r"\n{4,}", "\n\n\n", out)
    return out


def parse_pdf(path: Path) -> str:
    chunks = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            chunks.append(f"\n\n--- page {i} ---\n{text}")
    return clean_pdf_text("\n".join(chunks))


def parse_html(path: Path) -> str:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "lxml")
    # remove nav / footer / scripts
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = []
    for rec in manifest["reports"]:
        rid = rec["id"]
        fmt = rec["format"]
        src = RAW / f"{rid}.{fmt}"
        if not src.exists():
            print(f"MISS {rid}: raw file not present")
            continue
        if fmt == "pdf":
            txt = parse_pdf(src)
        elif fmt == "html":
            txt = parse_html(src)
        else:
            print(f"SKIP {rid}: unknown format {fmt}")
            continue
        out = PARSED / f"{rid}.md"
        out.write_text(txt, encoding="utf-8")
        rows.append((rid, len(txt)))
        print(f"OK {rid:30s} {len(txt):>9} chars → {out.name}")
    print("\nTotal: %d files" % len(rows))
    print("Avg chars: %.0f" % (sum(c for _, c in rows) / max(1, len(rows))))


if __name__ == "__main__":
    main()
