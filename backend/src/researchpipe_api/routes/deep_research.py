"""Deep Research SSE endpoint — POST /v1/deep-research/run.

Streams Tavily-style reasoning-trace events as the pipeline runs:
  step / queries / search_batch_start / search_result / search_batch_done /
  thinking / report_delta / sources / done / error

Each frame is `event: <name>\\ndata: <json>\\n\\n`. The client reads it via
`fetch` + a streaming reader (see frontend/src/lib/sse-client.ts).
"""
from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from .. import deep_research
from ..auth import require_api_key

router = APIRouter(
    prefix="/v1/deep-research",
    tags=["deep-research"],
    dependencies=[Depends(require_api_key)],
)


def _sse_frame(event: dict) -> str:
    name = event.get("event") or "message"
    payload = json.dumps(event, ensure_ascii=False)
    return f"event: {name}\ndata: {payload}\n\n"


async def _encode(stream: AsyncIterator[dict]) -> AsyncIterator[bytes]:
    async for ev in stream:
        yield _sse_frame(ev).encode("utf-8")


@router.post("/run")
async def deep_research_run(body: dict, request: Request):
    """Run the 4-step deep-research pipeline. Returns text/event-stream.

    Body:
      question: str (required) — the research question

    Events: see module docstring.
    """
    question = (body.get("question") or "").strip()
    if not question:
        raise HTTPException(400, "question required")
    if len(question) > 1000:
        raise HTTPException(400, "question too long (max 1000 chars)")

    async def _disconnected() -> bool:
        try:
            return await request.is_disconnected()
        except Exception:
            return False

    return StreamingResponse(
        _encode(deep_research.run(question, is_disconnected=_disconnected)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
