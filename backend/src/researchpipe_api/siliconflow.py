"""SiliconFlow OpenAI-compatible client — bge-m3 embedding + bge-reranker-v2-m3 rerank."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from .settings import (
    SILICONFLOW_API_KEY,
    SILICONFLOW_BASE_URL,
    SILICONFLOW_EMBED_MODEL,
    SILICONFLOW_RERANK_MODEL,
)

log = logging.getLogger(__name__)

EMBED_BATCH = 64  # bge-m3 supports up to 64 per request
EMBED_DIM = 1024
EMBED_MAX_CHARS = 6000  # bge-m3 8192 token limit; ~1.5 char/token in Chinese
RERANK_MAX_DOCS = 50
EMBED_PARALLEL = 3  # concurrent SF requests (free tier ~3 RPS sustainable; higher → 429)

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=SILICONFLOW_BASE_URL,
            headers={
                "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )
    return _client


async def close():
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


# ─────────────────────────────────────────────────────────────────────────
# Embedding
# ─────────────────────────────────────────────────────────────────────────


_EMBED_SEMA: asyncio.Semaphore | None = None


def _get_embed_sema(parallel: int) -> asyncio.Semaphore:
    global _EMBED_SEMA
    if _EMBED_SEMA is None:
        _EMBED_SEMA = asyncio.Semaphore(parallel)
    return _EMBED_SEMA


async def _embed_one_batch(cli: httpx.AsyncClient, batch: list[str], model: str, parallel: int) -> list[list[float]]:
    sema = _get_embed_sema(parallel)
    body = {"model": model, "input": batch}
    async with sema:
        attempt = 0
        rate_limit_attempt = 0
        while True:
            attempt += 1
            try:
                resp = await cli.post("/embeddings", json=body)
                if resp.status_code == 200:
                    data = resp.json()
                    return [d["embedding"] for d in data["data"]]
                if resp.status_code == 429:
                    # Bounded retry; quota exhaustion shouldn't hang request forever.
                    rate_limit_attempt += 1
                    if rate_limit_attempt > 12:  # ~13 min of cumulative backoff
                        raise RuntimeError(
                            f"SF embed 429 persisted after {rate_limit_attempt} retries"
                        )
                    backoff = min(2 ** rate_limit_attempt, 60)
                    log.warning("SF embed 429 (attempt %s), retry in %ss", rate_limit_attempt, backoff)
                    await asyncio.sleep(backoff)
                    continue
                if resp.status_code in (500, 502, 503, 504) and attempt <= 4:
                    backoff = min(2 ** attempt, 10)
                    log.warning("SF embed status=%s, retry in %ss", resp.status_code, backoff)
                    await asyncio.sleep(backoff)
                    continue
                raise RuntimeError(f"SF embed http {resp.status_code}: {resp.text[:300]}")
            except httpx.ReadTimeout:
                if attempt <= 4:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise


async def embed_texts(texts: list[str], *, model: str | None = None, parallel: int = EMBED_PARALLEL) -> list[list[float]]:
    """Batch embed; chunks into EMBED_BATCH and runs `parallel` requests concurrently."""
    if not SILICONFLOW_API_KEY:
        raise RuntimeError("SILICONFLOW_API_KEY missing")
    if not texts:
        return []
    cli = _get_client()
    model_name = model or SILICONFLOW_EMBED_MODEL
    batches = []
    for i in range(0, len(texts), EMBED_BATCH):
        batch = [t[:EMBED_MAX_CHARS] if t else "(empty)" for t in texts[i : i + EMBED_BATCH]]
        batches.append(batch)
    results = await asyncio.gather(*[_embed_one_batch(cli, b, model_name, parallel) for b in batches])
    out: list[list[float]] = []
    for r in results:
        out.extend(r)
    return out


async def embed_query(query: str) -> list[float]:
    """Single-string convenience for query embedding."""
    embs = await embed_texts([query])
    return embs[0]


# ─────────────────────────────────────────────────────────────────────────
# Rerank
# ─────────────────────────────────────────────────────────────────────────


async def rerank(
    query: str,
    documents: list[str],
    *,
    top_n: int = 15,
    model: str | None = None,
) -> list[dict[str, Any]]:
    """Returns list of {index, relevance_score} sorted desc by score, top_n."""
    if not SILICONFLOW_API_KEY:
        raise RuntimeError("SILICONFLOW_API_KEY missing")
    if not documents:
        return []
    cli = _get_client()
    docs = [(d or "")[:EMBED_MAX_CHARS] for d in documents[:RERANK_MAX_DOCS]]
    body = {
        "model": model or SILICONFLOW_RERANK_MODEL,
        "query": query[:1000],
        "documents": docs,
        "top_n": min(top_n, len(docs)),
        "return_documents": False,
    }
    attempt = 0
    while True:
        attempt += 1
        try:
            resp = await cli.post("/rerank", json=body)
            if resp.status_code == 200:
                data = resp.json()
                return [
                    {"index": r["index"], "relevance_score": r["relevance_score"]}
                    for r in data.get("results", [])
                ]
            if resp.status_code in (429, 500, 502, 503, 504) and attempt <= 4:
                await asyncio.sleep(min(2 ** attempt, 10))
                continue
            raise RuntimeError(f"SF rerank http {resp.status_code}: {resp.text[:300]}")
        except httpx.ReadTimeout:
            if attempt <= 4:
                await asyncio.sleep(2 ** attempt)
                continue
            raise
