"""百炼 (DashScope OpenAI-compat) client wrapper for ResearchPipe eval."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

API_KEY = os.environ["BAILIAN_API_KEY"]
BASE_URL = os.environ.get(
    "BAILIAN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
)
MODEL = os.environ.get("BAILIAN_MODEL", "deepseek-v4-pro")
ENABLE_THINKING = os.environ.get("BAILIAN_ENABLE_THINKING", "false").lower() == "true"

_client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=600)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
def chat(
    system: str,
    user: str,
    *,
    model: str | None = None,
    response_format: str = "json_object",
    temperature: float = 0.2,
    max_tokens: int = 8000,
    enable_thinking: bool | None = None,
) -> tuple[str, dict]:
    """Run one chat completion. Returns (content, usage_dict).

    enable_thinking: V4 系列默认 True，必须显式 False 才走 no-think 快速通道。
    """
    started = time.time()
    kwargs = dict(
        model=model or MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if response_format == "json_object":
        kwargs["response_format"] = {"type": "json_object"}

    # V4 系列要求通过 extra_body 透传 enable_thinking
    et = ENABLE_THINKING if enable_thinking is None else enable_thinking
    kwargs["extra_body"] = {"enable_thinking": et}

    resp = _client.chat.completions.create(**kwargs)
    elapsed = time.time() - started
    content = resp.choices[0].message.content or ""
    usage = {
        "prompt_tokens": resp.usage.prompt_tokens if resp.usage else None,
        "completion_tokens": resp.usage.completion_tokens if resp.usage else None,
        "total_tokens": resp.usage.total_tokens if resp.usage else None,
        "model": resp.model,
        "elapsed_s": round(elapsed, 2),
    }
    return content, usage


def extract_json(content: str) -> dict:
    """Robustly parse JSON from LLM output (strips ```json fences if any)."""
    text = content.strip()
    if text.startswith("```"):
        # remove first fence line + last fence
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return json.loads(text)
