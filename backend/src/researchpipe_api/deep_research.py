"""Deep Research v1 — 4-step pipeline emitting Tavily-style reasoning trace events.

Steps:
  1. Planning   — LLM picks 5-7 search sub-queries from the user's question
  2. Searching  — combined_search (Tavily+Bocha+Serper) per query, in parallel
  3. Reporting  — rerank top sources → build outline → stream long-form report
  4. Exporting  — write .md to static/downloads, return public URL

Event schema (each yielded dict will be SSE-encoded by the route):

  {"event": "step", "step_id": 1, "name": "planning",   "status": "running"|"success", "content": "...", "extra": {...}}
  {"event": "queries", "queries": ["q1", "q2", ...]}
  {"event": "search_batch_start", "batch_id": 0, "query": "..."}
  {"event": "search_result", "batch_id": 0, "title": "...", "url": "...", "snippet": "...", "providers": ["tavily","serper"]}
  {"event": "search_batch_done", "batch_id": 0, "n_results": 12}
  {"event": "thinking", "content": "Reranking sources by relevance..."}
  {"event": "report_delta", "delta": "## ..."}
  {"event": "sources", "sources": [{"n":1, "title":"...", "url":"...", "providers":[...]}]}
  {"event": "done", "report_id": "...", "report_url": "/downloads/...", "total_ms": 142000, "n_sources": 18}
  {"event": "error", "code": "...", "message": "..."}

The pipeline is fault-tolerant: if a step fails the error is yielded and the loop
returns cleanly so the SSE response can close. Caller is `routes/deep_research.py`.
"""
from __future__ import annotations

import asyncio
import json
import logging
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable

import httpx

from . import multi_search, siliconflow
from .settings import (
    BAILIAN_API_KEY,
    BAILIAN_BASE_URL,
    BAILIAN_MODEL,
    SILICONFLOW_API_KEY,
)

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]  # backend/
DOWNLOADS_DIR = ROOT / "static" / "downloads"

LLM_TIMEOUT = 120.0
SEARCH_PARALLEL = 4         # how many sub-queries to run at once
MAX_QUERIES = 7
TOP_SOURCES = 18            # rerank cutoff
REPORT_MAX_TOKENS = 8000
SOURCE_TEXT_CAP = 40_000    # chars budget for sources sent to the report LLM


# ─────────────────────────────────────────────────────────────────────────
# LLM helpers (Bailian / DashScope OpenAI-compat, async via httpx)
# ─────────────────────────────────────────────────────────────────────────


async def _llm_json(messages: list[dict], *, max_tokens: int = 1500) -> dict:
    """Single non-streaming chat completion, parsed as JSON object."""
    payload = {
        "model": BAILIAN_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as cli:
        resp = await cli.post(
            f"{BAILIAN_BASE_URL.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {BAILIAN_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"LLM JSON http {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
    raw = (data.get("choices") or [{}])[0].get("message", {}).get("content") or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


async def _llm_text(messages: list[dict], *, max_tokens: int = 3000) -> str:
    payload = {
        "model": BAILIAN_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": max_tokens,
    }
    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as cli:
        resp = await cli.post(
            f"{BAILIAN_BASE_URL.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {BAILIAN_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"LLM text http {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
    return (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""


async def _llm_stream(
    messages: list[dict],
    on_token: Callable[[str], Awaitable[None]],
    *,
    max_tokens: int = REPORT_MAX_TOKENS,
) -> str:
    """Stream OpenAI-compat SSE; await on_token(delta) per token. Returns full text."""
    payload = {
        "model": BAILIAN_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": max_tokens,
        "stream": True,
    }
    full: list[str] = []
    async with httpx.AsyncClient(timeout=None) as cli:
        async with cli.stream(
            "POST",
            f"{BAILIAN_BASE_URL.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {BAILIAN_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        ) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise RuntimeError(
                    f"LLM stream http {resp.status_code}: {body[:300].decode('utf-8', 'replace')}"
                )
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = (
                    (obj.get("choices") or [{}])[0]
                    .get("delta", {})
                    .get("content")
                ) or ""
                if delta:
                    full.append(delta)
                    await on_token(delta)
    return "".join(full)


# ─────────────────────────────────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────────────────────────────────


def _planning_prompt(today: str) -> str:
    return f"""You are a senior investment research strategist. Today is {today}.
Given a research question, produce a research plan and search queries.

Return JSON with these keys:
  research_plan:    one short paragraph describing the angle of attack
  research_steps:   3-6 numbered analysis steps in the user's language
  search_queries:   5-7 search sub-queries optimised for web search engines

Query design rules:
  - At least one broad overview query and one recent-news query
  - At least one quantitative query (data, statistics, market sizing)
  - At least one competitive-landscape query
  - If the question names a specific company/product, EVERY query must include that name
  - Chinese topics → Chinese queries; global topics → mix Chinese + English
  - Each query short and Google-friendly (≤ 12 tokens)

Always respond in the same language as the user's question.
Return ONLY the JSON object."""


def _outline_prompt(today: str) -> str:
    return f"""You are a senior research strategist. Today is {today}.
Given web search results, produce a detailed report outline as Markdown.

Requirements:
  - 6-8 major sections, named for the specific topic (no generic templates)
  - Under each section, 3-5 bullets describing what to cover, with [N] citations from the source list
  - Note any quantitative anchors (numbers, dates, parties) and which source carries them
  - If a section has thin sources, mark "[sources thin]" so the writer keeps it short
  - Always respond in the same language as the question."""


def _report_prompt(today: str) -> str:
    return f"""You are a senior investment analyst. Today is {today}.
Write a comprehensive research report following the provided outline, synthesising across the source material.

Format requirements (these decide whether the report looks like a real analyst note):
  - Use Markdown headings (##, ###) — at least 4 top-level sections
  - At least 2 Markdown tables for any quantitative comparison (companies, financials, scenarios)
  - Use bullet lists for parallel drivers/risks/catalysts (3+ items)
  - Bold key numbers / company names / verdicts (**...**)
  - Open with `### 核心观点` or `### Key Takeaways` — 3-5 bullets summarising the thesis

Citation rules:
  - Cite every quantitative claim with [N] referencing the numbered source list
  - When sources disagree, flag the disagreement explicitly rather than picking silently
  - Do NOT fabricate figures, dates, or company names — if not in sources, say so
  - Do NOT use general training knowledge to fill gaps

Length target: 4000-6000 words for Chinese topics, 1500-2500 words for English topics.
Always respond in the same language as the user's question."""


# ─────────────────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────────────────


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _step(step_id: int, name: str, status: str, content: str, **extra: Any) -> dict:
    return {
        "event": "step",
        "step_id": step_id,
        "name": name,
        "status": status,
        "content": content,
        **({"extra": extra} if extra else {}),
    }


async def _gather_queries(question: str) -> dict:
    messages = [
        {"role": "system", "content": _planning_prompt(_today())},
        {"role": "user", "content": question},
    ]
    plan = await _llm_json(messages, max_tokens=1200)
    queries = plan.get("search_queries") or []
    if not isinstance(queries, list):
        queries = []
    queries = [str(q).strip() for q in queries if str(q).strip()][:MAX_QUERIES]
    if not queries:
        queries = [question]
    plan["search_queries"] = queries
    if not isinstance(plan.get("research_steps"), list):
        plan["research_steps"] = []
    if not isinstance(plan.get("research_plan"), str):
        plan["research_plan"] = ""
    return plan


async def _search_one_batch(
    batch_id: int,
    query: str,
    queue: asyncio.Queue,
) -> list[dict[str, Any]]:
    """Run combined_search for one sub-query, push events to queue, return result list."""
    await queue.put({"event": "search_batch_start", "batch_id": batch_id, "query": query})
    try:
        resp = await multi_search.combined_search(query, max_results=10)
    except Exception as e:
        await queue.put({
            "event": "search_batch_done",
            "batch_id": batch_id,
            "n_results": 0,
            "error": f"{type(e).__name__}: {str(e)[:120]}",
        })
        return []
    items = resp.get("results") or []
    for r in items:
        await queue.put({
            "event": "search_result",
            "batch_id": batch_id,
            "title": r.get("title") or r.get("url"),
            "url": r.get("url"),
            "snippet": r.get("snippet"),
            "providers": r.get("providers") or [],
        })
    await queue.put({"event": "search_batch_done", "batch_id": batch_id, "n_results": len(items)})
    return items


async def _run_searches(queries: list[str], queue: asyncio.Queue) -> list[dict[str, Any]]:
    """Run search batches with bounded concurrency, streaming events through queue."""
    sem = asyncio.Semaphore(SEARCH_PARALLEL)
    all_items: list[dict[str, Any]] = []

    async def _bounded(batch_id: int, q: str):
        async with sem:
            items = await _search_one_batch(batch_id, q, queue)
            all_items.extend(items)

    await asyncio.gather(*[_bounded(i, q) for i, q in enumerate(queries)])

    # Cross-query dedupe — combined_search dedupes within one query, but the
    # same URL may surface under multiple sub-queries. Keep the first seen.
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for it in all_items:
        url = it.get("url") or ""
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(it)
    return deduped


async def _rerank(question: str, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return top-N sources ranked by relevance. Falls back to rank_score order if SF unavailable."""
    if not sources:
        return []
    if not SILICONFLOW_API_KEY or len(sources) <= TOP_SOURCES:
        # Already sorted by combined_search rank_score desc — just trim.
        return sources[:TOP_SOURCES]
    docs = [
        f"{(s.get('title') or '')}\n{(s.get('snippet') or s.get('content') or '')[:1200]}"
        for s in sources
    ]
    try:
        ranked = await siliconflow.rerank(question, docs, top_n=TOP_SOURCES)
    except Exception as e:
        log.warning("rerank failed (%s); falling back to combined_search ranking", e)
        return sources[:TOP_SOURCES]
    out: list[dict[str, Any]] = []
    for r in ranked:
        idx = r.get("index")
        if isinstance(idx, int) and 0 <= idx < len(sources):
            s = dict(sources[idx])
            s["rerank_score"] = r.get("relevance_score")
            out.append(s)
    return out or sources[:TOP_SOURCES]


def _format_sources_for_llm(sources: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for i, s in enumerate(sources, 1):
        title = s.get("title") or s.get("url") or "(no title)"
        url = s.get("url") or ""
        body = (s.get("content") or s.get("snippet") or "").strip()
        blocks.append(f"[{i}] {title}\nURL: {url}\n{body}")
    text = "\n\n".join(blocks)
    if len(text) > SOURCE_TEXT_CAP:
        text = text[:SOURCE_TEXT_CAP] + "\n\n[... remaining sources truncated for context length]"
    return text


def _save_report(question: str, report_md: str, sources: list[dict[str, Any]]) -> tuple[str, str]:
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    rid = secrets.token_urlsafe(9)
    fname = f"deep_research_{rid}.md"
    header = f"# {question.strip()}\n\n_Generated: {_today()}_\n\n"
    refs = "\n\n## References\n\n" + "\n".join(
        f"{i}. [{s.get('title') or s.get('url')}]({s.get('url')})"
        for i, s in enumerate(sources, 1)
    )
    full = header + report_md.rstrip() + refs + "\n"
    (DOWNLOADS_DIR / fname).write_text(full, encoding="utf-8")
    return rid, f"/downloads/{fname}"


# ─────────────────────────────────────────────────────────────────────────
# Top-level orchestrator (yields events)
# ─────────────────────────────────────────────────────────────────────────


async def run(
    question: str,
    *,
    is_disconnected: Callable[[], Awaitable[bool]] | None = None,
) -> AsyncIterator[dict]:
    """Yield Tavily-style reasoning-trace events. Final event is `done` or `error`."""
    started = time.time()
    request_id = secrets.token_urlsafe(8)

    try:
        # ── Step 1: Planning ────────────────────────────────────────────
        yield _step(1, "planning", "running", "Generating research plan...")
        plan = await _gather_queries(question)
        queries = plan["search_queries"]
        yield {"event": "queries", "queries": queries}
        yield _step(
            1, "planning", "success",
            plan.get("research_plan") or f"Generated {len(queries)} search queries",
            queries=queries,
            research_steps=plan.get("research_steps") or [],
        )

        if is_disconnected and await is_disconnected():
            return

        # ── Step 2: Searching ───────────────────────────────────────────
        yield _step(2, "searching", "running", f"Searching {len(queries)} queries across web sources...")
        queue: asyncio.Queue = asyncio.Queue()
        search_task = asyncio.create_task(_run_searches(queries, queue))
        # Drain the queue until the search task finishes and queue is empty.
        while not (search_task.done() and queue.empty()):
            try:
                ev = await asyncio.wait_for(queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                if is_disconnected and await is_disconnected():
                    search_task.cancel()
                    return
                continue
            yield ev
        sources = await search_task

        if not sources:
            yield {
                "event": "error",
                "code": "no_sources",
                "message": "No sources found. Try a more specific or differently-worded question.",
            }
            return
        yield _step(
            2, "searching", "success",
            f"Collected {len(sources)} unique sources across {len(queries)} queries",
            n_sources=len(sources),
        )

        if is_disconnected and await is_disconnected():
            return

        # ── Step 3: Reporting ───────────────────────────────────────────
        yield _step(3, "reporting", "running", "Reranking sources by relevance...")
        top_sources = await _rerank(question, sources)
        yield {
            "event": "sources",
            "sources": [
                {
                    "n": i + 1,
                    "title": s.get("title"),
                    "url": s.get("url"),
                    "snippet": s.get("snippet"),
                    "providers": s.get("providers") or [],
                    "rerank_score": s.get("rerank_score"),
                }
                for i, s in enumerate(top_sources)
            ],
        }

        if is_disconnected and await is_disconnected():
            return

        yield {"event": "thinking", "content": "Building outline from top sources..."}
        sources_text = _format_sources_for_llm(top_sources)
        outline = await _llm_text(
            [
                {"role": "system", "content": _outline_prompt(_today())},
                {
                    "role": "user",
                    "content": (
                        f"## Research Question\n{question}\n\n"
                        f"## Sources ({len(top_sources)})\n{sources_text}"
                    ),
                },
            ],
            max_tokens=2500,
        )

        if is_disconnected and await is_disconnected():
            return

        yield _step(3, "reporting", "running", "Writing the full report...")
        report_chunks: list[dict] = []

        # Stream the report. Because we can't yield from inside an async callback,
        # the callback pushes deltas into a queue that the outer loop drains.
        rep_queue: asyncio.Queue = asyncio.Queue()

        async def _on_token(delta: str):
            await rep_queue.put({"event": "report_delta", "delta": delta})

        report_task = asyncio.create_task(
            _llm_stream(
                [
                    {"role": "system", "content": _report_prompt(_today())},
                    {
                        "role": "user",
                        "content": (
                            f"## Research Question\n{question}\n\n"
                            f"## Outline\n{outline}\n\n"
                            f"## Source Material ({len(top_sources)} sources, cite as [N])\n{sources_text}"
                        ),
                    },
                ],
                _on_token,
                max_tokens=REPORT_MAX_TOKENS,
            )
        )
        while not (report_task.done() and rep_queue.empty()):
            try:
                ev = await asyncio.wait_for(rep_queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                if is_disconnected and await is_disconnected():
                    report_task.cancel()
                    return
                continue
            report_chunks.append(ev)
            yield ev

        report_md = await report_task
        yield _step(3, "reporting", "success", f"Report drafted ({len(report_md)} chars)")

        # ── Step 4: Exporting ───────────────────────────────────────────
        yield _step(4, "exporting", "running", "Saving report...")
        report_id, report_url = _save_report(question, report_md, top_sources)
        yield _step(4, "exporting", "success", f"Saved as {report_id}")

        yield {
            "event": "done",
            "request_id": request_id,
            "report_id": report_id,
            "report_url": report_url,
            "total_ms": int((time.time() - started) * 1000),
            "n_sources": len(top_sources),
        }

    except Exception as exc:
        log.exception("deep-research pipeline failed")
        yield {
            "event": "error",
            "code": "pipeline_failed",
            "message": f"{type(exc).__name__}: {str(exc)[:240]}",
        }
