"""End-to-end embed pipeline for the 14k 研报 corpus.

For each corpus_files row with embed_status='pending':
    parse PDF → chunk → embed (SiliconFlow bge-m3) → insert to corpus_chunks
    update corpus_files: embed_status='embedded' | 'skipped' | 'failed', chunk_count, embedded_at.

Idempotent — resumes by filtering on embed_status. Run with --limit N for trial.

Usage:
    uv run python -m corpus.embed_pipeline --limit 50      # trial run
    uv run python -m corpus.embed_pipeline                  # full corpus
    uv run python -m corpus.embed_pipeline --concurrency 8  # parallelize PDF parsing
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from researchpipe_api.siliconflow import embed_texts  # noqa: E402

from .chunker import chunk_pdf  # noqa: E402

_PROC_POOL: ProcessPoolExecutor | None = None


def _get_proc_pool(workers: int) -> ProcessPoolExecutor:
    global _PROC_POOL
    if _PROC_POOL is None:
        _PROC_POOL = ProcessPoolExecutor(max_workers=workers)
    return _PROC_POOL

DSN = os.environ.get("RP_CORPUS_DSN", "postgresql://postgres:postgres@192.168.1.23:5433/researchpipe")


async def fetch_pending(pool, limit: int | None = None) -> list[dict]:
    sql = "SELECT id, file_path FROM corpus_files WHERE embed_status = 'pending' ORDER BY id"
    if limit:
        sql += f" LIMIT {int(limit)}"
    async with pool.acquire() as cn:
        rows = await cn.fetch(sql)
    return [{"id": r["id"], "file_path": r["file_path"]} for r in rows]


def parse_one_sync(item: dict) -> dict:
    """CPU-bound: open PDF + chunk. Returns serializable dict (no Chunk dataclass)."""
    try:
        chunks, info = chunk_pdf(item["file_path"])
    except Exception as e:
        return {**item, "ok": False, "error": f"parse_failed: {type(e).__name__}: {e}"[:200], "chunks": [], "info": {}}
    if info.get("looks_scanned"):
        return {**item, "ok": False, "error": "looks_scanned", "chunks": [], "info": info}
    if not chunks:
        return {**item, "ok": False, "error": "no_text", "chunks": [], "info": info}
    # Convert dataclasses to dicts for cross-process serialization
    chunks_serial = [
        {"chunk_idx": c.chunk_idx, "page_no": c.page_no, "content": c.content, "token_count": c.token_count}
        for c in chunks
    ]
    return {**item, "ok": True, "error": None, "chunks": chunks_serial, "info": info}


async def parse_concurrent(items: list[dict], concurrency: int) -> list[dict]:
    """Parse PDFs in parallel via ProcessPool (true CPU parallelism, no GIL)."""
    pool = _get_proc_pool(concurrency)
    loop = asyncio.get_running_loop()
    return await asyncio.gather(*[loop.run_in_executor(pool, parse_one_sync, i) for i in items])


async def embed_and_persist(pool, parsed_items: list[dict]) -> dict:
    """Given parsed items, embed all chunks + write to PG."""
    # Aggregate all chunks across items (chunks are dicts now after process pool)
    flat: list[tuple[int, int, int, int, str, int]] = []  # (file_id, chunk_idx, pos_in_flat, page_no, content, token_count)
    for it in parsed_items:
        if not it["ok"]:
            continue
        fid = it["id"]
        for c in it["chunks"]:
            flat.append((fid, c["chunk_idx"], len(flat), c["page_no"], c["content"], c["token_count"]))

    embedded_count = 0
    rows: list[tuple] = []
    if flat:
        contents = [t[4] for t in flat]
        embs = await embed_texts(contents)
        if len(embs) != len(contents):
            raise RuntimeError(f"embed length mismatch: got {len(embs)}, expected {len(contents)}")
        embedded_count = len(embs)
        # Build insert rows: (file_id, chunk_idx, page_no, content, token_count, embedding)
        rows = [(t[0], t[1], t[3], t[4], t[5], _vec_literal(embs[t[2]])) for t in flat]

    # Update status per file
    now = datetime.now(timezone.utc)
    file_updates: list[tuple] = []
    for it in parsed_items:
        if it["ok"]:
            file_updates.append(("embedded", None, len(it["chunks"]), now, it["id"]))  # chunks list of dicts
        elif it["error"] in {"looks_scanned", "no_text"}:
            file_updates.append(("skipped", it["error"], 0, now, it["id"]))
        else:
            file_updates.append(("failed", it["error"], 0, now, it["id"]))

    # Single transaction over both inserts → no orphans on partial failure.
    async with pool.acquire() as cn:
        async with cn.transaction():
            if rows:
                await cn.executemany(
                    """
                    INSERT INTO corpus_chunks (file_id, chunk_idx, page_no, content, token_count, embedding)
                    VALUES ($1, $2, $3, $4, $5, $6::vector)
                    ON CONFLICT (file_id, chunk_idx) DO NOTHING
                    """,
                    rows,
                )
            await cn.executemany(
                """
                UPDATE corpus_files SET
                  embed_status = $1, embed_error = $2, chunk_count = $3, embedded_at = $4
                WHERE id = $5
                """,
                file_updates,
            )

    return {"chunks_embedded": embedded_count, "files_processed": len(parsed_items)}


def _vec_literal(emb: list[float]) -> str:
    """pgvector accepts string literal '[v1,v2,...]'"""
    return "[" + ",".join(f"{x:.6f}" for x in emb) + "]"


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="cap files processed (for trials)")
    ap.add_argument("--concurrency", type=int, default=4, help="parallel PDF parses")
    ap.add_argument("--batch", type=int, default=8, help="files per embed batch (chunks aggregated)")
    args = ap.parse_args()

    pool = await asyncpg.create_pool(DSN, min_size=1, max_size=4)
    pending = await fetch_pending(pool, limit=args.limit)
    print(f"[embed] {len(pending)} files pending")

    started = time.time()
    total_chunks = 0
    total_files = 0
    n_skipped = 0
    n_failed = 0

    # Process in batches of `batch` files
    for batch_start in range(0, len(pending), args.batch):
        batch = pending[batch_start : batch_start + args.batch]
        t0 = time.time()
        parsed = await parse_concurrent(batch, args.concurrency)
        t_parse = time.time() - t0
        t1 = time.time()
        try:
            stats = await embed_and_persist(pool, parsed)
            t_embed = time.time() - t1
        except Exception as e:
            print(f"[embed] BATCH FAIL @ {batch_start}: {e}")
            # Mark all in batch as 'failed' so we don't retry forever
            ids = [it["id"] for it in batch]
            now = datetime.now(timezone.utc)
            async with pool.acquire() as cn:
                await cn.executemany(
                    """
                    UPDATE corpus_files
                    SET embed_status = 'failed', embed_error = $1, embedded_at = $2
                    WHERE id = $3
                    """,
                    [(f"batch_fail: {str(e)[:160]}", now, i) for i in ids],
                )
            continue
        total_chunks += stats["chunks_embedded"]
        total_files += stats["files_processed"]
        n_skipped += sum(1 for p in parsed if not p["ok"] and p["error"] in {"looks_scanned", "no_text"})
        n_failed += sum(1 for p in parsed if not p["ok"] and p["error"] not in {"looks_scanned", "no_text"})
        elapsed_batch = time.time() - t0
        elapsed_total = time.time() - started
        rate = total_files / elapsed_total
        remaining = (len(pending) - total_files) / rate if rate > 0 else 0
        print(
            f"[embed] +{len(batch):>3} | total {total_files:>5}/{len(pending)} "
            f"| chunks={total_chunks:>6} | skipped={n_skipped:>3} failed={n_failed:>3} "
            f"| parse={t_parse:.1f}s embed={t_embed:.1f}s | ETA {remaining/60:.1f}min"
        )

    elapsed = time.time() - started
    print(f"\n[embed] DONE in {elapsed/60:.1f} min")
    print(f"[embed]   files_embedded: {total_files - n_skipped - n_failed}")
    print(f"[embed]   chunks_total:   {total_chunks}")
    print(f"[embed]   skipped:        {n_skipped} (looks_scanned/no_text)")
    print(f"[embed]   failed:         {n_failed}")

    await pool.close()
    # Shutdown ProcessPool cleanly to avoid leaked semaphore warnings.
    global _PROC_POOL
    if _PROC_POOL is not None:
        _PROC_POOL.shutdown(wait=True)
        _PROC_POOL = None


if __name__ == "__main__":
    asyncio.run(main())
