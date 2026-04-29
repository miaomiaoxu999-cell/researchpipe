"""Runner for 10 NEW scenarios v2 — handles idempotency / rate-limit / error / follow-up cases."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from .scenarios_v2 import SCENARIOS_V2

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "simulation"
OUT.mkdir(parents=True, exist_ok=True)

BACKEND = "http://localhost:3725"
KEY = "rp-demo-public"
HEADERS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}


def _encode_path(p: str) -> str:
    parts = p.split("/")
    return "/".join(quote(x, safe="") if any(ord(c) > 127 for c in x) else x for x in parts)


def _flatten(d: Any) -> dict:
    if not isinstance(d, dict):
        return {}
    flat = dict(d)
    if isinstance(d.get("extraction"), dict):
        flat.update(d["extraction"])
    if isinstance(d.get("result"), dict):
        flat.update(d["result"])
    if isinstance(d.get("fields"), dict):
        # filings/extract response shape
        flat.update(d["fields"])
    return flat


def run_scenario(s: dict, cli: httpx.Client) -> dict:
    sid = s["id"]
    started = time.time()
    issues: list[str] = []
    log: dict[str, Any] = {"id": sid, "persona": s["persona"], "story": s["story"]}

    # ─── Burst (rate limit test) ──────────────────────────────────────────
    if s.get("burst_count"):
        statuses = []
        for i in range(s["burst_count"]):
            r = cli.post(f"{BACKEND}{_encode_path(s['path'])}", json=s.get("body") or {})
            statuses.append(r.status_code)
        n_429 = sum(1 for x in statuses if x == 429)
        n_200 = sum(1 for x in statuses if x == 200)
        log.update({"burst_statuses": statuses, "n_200": n_200, "n_429": n_429})
        if s.get("expect_some_429") and n_429 == 0:
            issues.append("expected_some_429_got_none")
        if n_200 < 5:
            issues.append(f"too_few_200:{n_200}")
        log["ok"] = not issues
        log["issues"] = issues
        log["elapsed_ms"] = round((time.time() - started) * 1000, 1)
        # Wait for bucket to refill before next test
        time.sleep(8)
        return log

    # ─── Idempotency test (call twice with same key) ──────────────────────
    if s.get("call_twice") and s.get("idempotency_key"):
        headers_with_idem = {**HEADERS, "Idempotency-Key": s["idempotency_key"] + f"-{int(time.time())}"}
        cli2 = httpx.Client(timeout=60.0, headers=headers_with_idem)
        r1 = cli2.post(f"{BACKEND}{_encode_path(s['path'])}", json=s.get("body") or {})
        d1 = r1.json() if r1.headers.get("content-type", "").startswith("application/json") else {}
        time.sleep(1)
        r2 = cli2.post(f"{BACKEND}{_encode_path(s['path'])}", json=s.get("body") or {})
        d2 = r2.json() if r2.headers.get("content-type", "").startswith("application/json") else {}
        replay = r2.headers.get("x-idempotency-replay")
        rid1 = (d1.get("metadata") or {}).get("request_id")
        rid2 = (d2.get("metadata") or {}).get("request_id")
        log.update(
            {
                "first_status": r1.status_code,
                "second_status": r2.status_code,
                "x_idempotency_replay": replay,
                "rid_1st": rid1,
                "rid_2nd": rid2,
            }
        )
        if replay != "true":
            issues.append("x-idempotency-replay header missing/false")
        if rid1 != rid2:
            issues.append(f"rid_mismatch:{rid1}!={rid2}")
        cli2.close()
        log["ok"] = not issues
        log["issues"] = issues
        log["elapsed_ms"] = round((time.time() - started) * 1000, 1)
        return log

    # ─── Standard call ────────────────────────────────────────────────────
    method = s["method"]
    path = _encode_path(s["path"])
    body = s.get("body")
    try:
        if method == "POST":
            r = cli.post(f"{BACKEND}{path}", json=body or {})
        else:
            r = cli.get(f"{BACKEND}{path}")
        status = r.status_code
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"_raw": r.text[:300]}
    except Exception as e:
        log.update({"ok": False, "issues": [f"request_error:{e}"], "elapsed_ms": round((time.time() - started) * 1000, 1)})
        return log

    log.update({"first_status": status, "data_keys": list((data or {}).keys())[:10]})

    # Error path expectations
    if s.get("expect_error_code"):
        if status < 400:
            issues.append(f"expected_error_got_{status}")
        else:
            err = (data.get("detail") if isinstance(data.get("detail"), dict) else (data.get("error") or {}))
            if not isinstance(err, dict):
                issues.append(f"error_shape_unexpected:{type(err).__name__}")
            else:
                if err.get("code") != s["expect_error_code"]:
                    issues.append(f"error_code:expected={s['expect_error_code']}, got={err.get('code')}")
                hint = err.get("hint_for_agent") or ""
                if s.get("expect_error_hint_contains") and s["expect_error_hint_contains"] not in hint:
                    issues.append(f"hint_missing:'{s['expect_error_hint_contains']}'")
        log["error_body"] = data
        log["ok"] = not issues
        log["issues"] = issues
        log["elapsed_ms"] = round((time.time() - started) * 1000, 1)
        return log

    # Happy path
    if status >= 400:
        issues.append(f"unexpected_http_{status}")
        log["error_body"] = data
        log["ok"] = False
        log["issues"] = issues
        log["elapsed_ms"] = round((time.time() - started) * 1000, 1)
        return log

    flat = _flatten(data)
    for f in s.get("expected_fields") or []:
        if f not in flat:
            issues.append(f"missing:{f}")

    md = data.get("metadata") or {}
    cmin, cmax = s.get("credits_expected") or (0, 9999)
    if cmin is None and cmax is None:
        pass
    else:
        credits = md.get("credits_charged")
        if isinstance(credits, (int, float)) and not (cmin <= credits <= cmax):
            issues.append(f"credits:expected_range=[{cmin},{cmax}],got={credits}")

    log["data_sources"] = md.get("data_sources_used")
    log["credits"] = md.get("credits_charged")
    log["response_summary"] = _short(data)

    # Follow-up call (for watch/create → digest)
    if s.get("follow_up"):
        fu = s["follow_up"]
        wid = data.get("id")
        if wid:
            fu_path = fu["path_template"].replace("{id}", str(wid))
            try:
                fr = cli.request(fu["method"], f"{BACKEND}{fu_path}")
                fd = fr.json() if fr.headers.get("content-type", "").startswith("application/json") else {}
                log["follow_up"] = {"status": fr.status_code, "data_keys": list(fd.keys())[:10], "summary": _short(fd)}
                ff_flat = _flatten(fd)
                for f in fu.get("expected_fields") or []:
                    if f not in ff_flat:
                        issues.append(f"follow_up_missing:{f}")
            except Exception as e:
                issues.append(f"follow_up_error:{e}")

    log["ok"] = not issues
    log["issues"] = issues
    log["elapsed_ms"] = round((time.time() - started) * 1000, 1)
    return log


def _short(data: Any, max_chars: int = 800) -> Any:
    s = json.dumps(data, ensure_ascii=False, default=str)
    return s[:max_chars] + ("...[truncated]" if len(s) > max_chars else "")


def main():
    cli = httpx.Client(timeout=120.0, headers=HEADERS)
    results = []
    for s in SCENARIOS_V2:
        print(f"\n=== {s['id']} | {s['persona']} ===")
        print(f"    {s['story']}")
        r = run_scenario(s, cli)
        flag = "✅" if r.get("ok") else f"❌ {r.get('issues')}"
        print(f"    → {flag} {r.get('elapsed_ms', '?')}ms")
        results.append(r)
        (OUT / f"{s['id']}.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        # Pause between rate-limit-heavy tests
        if s.get("burst_count"):
            time.sleep(2)
    cli.close()

    n_ok = sum(1 for r in results if r.get("ok"))
    print(f"\n📊 SUMMARY: {n_ok}/{len(results)} ok")
    for r in results:
        if not r.get("ok"):
            print(f"  ❌ {r['id']}: {r.get('issues')}")
    (OUT / "_summary_v2.json").write_text(json.dumps({"n_ok": n_ok, "n_total": len(results), "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
