"""Run 10 scenarios end-to-end against real backend, record responses + audit."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from .scenarios import SCENARIOS

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "simulation"
OUT.mkdir(parents=True, exist_ok=True)

BACKEND = "http://localhost:3725"
KEY = "rp-demo-public"
HEADERS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
TIMEOUT = 60.0


def run_one(scenario: dict[str, Any], cli: httpx.Client) -> dict[str, Any]:
    sid = scenario["id"]
    started = time.time()

    # URL-encode any non-ASCII in path
    raw_path = scenario["path"]
    parts = raw_path.split("/")
    encoded_parts = [quote(p, safe="") if any(ord(c) > 127 for c in p) else p for p in parts]
    path = "/".join(encoded_parts)
    url = f"{BACKEND}{path}"
    method = scenario["method"]
    body = scenario.get("body")
    is_async = scenario.get("async", False)
    max_wait = scenario.get("max_wait_s", 60)

    try:
        if method == "POST":
            resp = cli.post(url, json=body or {})
        else:
            resp = cli.get(url)
        first_status = resp.status_code
        first_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"_raw": resp.text[:300]}
    except Exception as e:
        return _fail(sid, f"request_error: {type(e).__name__}: {e}", scenario, started)

    if first_status >= 400:
        return _fail(sid, f"http_{first_status}", scenario, started, body=first_data)

    final_data = first_data

    if is_async:
        rid = first_data.get("request_id")
        if not rid:
            return _fail(sid, "async_no_request_id", scenario, started, body=first_data)
        # Poll
        polls = 0
        deadline = time.time() + max_wait
        while time.time() < deadline:
            polls += 1
            time.sleep(3)
            try:
                poll_resp = cli.get(f"{BACKEND}/v1/jobs/{rid}")
                poll_data = poll_resp.json()
                status = poll_data.get("status")
                if status == "completed":
                    final_data = poll_data.get("result") or poll_data
                    break
                if status == "failed":
                    return _fail(sid, f"job_failed: {poll_data.get('error')}", scenario, started, body=poll_data)
            except Exception as e:
                return _fail(sid, f"poll_error: {e}", scenario, started)
        else:
            return _fail(sid, f"job_timeout_after_{max_wait}s", scenario, started)

    elapsed = round((time.time() - started) * 1000, 1)

    # Validate expected fields — check top-level OR nested under "extraction" / "result"
    issues: list[str] = []
    expected_fields = scenario.get("expected_fields") or []
    flat = (final_data or {}).copy() if isinstance(final_data, dict) else {}
    if isinstance(flat.get("extraction"), dict):
        flat.update(flat["extraction"])  # for extract/research style responses
    if isinstance(flat.get("result"), dict):
        flat.update(flat["result"])  # for async job responses
    for f in expected_fields:
        if f not in flat:
            issues.append(f"missing:{f}")

    # Validate language
    if scenario.get("expect_language"):
        actual = (final_data.get("extraction") or {}).get("language") if "extraction" in final_data else final_data.get("language")
        expected = scenario["expect_language"]
        if actual != expected:
            issues.append(f"language:expected={expected}, got={actual}")

    if scenario.get("expect_broker_country"):
        actual = flat.get("broker_country")
        if actual != scenario["expect_broker_country"]:
            issues.append(f"broker_country:expected={scenario['expect_broker_country']}, got={actual}")

    # Validate min total (data endpoints)
    if scenario.get("expect_min_total"):
        total = final_data.get("total")
        if not isinstance(total, int) or total < scenario["expect_min_total"]:
            issues.append(f"total:expected>={scenario['expect_min_total']}, got={total}")

    # Validate providers_attempted
    if scenario.get("expect_providers_attempted"):
        n = scenario["expect_providers_attempted"]
        attempted = ((final_data.get("metadata") or {}).get("providers_attempted") or [])
        if len(attempted) < n:
            issues.append(f"providers_attempted:expected>={n}, got={len(attempted)}")

    # Validate credits range
    cmin, cmax = scenario.get("credits_expected", (0, 9999))
    md = final_data.get("metadata") or {}
    credits = md.get("credits_charged")
    if isinstance(credits, (int, float)):
        if credits < cmin or credits > cmax:
            issues.append(f"credits:expected_range=[{cmin},{cmax}], got={credits}")

    return {
        "id": sid,
        "persona": scenario["persona"],
        "story": scenario["story"],
        "method": method,
        "path": raw_path,
        "elapsed_ms": elapsed,
        "ok": len(issues) == 0,
        "issues": issues,
        "response_keys": list((final_data or {}).keys())[:15],
        "credits_charged": credits,
        "data_sources_used": md.get("data_sources_used"),
        "first_status": first_status,
        "polls": polls if is_async else 0,
        "response_sample": _truncate_for_log(final_data),
    }


def _fail(sid: str, reason: str, scenario: dict, started: float, body: Any = None) -> dict[str, Any]:
    return {
        "id": sid,
        "persona": scenario["persona"],
        "story": scenario["story"],
        "method": scenario["method"],
        "path": scenario["path"],
        "elapsed_ms": round((time.time() - started) * 1000, 1),
        "ok": False,
        "issues": [reason],
        "response_sample": body,
    }


def _truncate_for_log(data: Any, max_len: int = 1500) -> Any:
    if data is None:
        return None
    s = json.dumps(data, ensure_ascii=False)[:max_len]
    return json.loads(s) if s.endswith("}") or s.endswith("]") else {"_truncated": s}


def main():
    cli = httpx.Client(timeout=TIMEOUT, headers=HEADERS)
    results = []
    for s in SCENARIOS:
        print(f"\n=== {s['id']} | {s['persona']} ===")
        print(f"    {s['story']}")
        print(f"    {s['method']} {s['path']}")
        r = run_one(s, cli)
        flag = "✅" if r["ok"] else f"❌ {r['issues']}"
        print(f"    → {flag} {r['elapsed_ms']}ms")
        results.append(r)
        # Save full response for audit
        (OUT / f"{s['id']}.json").write_text(
            json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    cli.close()

    # Summary
    n_ok = sum(1 for r in results if r["ok"])
    summary = {
        "n_total": len(results),
        "n_ok": n_ok,
        "n_failed": len(results) - n_ok,
        "rows": [
            {
                "id": r["id"],
                "ok": r["ok"],
                "elapsed_ms": r["elapsed_ms"],
                "issues": r["issues"],
                "credits": r.get("credits_charged"),
                "sources": r.get("data_sources_used"),
            }
            for r in results
        ],
    }
    (OUT / "_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n📊 SUMMARY: {n_ok}/{len(results)} ok")
    for r in results:
        if not r["ok"]:
            print(f"  ❌ {r['id']}: {r['issues']}")


if __name__ == "__main__":
    main()
