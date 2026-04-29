"""Agent SSE endpoint — POST /v1/agent/ask returns Server-Sent Events stream."""
from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from .. import agent_runner
from ..auth import require_api_key

router = APIRouter(prefix="/v1/agent", tags=["agent"], dependencies=[Depends(require_api_key)])


def _sse_format(event: dict) -> str:
    """Encode dict as SSE 'data: {...}\\n\\n' frame.

    Uses the `event:` field optionally for SSE event-name dispatch on the client.
    """
    name = event.get("event") or "message"
    payload = json.dumps(event, ensure_ascii=False)
    return f"event: {name}\ndata: {payload}\n\n"


async def _stream(events: AsyncIterator[dict]) -> AsyncIterator[bytes]:
    async for ev in events:
        yield _sse_format(ev).encode("utf-8")


@router.post("/ask")
async def agent_ask(body: dict, request: Request):
    """Stream agent reasoning + final answer via SSE.

    Body:
        query: str (required) — natural-language investment-research question.

    Response: text/event-stream with these events:
        tool_call    {tool, args, iteration}
        tool_result  {tool, n_results, n_new_sources, elapsed_ms}
        content      {delta}                          (final answer markdown)
        sources      {sources: [{n, title, broker, date, url, snippet, source_type}]}
        done         {request_id, total_ms, iterations, tool_calls, credits_charged}
        error        {code, message}                  (on agent failure)

    Cite scheme: each fact in `content` should reference [N] matching `sources[N-1].n`.
    """
    query = (body.get("query") or "").strip()
    if not query:
        raise HTTPException(400, "query required")
    if len(query) > 1000:
        raise HTTPException(400, "query too long (max 1000 chars)")

    async def _is_disconnected() -> bool:
        try:
            return await request.is_disconnected()
        except Exception:
            return False

    return StreamingResponse(
        _stream(agent_runner.run_agent(query, is_disconnected=_is_disconnected)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering when proxied
            "Connection": "keep-alive",
        },
    )
