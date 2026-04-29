"""SQLite persistence layer tests."""
from __future__ import annotations

import asyncio
import time

import pytest


def test_storage_idem_roundtrip():
    from researchpipe_api import storage

    async def go():
        await storage.idem_set("test-key-1", "rp-test", b'{"x":1}', 200, "application/json")
        result = await storage.idem_get("test-key-1")
        assert result is not None
        assert result["body"] == b'{"x":1}'
        assert result["status_code"] == 200
        assert result["content_type"] == "application/json"

    asyncio.run(go())


def test_storage_idem_ttl_expired():
    from researchpipe_api import storage

    async def go():
        await storage.idem_set("test-key-2", "rp-test", b"{}", 200, "json")
        # Manually mark as expired by setting created_at very old
        with storage._conn() as c:
            c.execute("UPDATE idempotency SET created_at = ? WHERE cache_key = ?", (time.time() - 100000, "test-key-2"))
        result = await storage.idem_get("test-key-2", ttl_s=86400)
        assert result is None  # expired

    asyncio.run(go())


def test_storage_jobs_lifecycle():
    from researchpipe_api import storage

    async def go():
        await storage.job_create("req_test_001", "sector")
        job = await storage.job_get("req_test_001")
        assert job is not None
        assert job["status"] == "running"
        assert job["kind"] == "sector"

        await storage.job_complete("req_test_001", {"result_data": "ok"})
        job = await storage.job_get("req_test_001")
        assert job["status"] == "completed"
        assert job["result"]["result_data"] == "ok"

        # Failed job
        await storage.job_create("req_test_002", "company")
        await storage.job_fail("req_test_002", {"message": "test fail"})
        job = await storage.job_get("req_test_002")
        assert job["status"] == "failed"
        assert job["error"]["message"] == "test fail"

    asyncio.run(go())


def test_storage_watchlist_create_get():
    from researchpipe_api import storage

    async def go():
        result = await storage.watch_create(
            "rp-test",
            name="Test Watch",
            industries=["AI"],
            company_ids=[],
            investor_ids=[],
            cron="0 8 * * *",
        )
        wid = result["id"]
        assert wid.startswith("watch_")

        wl = await storage.watch_get(wid)
        assert wl is not None
        assert wl["name"] == "Test Watch"
        assert wl["industries"] == ["AI"]
        assert wl["cron"] == "0 8 * * *"

    asyncio.run(go())


def test_storage_account_billing():
    from researchpipe_api import storage

    storage.ensure_dev_account("rp-account-test")

    async def go():
        me = await storage.account_me("rp-account-test")
        assert me["plan"] == "Pro"
        assert me["credits_limit"] == 80000

        await storage.usage_log("rp-account-test", "search", 1.0)
        await storage.usage_log("rp-account-test", "extract/research", 5.0)

        history = await storage.usage_history("rp-account-test", days=30)
        assert len(history) >= 2

        billing = await storage.billing_estimate("rp-account-test")
        assert billing["plan"] == "Pro"
        assert billing["plan_fee_cny"] == 5000

    asyncio.run(go())


def test_jobs_persisted_across_simulated_restart(client, auth_headers):
    """End-to-end: submit research/sector job → check it persists in SQLite → polling returns it."""
    # Submit
    r = client.post("/v1/research/sector", headers=auth_headers, json={"input": "AI", "time_range": "12m"})
    assert r.status_code == 200
    rid = r.json()["request_id"]

    # Mock-mode synthesize_with_search returns immediately, so the job should be done quickly
    # Poll a few times
    for _ in range(5):
        time.sleep(0.5)
        poll = client.get(f"/v1/jobs/{rid}", headers=auth_headers)
        assert poll.status_code == 200
        body = poll.json()
        if body["status"] in {"completed", "failed"}:
            break

    # Now verify it's in SQLite directly (simulates restart — even if _JOBS dict cleared)
    from researchpipe_api import storage

    async def check():
        return await storage.job_get(rid)

    job = asyncio.run(check())
    # Job should be persisted even if status hasn't moved past 'running' yet
    assert job is not None
    assert job["request_id"] == rid


def test_idempotency_persisted_across_dict_clear(client, auth_headers):
    """Send same request twice with same Idempotency-Key, then clear in-memory shadow,
    third call should still hit SQLite cache."""
    headers = {**auth_headers, "Idempotency-Key": "test-persist-001"}
    r1 = client.post("/v1/companies/search", headers=headers, json={"query": "X"})
    assert r1.status_code == 200
    rid1 = r1.json().get("metadata", {}).get("request_id")

    # Clear in-memory shadow only
    from researchpipe_api import middleware

    middleware.idempotency._store.clear()

    # Replay should still work via SQLite
    r2 = client.post("/v1/companies/search", headers=headers, json={"query": "X"})
    assert r2.status_code == 200
    rid2 = r2.json().get("metadata", {}).get("request_id")
    assert rid1 == rid2  # Same request_id = served from cache
    assert r2.headers.get("X-Idempotency-Replay") == "true"
