"""Bailian (DashScope) OpenAI-compat LLM client."""
from __future__ import annotations

import json
import time

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .settings import (
    BAILIAN_API_KEY,
    BAILIAN_BASE_URL,
    BAILIAN_ENABLE_THINKING,
    BAILIAN_MODEL,
)

_client = OpenAI(api_key=BAILIAN_API_KEY, base_url=BAILIAN_BASE_URL, timeout=600)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
def chat_json(
    system: str,
    user: str,
    *,
    model: str | None = None,
    enable_thinking: bool | None = None,
    max_tokens: int = 8000,
    temperature: float = 0.2,
) -> tuple[dict, dict]:
    """Run chat completion with response_format=json_object. Returns (parsed_json, usage)."""
    et = BAILIAN_ENABLE_THINKING if enable_thinking is None else enable_thinking
    started = time.time()
    resp = _client.chat.completions.create(
        model=model or BAILIAN_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        extra_body={"enable_thinking": et},
    )
    elapsed = round(time.time() - started, 2)
    raw = resp.choices[0].message.content or "{}"
    parsed = _parse_json_loose(raw)
    usage = {
        "prompt_tokens": resp.usage.prompt_tokens if resp.usage else None,
        "completion_tokens": resp.usage.completion_tokens if resp.usage else None,
        "total_tokens": resp.usage.total_tokens if resp.usage else None,
        "model": resp.model,
        "elapsed_s": elapsed,
    }
    return parsed, usage


def _parse_json_loose(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}
