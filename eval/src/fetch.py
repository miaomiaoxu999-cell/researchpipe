"""Fetch raw research reports listed in data/manifest.json into data/raw/."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST = ROOT / "data" / "manifest.json"

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)


def fetch_one(rec: dict) -> tuple[str, int]:
    url = rec["url"]
    fmt = rec["format"]
    rid = rec["id"]
    out = RAW_DIR / f"{rid}.{fmt}"
    if out.exists() and out.stat().st_size > 1024:
        return f"SKIP {rid} ({out.stat().st_size} B)", 0
    headers = {"User-Agent": UA, "Accept": "*/*"}
    with httpx.Client(timeout=60.0, follow_redirects=True, headers=headers) as cli:
        r = cli.get(url)
        if r.status_code != 200:
            return f"FAIL {rid} {r.status_code}", r.status_code
        out.write_bytes(r.content)
        return f"OK   {rid} ({len(r.content)} B) → {out.name}", 0


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    fails = []
    for rec in manifest["reports"]:
        msg, code = fetch_one(rec)
        print(msg)
        if code:
            fails.append(rec["id"])
    if fails:
        print(f"\nFAILED: {fails}")
        sys.exit(1)


if __name__ == "__main__":
    main()
