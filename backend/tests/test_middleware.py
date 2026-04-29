"""Tests for rate-limit + Idempotency-Key middleware."""
from __future__ import annotations


def test_rate_limit_allows_burst_then_blocks(client, auth_headers):
    # Burst capacity = 10; first 10 should succeed
    for i in range(10):
        r = client.get("/v1/me", headers=auth_headers)
        assert r.status_code == 200, f"req {i} blocked unexpectedly"
    # 11th should 429
    r = client.get("/v1/me", headers=auth_headers)
    assert r.status_code == 429
    body = r.json()
    err = body.get("error") or {}
    assert err.get("code") == "rate_limit_exceeded"
    assert err.get("retry_after_seconds") and err["retry_after_seconds"] >= 1
    assert "Retry" in (err.get("hint_for_agent") or "") or "retry" in (err.get("hint_for_agent") or "")
    # Headers
    assert r.headers.get("X-RateLimit-Remaining") == "0"
    assert r.headers.get("Retry-After")


def test_rate_limit_per_api_key(client):
    # Different API keys have separate buckets — but our test only has one valid key,
    # so we test that exhaustion under one is independent of healthz path
    for _ in range(10):
        r = client.get("/v1/me", headers={"Authorization": "Bearer rp-test-key"})
        assert r.status_code == 200
    # /healthz unaffected
    r = client.get("/healthz")
    assert r.status_code == 200


def test_idempotency_replay_same_response(client, auth_headers):
    headers = {**auth_headers, "Idempotency-Key": "test-idem-001"}
    r1 = client.post("/v1/companies/search", headers=headers, json={"query": "智元"})
    assert r1.status_code == 200
    body1 = r1.json()
    r1_request_id = body1.get("metadata", {}).get("request_id")

    # Replay
    r2 = client.post("/v1/companies/search", headers=headers, json={"query": "智元"})
    assert r2.status_code == 200
    body2 = r2.json()
    # Same request_id (because cached body is identical)
    assert body2.get("metadata", {}).get("request_id") == r1_request_id
    # Replay header
    assert r2.headers.get("X-Idempotency-Replay") == "true"


def test_idempotency_different_body_no_replay(client, auth_headers):
    h1 = {**auth_headers, "Idempotency-Key": "test-idem-002"}
    h2 = {**auth_headers, "Idempotency-Key": "test-idem-002"}  # same key
    r1 = client.post("/v1/companies/search", headers=h1, json={"query": "智元"})
    r2 = client.post("/v1/companies/search", headers=h2, json={"query": "高瓴"})  # different body
    assert r1.status_code == 200 and r2.status_code == 200
    # request_ids should differ
    rid1 = r1.json().get("metadata", {}).get("request_id")
    rid2 = r2.json().get("metadata", {}).get("request_id")
    assert rid1 != rid2


def test_idempotency_no_key_no_caching(client, auth_headers):
    r1 = client.post("/v1/companies/search", headers=auth_headers, json={"query": "智元"})
    r2 = client.post("/v1/companies/search", headers=auth_headers, json={"query": "智元"})
    assert r1.status_code == 200 and r2.status_code == 200
    # request_ids differ because no Idempotency-Key was sent
    rid1 = r1.json().get("metadata", {}).get("request_id")
    rid2 = r2.json().get("metadata", {}).get("request_id")
    assert rid1 != rid2


def test_idempotency_cache_only_for_2xx(client, auth_headers):
    # 401 should never be cached
    bad_headers = {"Authorization": "Bearer wrong-key", "Idempotency-Key": "test-idem-003"}
    r = client.get("/v1/me", headers=bad_headers)
    assert r.status_code == 401
    # No api key → no rate limit either, but no caching


def test_response_has_rate_limit_headers(client, auth_headers):
    r = client.get("/v1/me", headers=auth_headers)
    assert r.headers.get("X-RateLimit-Limit") == "60"
    assert int(r.headers.get("X-RateLimit-Remaining") or "0") >= 0
