"""Run all 20 UC tests against a deployed ResearchPipe agent.

Usage:
    python run.py [--base https://rp.zgen.xin] [--key rp-demo-public]
                  [--mode corpus_first] [--only uc01_*] [--out results.json]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib import request as urlreq

from cases import CASES


def stream_agent(base: str, key: str, mode: str, query: str, timeout: int = 180,
                 retries: int = 3, retry_delay: float = 5.0) -> dict[str, Any]:
    """POST /v1/agent/ask, consume SSE, return event log + final state.

    Retries on 502/503/504 (transient frp/nginx upstream issues).
    """
    payload = json.dumps({"query": query, "mode": mode}).encode("utf-8")
    url = f"{base.rstrip('/')}/v1/agent/ask"

    t0 = time.time()
    tool_calls: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    content_chunks: list[str] = []
    err: str | None = None
    sources: list[Any] = []
    final_done: bool = False
    iterations: int = 0
    attempts = 0

    # Outer retry loop for upstream transient errors.
    resp_obj = None
    while attempts < retries:
        attempts += 1
        req = urlreq.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            method="POST",
        )
        try:
            resp_obj = urlreq.urlopen(req, timeout=timeout)
            break
        except urlreq.HTTPError as e:
            if e.code in (502, 503, 504) and attempts < retries:
                time.sleep(retry_delay)
                continue
            err = f"http: {e!r}"
            resp_obj = None
            break
        except Exception as e:
            err = f"http: {e!r}"
            resp_obj = None
            break

    try:
        if resp_obj is None:
            raise RuntimeError(err or "no response")
        with resp_obj as resp:
            data_buf = b""
            for line in resp:
                line = line.rstrip(b"\n").rstrip(b"\r")
                if line.startswith(b"data: "):
                    data_buf = line[len(b"data: "):]
                elif line == b"":
                    if not data_buf:
                        continue
                    try:
                        ev = json.loads(data_buf.decode("utf-8"))
                    except Exception as e:
                        err = f"bad json: {e!r}"
                        break
                    et = ev.get("event")
                    if et == "tool_call":
                        tool_calls.append(ev)
                        iterations = max(iterations, int(ev.get("iteration") or 0))
                    elif et == "tool_result":
                        tool_results.append(ev)
                    elif et == "content":
                        d = ev.get("delta") or ev.get("content") or ""
                        if d:
                            content_chunks.append(d)
                    elif et == "done":
                        final_done = True
                    elif et == "sources":
                        sources = ev.get("sources") or []
                    elif et == "error":
                        err = ev.get("error") or ev.get("message") or "unknown"
                    data_buf = b""
    except Exception as e:
        err = f"http: {e!r}"

    elapsed = round(time.time() - t0, 2)
    final_text = "".join(content_chunks)
    return {
        "elapsed_s": elapsed,
        "tool_calls": [
            {
                "iteration": tc.get("iteration"),
                "tool": tc.get("tool"),
                "args": tc.get("args"),
                "id": tc.get("tool_call_id"),
            }
            for tc in tool_calls
        ],
        "tool_results": [
            {
                "tool": tr.get("tool"),
                "n_results": tr.get("n_results"),
                "n_new_sources": tr.get("n_new_sources"),
                "elapsed_ms": tr.get("elapsed_ms"),
                "id": tr.get("tool_call_id"),
                "err": tr.get("error"),
            }
            for tr in tool_results
        ],
        "iterations": iterations,
        "n_tool_calls": len(tool_calls),
        "n_sources": len(sources),
        "answer_chars": len(final_text),
        "answer_text": final_text,
        "has_citation": "[1]" in final_text or "[2]" in final_text,
        "error": err,
        "completed": final_done,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://rp.zgen.xin")
    ap.add_argument("--key", default="rp-demo-public")
    ap.add_argument("--mode", default="corpus_first")
    ap.add_argument("--only", default=None, help="run only this case id")
    ap.add_argument("--out", default="results.json")
    args = ap.parse_args()

    out_dir = Path(__file__).parent
    results_path = out_dir / args.out

    cases = CASES
    if args.only:
        cases = [c for c in cases if c["id"] == args.only]
        if not cases:
            print(f"no case matches --only={args.only}", file=sys.stderr)
            return 2

    print(f"running {len(cases)} cases against {args.base}", flush=True)
    out: list[dict[str, Any]] = []

    for i, c in enumerate(cases, 1):
        print(f"\n[{i}/{len(cases)}] {c['id']}: {c['query'][:60]}...", flush=True)
        # Brief inter-query pause to let frp tunnel recycle connections.
        if i > 1:
            time.sleep(3)
        try:
            r = stream_agent(args.base, args.key, args.mode, c["query"])
        except Exception as e:
            r = {"error": f"runner crash: {e!r}", "elapsed_s": 0, "tool_calls": [],
                 "tool_results": [], "answer_chars": 0, "answer_text": "",
                 "completed": False, "has_citation": False, "iterations": 0,
                 "n_tool_calls": 0, "n_sources": 0}

        rec = {**c, **r}
        out.append(rec)

        # Tiny progress log
        status = "ok" if r["completed"] and not r["error"] else "FAIL"
        print(
            f"   → {status} | iters={r.get('iterations')} | tools={r.get('n_tool_calls')} "
            f"| sources={r.get('n_sources')} | chars={r.get('answer_chars')} "
            f"| t={r.get('elapsed_s')}s | cite={r.get('has_citation')} "
            f"| err={r.get('error') or '-'}",
            flush=True,
        )

        # Persist as we go
        results_path.write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(f"\nwrote {results_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
