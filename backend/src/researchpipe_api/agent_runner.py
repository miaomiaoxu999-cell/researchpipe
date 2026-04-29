"""Agent loop — LLM tool-call orchestration, yields SSE-ready events.

MVP: non-streaming LLM, single emit of final content. Each tool call dispatches
directly to internal functions (no HTTP self-call) for speed.

Events yielded (each is a dict):
    {"event": "tool_call",    "tool": "search_corpus_semantic", "args": {...}, "iteration": 1}
    {"event": "tool_result",  "tool": "...", "n_results": 5, "elapsed_ms": 380}
    {"event": "content",      "delta": "根据浙商证券[1]..."}
    {"event": "sources",      "sources": [{"n":1,"title":"...","broker":"...","date":"...","url":"..."}, ...]}
    {"event": "done",         "request_id": "...", "total_ms": 5400, "iterations": 3, "tool_calls": 4}
    {"event": "error",        "code": "max_iterations", "message": "..."}
"""
from __future__ import annotations

import json
import logging
import secrets
import time
import urllib.parse
from typing import Any, AsyncIterator

import httpx

from . import corpus_db, db, multi_search, siliconflow, web_combined
from .agent_tools import SYSTEM_PROMPT, TOOLS
from .settings import BAILIAN_API_KEY, BAILIAN_BASE_URL, BAILIAN_MODEL

log = logging.getLogger(__name__)

MAX_ITERATIONS = 8
MAX_TOOL_CALLS = 14  # hard cap across all iterations to prevent runaway cost
LLM_TIMEOUT = 60.0


async def _force_final_synthesis(messages: list[dict]) -> str:
    """Force LLM to give final answer with no further tool calls.

    Called when iteration / tool-call budget is exhausted but enough info
    has been gathered. Avoids returning empty error responses to the user.
    """
    msgs = list(messages) + [
        {
            "role": "user",
            "content": (
                "请基于上面已检索到的信息立刻给出最终答案，不要再调用任何工具。"
                "如果信息不足，请明确说明缺失部分。"
            ),
        }
    ]
    try:
        llm_resp = await _llm_chat(msgs, tools=None)
        return (llm_resp.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    except Exception:
        log.exception("force_final_synthesis failed")
        return ""


# ─────────────────────────────────────────────────────────────────────────
# LLM call
# ─────────────────────────────────────────────────────────────────────────


async def _llm_chat(
    messages: list[dict],
    *,
    tools: list[dict] | None = None,
    tool_choice: str = "auto",
) -> dict:
    """Single non-streaming chat completion via Bailian (OpenAI compat)."""
    payload: dict[str, Any] = {
        "model": BAILIAN_MODEL,
        "messages": messages,
        "temperature": 0.3,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice

    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as cli:
        resp = await cli.post(
            f"{BAILIAN_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {BAILIAN_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"LLM http {resp.status_code}: {resp.text[:300]}")
        return resp.json()


# ─────────────────────────────────────────────────────────────────────────
# Tool dispatch — direct calls to internal functions
# ─────────────────────────────────────────────────────────────────────────


async def _dispatch_tool(name: str, args: dict) -> tuple[Any, list[dict]]:
    """Execute one tool. Returns (result_for_llm, source_items_for_citations).

    Each source item: {title, broker, date, url, snippet, source_type}
    """
    started = time.time()

    if name == "search_corpus_metadata":
        res = await corpus_db.corpus_search(
            query=args.get("query"),
            broker=args.get("broker"),
            industry=args.get("industry"),
            week=args.get("week"),
            date_from=_iso(args.get("date_from")),
            date_to=_iso(args.get("date_to")),
            limit=min(int(args.get("limit") or 10), 30),
        )
        sources = [
            {
                "title": r["title"],
                "broker": r["broker"],
                "date": r["report_date"],
                "url": f"corpus://2026/{r['file_path']}",
                "snippet": None,
                "source_type": "corpus_metadata",
                "industry_tags": r["industry_tags"],
            }
            for r in res["results"]
        ]
        return {"total": res["total"], "results": res["results"][:5]}, sources

    if name == "search_corpus_semantic":
        q = args.get("query") or ""
        if not q:
            return {"error": "query required"}, []
        emb = await siliconflow.embed_query(q)
        candidates = await corpus_db.semantic_search(
            emb,
            candidate_top_k=50,
            industry=args.get("industry"),
            broker=args.get("broker"),
        )
        if not candidates:
            return {"results": [], "note": "no chunks matched"}, []
        # Rerank
        rerank_ok = True
        try:
            ranked = await siliconflow.rerank(q, [c["content"] for c in candidates], top_n=min(int(args.get("top_n") or 10), 20))
            results = []
            for r in ranked:
                c = candidates[r["index"]]
                c["rerank_score"] = r["relevance_score"]
                results.append(c)
        except Exception as e:
            log.warning("rerank failed: %s", e)
            rerank_ok = False
            results = candidates[: int(args.get("top_n") or 10)]
            for r in results:
                r["rerank_score"] = None
        sources = [
            {
                "title": c["title"],
                "broker": c["broker"],
                "date": c["report_date"],
                "url": f"corpus://2026/{c['file_path']}#page={c['page_no']}",
                "snippet": c["content"][:300],
                "source_type": "corpus_chunk",
                "page_no": c["page_no"],
                "rerank_score": c.get("rerank_score"),
                "industry_tags": c["industry_tags"],
            }
            for c in results
        ]
        # Trim content for LLM context
        llm_view = [
            {
                "n": i + 1,
                "title": c["title"],
                "broker": c["broker"],
                "date": c["report_date"],
                "page": c["page_no"],
                "content": c["content"][:800],
                "rerank_score": c.get("rerank_score"),
            }
            for i, c in enumerate(results)
        ]
        # max_rerank: distinguish "rerank failed" from "ran but low" — agent must not
        # falsely claim "no relevant content" if rerank service was down.
        if not results:
            max_rerank: float | None = 0.0
        elif not rerank_ok:
            max_rerank = None
        else:
            max_rerank = max((r.get("rerank_score") or 0) for r in results)
        return {"total": len(results), "results": llm_view, "max_rerank": max_rerank, "rerank_ok": rerank_ok}, sources

    if name == "search_companies":
        rows = await db.companies_search(
            query=args.get("query"),
            industry=args.get("industry"),
            limit=min(int(args.get("limit") or 10), 30),
        )
        sources = [
            {
                "title": r["company_name"],
                "broker": None,
                "date": None,
                "url": f"qmp://company/{urllib.parse.quote(r['company_name'])}",
                "snippet": f"行业: {r.get('industry')} / {r.get('sub_industry')}",
                "source_type": "qmp_company",
            }
            for r in rows[:10]
        ]
        return {"total": len(rows), "results": rows[:10]}, sources

    if name == "get_company":
        cid = args.get("company_id")
        if not cid:
            return {"error": "company_id required"}, []
        try:
            data = await db.companies_get(cid)
        except Exception as e:
            return {"error": f"company_get_failed: {e}"}, []
        sources = [
            {
                "title": data.get("company_name") or cid,
                "broker": None,
                "date": None,
                "url": f"qmp://company/{urllib.parse.quote(cid)}",
                "snippet": str(data.get("description") or "")[:300],
                "source_type": "qmp_company",
            }
        ]
        return data, sources

    if name == "search_deals":
        rows = await db.deals_search(
            company_name=args.get("company_name"),
            industry=args.get("industry"),
            round_=args.get("round"),
            limit=min(int(args.get("limit") or 10), 30),
        )
        sources = [
            {
                "title": f"{r.get('company_name')} {r.get('round')}",
                "broker": None,
                "date": str(r.get("event_date")) if r.get("event_date") else None,
                "url": f"qmp://deal/{r.get('event_id')}",
                "snippet": f"金额: {r.get('amount_text') or '未披露'} | 投资方: {r.get('investors_text','')[:120]}",
                "source_type": "qmp_deal",
            }
            for r in rows[:10]
        ]
        return {"total": len(rows), "results": rows[:10]}, sources

    if name == "industry_overview":
        ind = args.get("industry_id")
        if not ind:
            return {"error": "industry_id required"}, []
        try:
            deals = await db.industry_deals(ind, limit=10)
            chain = await web_combined.industry_chain(ind)
            sources = []
            return {"deals": deals, "chain": chain}, sources
        except Exception as e:
            return {"error": str(e)}, []

    if name == "research_sector":
        # Skip in MVP — too slow / async. Hint LLM to use other tools.
        return {"error": "research_sector skipped in MVP — use search_corpus_semantic for substantive analysis"}, []

    if name == "web_search":
        try:
            res = await multi_search.combined_search(
                query=args.get("query") or "",
                max_results=min(int(args.get("max_results") or 5), 15),
            )
            items = res.get("results", [])
            sources = [
                {
                    "title": r.get("title"),
                    "broker": None,
                    "date": r.get("published_date"),
                    "url": r.get("url"),
                    "snippet": (r.get("content") or "")[:300],
                    "source_type": "web",
                }
                for r in items[:10]
            ]
            return {"total": len(items), "results": items[:10]}, sources
        except Exception as e:
            return {"error": f"web_search_failed: {e}"}, []

    return {"error": f"unknown_tool: {name}"}, []


def _iso(s):
    if not s:
        return None
    try:
        from datetime import date

        return date.fromisoformat(s)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────
# Agent loop
# ─────────────────────────────────────────────────────────────────────────


async def run_agent(user_query: str, *, is_disconnected=None) -> AsyncIterator[dict]:
    """Run agent loop and yield events.

    is_disconnected: optional async callable returning True when the client closed
    the SSE connection. Checked between iterations to abort early and stop $ leak.
    """
    request_id = f"agent_{secrets.token_hex(5)}"
    started = time.time()
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]
    all_sources: list[dict] = []
    seen_urls: set[str] = set()
    n_tool_calls = 0
    iteration = 0

    try:
        while iteration < MAX_ITERATIONS:
            # Abort if client gone (free $$ savings).
            if is_disconnected is not None and await is_disconnected():
                log.info("agent: client disconnected, aborting")
                return

            # Hard cap on tool calls (cost protection). Force final synthesis
            # so user gets a real answer rather than an opaque error.
            if n_tool_calls >= MAX_TOOL_CALLS:
                content = await _force_final_synthesis(messages)
                if content:
                    yield {"event": "content", "delta": content}
                else:
                    yield {
                        "event": "error",
                        "code": "max_tool_calls",
                        "message": f"Reached MAX_TOOL_CALLS={MAX_TOOL_CALLS}; aborting.",
                    }
                break

            iteration += 1
            llm_resp = await _llm_chat(messages, tools=TOOLS)
            choices = llm_resp.get("choices") or []
            if not choices:
                yield {"event": "error", "code": "llm_empty_response", "message": "LLM returned no choices."}
                break
            msg = choices[0].get("message") or {}
            tool_calls = msg.get("tool_calls") or []

            if not tool_calls:
                # Final synthesis content
                content = msg.get("content") or ""
                yield {"event": "content", "delta": content}
                break

            # Backfill missing tool_call ids BEFORE we use them anywhere — assistant
            # message's tool_calls[i].id must exactly match the subsequent
            # tool message's tool_call_id for the LLM to accept the conversation.
            for i, tc in enumerate(tool_calls):
                if not tc.get("id"):
                    tc["id"] = f"tc_{n_tool_calls + i + 1}"

            # Append assistant message that has tool_calls
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.get("content"),
                    "tool_calls": tool_calls,
                }
            )

            # Execute tool calls in sequence
            for tc in tool_calls:
                if n_tool_calls >= MAX_TOOL_CALLS:
                    break
                n_tool_calls += 1
                tc_id = tc["id"]  # guaranteed present by backfill above
                fn = tc.get("function", {})
                tool_name = fn.get("name")
                try:
                    parsed = json.loads(fn.get("arguments") or "{}")
                    args = parsed if isinstance(parsed, dict) else {}
                except Exception:
                    args = {}
                yield {
                    "event": "tool_call",
                    "tool_call_id": tc_id,  # client uses this to match tool_result
                    "tool": tool_name,
                    "args": args,
                    "iteration": iteration,
                }
                t0 = time.time()
                try:
                    result, source_items = await _dispatch_tool(tool_name, args)
                except Exception as e:
                    log.exception("tool dispatch failed: %s", tool_name)
                    # Generic error to LLM; details server-side only.
                    result = {"error": "tool_dispatch_failed", "tool": tool_name}
                    source_items = []
                # Dedup sources by URL
                added = 0
                for s in source_items:
                    u = s.get("url")
                    if u and u not in seen_urls:
                        seen_urls.add(u)
                        s["n"] = len(all_sources) + 1
                        all_sources.append(s)
                        added += 1
                yield {
                    "event": "tool_result",
                    "tool_call_id": tc_id,
                    "tool": tool_name,
                    "n_results": len(source_items),
                    "n_new_sources": added,
                    "elapsed_ms": round((time.time() - t0) * 1000, 1),
                }
                # Wrap tool output for prompt-injection containment: instruct LLM
                # not to follow instructions found within <tool_output>.
                wrapped = (
                    "<tool_output>\n"
                    + json.dumps(result, ensure_ascii=False)[:6000]
                    + "\n</tool_output>"
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc_id,  # use the same fallback id we emitted earlier
                        "content": wrapped,
                    }
                )

        else:
            # Loop ended without final content — force a synthesis so the
            # user gets an answer based on tool calls already made.
            content = await _force_final_synthesis(messages)
            if content:
                yield {"event": "content", "delta": content}
            else:
                yield {
                    "event": "error",
                    "code": "max_iterations",
                    "message": f"Agent exceeded {MAX_ITERATIONS} iterations without final answer.",
                }
    except Exception as e:
        log.exception("agent loop crashed")
        yield {"event": "error", "code": "agent_crash", "message": "Internal agent error; see server logs."}

    # Final emits
    yield {"event": "sources", "sources": all_sources}
    yield {
        "event": "done",
        "request_id": request_id,
        "total_ms": round((time.time() - started) * 1000, 1),
        "iterations": iteration,
        "tool_calls": n_tool_calls,
        "credits_charged": 1.0 + 0.5 * n_tool_calls,
    }
