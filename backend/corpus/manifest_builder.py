"""Walk 2026研报合集 corpus, parse filenames, write to PG corpus_files.

Filename patterns:
    1. broker_dated:  '<title>-YYMMDD-<broker>-<pages>页.pdf'
    2. titled_only:   '<title>-<pages>页.pdf'

Idempotent — uses ON CONFLICT (file_path) DO NOTHING.

Run:
    uv run python -m corpus.manifest_builder
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

import asyncpg

# Allow `from src.researchpipe_api.aliases import ALIASES` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from researchpipe_api.aliases import ALIASES  # noqa: E402

CORPUS_ROOT = Path("/mnt/e/BaiduNetdiskDownload/2026研报/2026报告合集")
DSN = os.environ.get("RP_CORPUS_DSN", "postgresql://postgres:postgres@192.168.1.23:5433/researchpipe")

# Pattern 1: <title>-YYMMDD-<broker>-<pages>页.pdf
RE_BROKER = re.compile(r"^(?P<title>.+)-(?P<ymd>\d{6})-(?P<broker>[^-]+?)-(?P<pages>\d+)页\.pdf$")
# Pattern 2: <title>-<pages>页.pdf
RE_TITLED = re.compile(r"^(?P<title>.+)-(?P<pages>\d+)页\.pdf$")
# Pattern 3: <broker_cn 证券>-<title>-YYMMDD.pdf  (国内 broker 前置)
RE_BROKER_FIRST = re.compile(r"^(?P<broker>[一-鿿]+证券)-(?P<title>.+)-(?P<ymd>\d{6})\.pdf$")
# Pattern 4: 国际投行 - title - numeric id
_INTL_PREFIXES = (
    "Morgan Stanley", "UBS", "Deutsche Bank", "Barclays", "JPMorgan", "JP Morgan",
    "Goldman", "Citi", "Bank of America", "BofA", "Nomura", "HSBC", "BNP",
    "Credit Suisse", "Macquarie", "Jefferies",
)
RE_INTL_DASH = re.compile(
    r"^(?P<broker>(?:" + "|".join(re.escape(p) for p in _INTL_PREFIXES) + r")[^-]*)-(?P<title>.+)-(?P<id>\d{6,})\.pdf$"
)
# Pattern 5: <broker_intl>_<title>.pdf
RE_INTL_UNDERSCORE = re.compile(
    r"^(?P<broker>(?:" + "|".join(re.escape(p) for p in _INTL_PREFIXES) + r"))_(?P<title>.+)\.pdf$"
)
# Pattern 6: <title>（<pages>页）.pdf  (全角括号)
RE_FULL_PAREN = re.compile(r"^(?P<title>.+)[（(](?P<pages>\d+)页[)）]\.pdf$")
# Pattern 7: YYYY-MM-DD-<rest>.pdf — try as Pattern 4 inside rest
RE_ISO_PREFIX = re.compile(r"^(?P<iso>\d{4}-\d{2}-\d{2})-(?P<rest>.+)\.pdf$")
# Library dir like '01_重点报告-331份' → strip '-NNN份' tail
RE_LIB = re.compile(r"^(\d+_[^-]+?)(?:-\d+份)?$")


def parse_yymmdd(s: str) -> date | None:
    """260103 → 2026-01-03; 251231 → 2025-12-31."""
    try:
        yy, mm, dd = int(s[0:2]), int(s[2:4]), int(s[4:6])
        year = 2000 + yy
        return date(year, mm, dd)
    except Exception:
        return None


def match_industry_tags(title: str) -> list[str]:
    """Match alias keys whose name_patterns appear in title."""
    tags: list[str] = []
    for key, alias in ALIASES.items():
        patterns = alias.get("name_patterns", [])
        for p in patterns:
            if p and p in title:
                tags.append(key)
                break
    return tags


def parse_library(dirname: str) -> str:
    m = RE_LIB.match(dirname)
    return m.group(1) if m else dirname


def parse_filename(name: str) -> dict | None:
    """Returns dict with title/broker/report_date/pages/filename_pattern, or None.

    Tries patterns in priority order — most specific first.
    """
    # P1: <title>-YYMMDD-<broker>-<pages>页.pdf
    m = RE_BROKER.match(name)
    if m:
        return {
            "title": m.group("title").strip(),
            "broker": m.group("broker").strip(),
            "report_date": parse_yymmdd(m.group("ymd")),
            "pages": int(m.group("pages")),
            "filename_pattern": "broker_dated",
        }
    # P3: <broker_cn>-<title>-YYMMDD.pdf (broker first 中文)
    m = RE_BROKER_FIRST.match(name)
    if m:
        return {
            "title": m.group("title").strip(),
            "broker": m.group("broker").strip(),
            "report_date": parse_yymmdd(m.group("ymd")),
            "pages": None,
            "filename_pattern": "broker_first_cn",
        }
    # P4: 国际投行 - title - numeric id
    m = RE_INTL_DASH.match(name)
    if m:
        # Normalize multi-line broker like 'Morgan Stanley Fixed' -> keep
        return {
            "title": m.group("title").strip(),
            "broker": m.group("broker").strip(),
            "report_date": None,
            "pages": None,
            "filename_pattern": "intl_dash",
        }
    # P5: <broker_intl>_<title>.pdf
    m = RE_INTL_UNDERSCORE.match(name)
    if m:
        return {
            "title": m.group("title").replace("_", " ").strip(),
            "broker": m.group("broker").strip(),
            "report_date": None,
            "pages": None,
            "filename_pattern": "intl_underscore",
        }
    # P7: ISO date prefix → recurse on rest as a new filename
    m = RE_ISO_PREFIX.match(name)
    if m:
        iso, rest = m.group("iso"), m.group("rest")
        try:
            iso_dt = date.fromisoformat(iso)
        except ValueError:
            iso_dt = None
        # Try to extract broker + title from rest using intl-dash style
        sub = RE_INTL_DASH.match(rest + ".pdf")
        if sub:
            return {
                "title": sub.group("title").strip(),
                "broker": sub.group("broker").strip(),
                "report_date": iso_dt,
                "pages": None,
                "filename_pattern": "iso_prefix_intl",
            }
        # Fall back: use rest as title
        return {
            "title": rest.strip(),
            "broker": None,
            "report_date": iso_dt,
            "pages": None,
            "filename_pattern": "iso_prefix",
        }
    # P6: 全角括号页数
    m = RE_FULL_PAREN.match(name)
    if m:
        return {
            "title": m.group("title").strip(),
            "broker": None,
            "report_date": None,
            "pages": int(m.group("pages")),
            "filename_pattern": "full_paren_pages",
        }
    # P2: <title>-<pages>页.pdf  (greedy fallback for "页" suffix)
    m = RE_TITLED.match(name)
    if m:
        return {
            "title": m.group("title").strip(),
            "broker": None,
            "report_date": None,
            "pages": int(m.group("pages")),
            "filename_pattern": "titled_only",
        }
    # P8: ultimate fallback — keep filename (minus .pdf) as title.
    # Better than `unparsed` for downstream embedding step which uses PDF body anyway.
    if name.lower().endswith(".pdf"):
        return {
            "title": name[:-4].strip(),
            "broker": None,
            "report_date": None,
            "pages": None,
            "filename_pattern": "title_fallback",
        }
    return None


def walk_corpus(root: Path):
    """Yield (week, library, file_path, size, parsed, raw_name) for every PDF.

    Robust to OSError (network/Windows mount hiccups) — logs and skips bad dirs/files.
    """
    if not root.exists():
        raise SystemExit(f"corpus root not found: {root}")
    try:
        week_dirs = sorted(root.iterdir())
    except OSError as e:
        print(f"[corpus] WARN cannot list root: {e}")
        return
    for week_dir in week_dirs:
        try:
            if not week_dir.is_dir():
                continue
        except OSError as e:
            print(f"[corpus] WARN skip week {week_dir!r}: {e}")
            continue
        week = week_dir.name
        try:
            lib_dirs = sorted(week_dir.iterdir())
        except OSError as e:
            print(f"[corpus] WARN cannot list week {week}: {e}")
            continue
        for lib_dir in lib_dirs:
            try:
                if not lib_dir.is_dir():
                    continue
            except OSError as e:
                print(f"[corpus] WARN skip lib {lib_dir!r}: {e}")
                continue
            library = parse_library(lib_dir.name)
            try:
                files = list(lib_dir.iterdir())
            except OSError as e:
                print(f"[corpus] WARN cannot list {week}/{library}: {e}")
                continue
            for fp in files:
                try:
                    if fp.suffix.lower() != ".pdf" or not fp.is_file():
                        continue
                    size = fp.stat().st_size
                except OSError as e:
                    print(f"[corpus] WARN skip file {fp.name!r}: {e}")
                    continue
                parsed = parse_filename(fp.name)
                if not parsed:
                    yield (week, library, str(fp), size, None, fp.name)
                    continue
                yield (week, library, str(fp), size, parsed, fp.name)


async def main():
    print(f"[corpus] root: {CORPUS_ROOT}")
    print(f"[corpus] DSN:  {DSN}")
    started = time.time()

    pool = await asyncpg.create_pool(DSN, min_size=1, max_size=4)
    n_total = 0
    n_unparsed = 0
    n_with_broker = 0
    batch = []
    BATCH = 500

    async with pool.acquire() as cn:
        for week, library, file_path, file_size, parsed, raw_name in walk_corpus(CORPUS_ROOT):
            n_total += 1
            if parsed is None:
                n_unparsed += 1
                # Insert with empty fields so we don't lose track of the file
                batch.append(
                    (week, library, raw_name[:200], None, None, None,
                     [], file_path, file_size, "unparsed")
                )
            else:
                if parsed["broker"]:
                    n_with_broker += 1
                tags = match_industry_tags(parsed["title"])
                batch.append(
                    (week, library, parsed["title"], parsed["broker"],
                     parsed["report_date"], parsed["pages"],
                     tags, file_path, file_size, parsed["filename_pattern"])
                )

            if len(batch) >= BATCH:
                await cn.executemany(
                    """
                    INSERT INTO corpus_files
                      (week, library, title, broker, report_date, pages,
                       industry_tags, file_path, file_size, filename_pattern)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                    ON CONFLICT (file_path) DO NOTHING
                    """,
                    batch,
                )
                batch.clear()
                if n_total % 2000 == 0:
                    print(f"[corpus] {n_total:>6}  files indexed | unparsed={n_unparsed} brokered={n_with_broker}")

        if batch:
            await cn.executemany(
                """
                INSERT INTO corpus_files
                  (week, library, title, broker, report_date, pages,
                   industry_tags, file_path, file_size, filename_pattern)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                ON CONFLICT (file_path) DO NOTHING
                """,
                batch,
            )

    elapsed = time.time() - started
    print(f"\n[corpus] DONE in {elapsed:.1f}s")
    print(f"[corpus]   total files       : {n_total}")
    print(f"[corpus]   parsed (broker+date): {n_with_broker}")
    print(f"[corpus]   unparsed           : {n_unparsed}")

    # Quick stats
    async with pool.acquire() as cn:
        row = await cn.fetchrow("SELECT count(*) AS n FROM corpus_files")
        print(f"[corpus]   rows in DB now    : {row['n']}")
        row = await cn.fetchrow(
            "SELECT count(DISTINCT broker) AS n FROM corpus_files WHERE broker IS NOT NULL"
        )
        print(f"[corpus]   distinct brokers  : {row['n']}")
        row = await cn.fetchrow(
            "SELECT count(*) AS n FROM corpus_files WHERE array_length(industry_tags, 1) > 0"
        )
        print(f"[corpus]   with industry tag : {row['n']}")

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
