"""Auth + middleware behavior."""


def test_healthz_no_auth(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root_no_auth(client):
    r = client.get("/")
    assert r.status_code == 200


def test_v1_requires_auth(client):
    r = client.get("/v1/me")
    assert r.status_code == 401
    body = r.json()
    err = body.get("detail") or body
    assert err.get("code") == "auth_invalid"
    assert "Bearer" in (err.get("hint_for_agent") or "")


def test_v1_invalid_bearer(client):
    r = client.get("/v1/me", headers={"Authorization": "Bearer wrong-key"})
    assert r.status_code == 401


def test_v1_malformed_authorization(client):
    r = client.get("/v1/me", headers={"Authorization": "rp-test-key"})  # missing 'Bearer'
    assert r.status_code == 401


def test_v1_authorized_me(client, auth_headers):
    r = client.get("/v1/me", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert "plan" in body
    assert "credits_used_this_month" in body


def test_response_headers_present(client, auth_headers):
    r = client.get("/v1/me", headers=auth_headers)
    assert "X-Response-Time-Ms" in r.headers
    assert "X-RateLimit-Limit" in r.headers
    assert "X-Researchpipe-Version" in r.headers
