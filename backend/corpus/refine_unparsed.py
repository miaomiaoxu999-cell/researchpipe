"""Re-parse unparsed corpus_files rows with new patterns and UPDATE in place.

Run:
    uv run python -m corpus.refine_unparsed
"""
from __future__ import annotations

import asyncio
import os
import sys
from collections import Counter
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from researchpipe_api.aliases import ALIASES  # noqa: E402

from .manifest_builder import (  # noqa: E402
    match_industry_tags,
    parse_filename,
)

DSN = os.environ.get("RP_CORPUS_DSN", "postgresql://postgres:postgres@192.168.1.23:5433/researchpipe")


async def main():
    pool = await asyncpg.create_pool(DSN, min_size=1, max_size=2)
    async with pool.acquire() as cn:
        rows = await cn.fetch(
            "SELECT id, file_path FROM corpus_files WHERE filename_pattern = 'unparsed'"
        )
    print(f"[refine] {len(rows)} unparsed rows to retry")

    updates: list[tuple] = []
    pattern_counter: Counter[str] = Counter()
    still_unparsed = 0

    for r in rows:
        fname = Path(r["file_path"]).name
        p = parse_filename(fname)
        if p is None:
            still_unparsed += 1
            continue
        if p["filename_pattern"] == "unparsed":
            still_unparsed += 1
            continue
        tags = match_industry_tags(p["title"])
        updates.append(
            (
                p["title"],
                p["broker"],
                p["report_date"],
                p["pages"],
                tags,
                p["filename_pattern"],
                r["id"],
            )
        )
        pattern_counter[p["filename_pattern"]] += 1

    print(f"[refine] {len(updates)} can now be parsed; {still_unparsed} still unparsed")
    print(f"[refine] new pattern dist: {dict(pattern_counter)}")

    if updates:
        async with pool.acquire() as cn:
            await cn.executemany(
                """
                UPDATE corpus_files SET
                    title = $1,
                    broker = $2,
                    report_date = $3,
                    pages = $4,
                    industry_tags = $5,
                    filename_pattern = $6
                WHERE id = $7
                """,
                updates,
            )
        print(f"[refine] {len(updates)} rows UPDATEd")

    # Stats
    async with pool.acquire() as cn:
        total = await cn.fetchval("SELECT count(*) FROM corpus_files")
        n_unparsed = await cn.fetchval(
            "SELECT count(*) FROM corpus_files WHERE filename_pattern = 'unparsed'"
        )
        n_with_broker = await cn.fetchval(
            "SELECT count(*) FROM corpus_files WHERE broker IS NOT NULL"
        )
        n_with_industry = await cn.fetchval(
            "SELECT count(*) FROM corpus_files WHERE array_length(industry_tags, 1) > 0"
        )
        print(
            f"\n[refine] DB stats: total={total} unparsed={n_unparsed} "
            f"with_broker={n_with_broker} with_industry={n_with_industry}"
        )

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
