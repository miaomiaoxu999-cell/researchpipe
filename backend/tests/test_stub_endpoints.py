"""All 50 stub endpoints respond 200 with a metadata envelope."""

import pytest


# (method, path, body)
ENDPOINTS = [
    # Account (3)
    ("GET", "/v1/me", None),
    ("GET", "/v1/usage", None),
    ("GET", "/v1/billing", None),
    # Companies (6)
    ("POST", "/v1/companies/search", {}),
    ("GET", "/v1/companies/comp_1", None),
    ("GET", "/v1/companies/comp_1/deals", None),
    ("POST", "/v1/companies/comp_1/peers", {}),
    ("GET", "/v1/companies/comp_1/news", None),
    ("GET", "/v1/companies/comp_1/founders", None),
    # Investors (5)
    ("POST", "/v1/investors/search", {}),
    ("GET", "/v1/investors/inv_1", None),
    ("GET", "/v1/investors/inv_1/portfolio", None),
    ("GET", "/v1/investors/inv_1/preferences", None),
    ("GET", "/v1/investors/inv_1/exits", None),
    # Deals (5)
    ("POST", "/v1/deals/search", {}),
    ("GET", "/v1/deals/deal_1", None),
    ("POST", "/v1/deals/timeline", {}),
    ("POST", "/v1/deals/overseas", {}),
    ("GET", "/v1/deals/deal_1/co_investors", None),
    # Industries (9)
    ("POST", "/v1/industries/search", {}),
    ("GET", "/v1/industries/ind_1/deals", None),
    ("GET", "/v1/industries/ind_1/companies", None),
    ("GET", "/v1/industries/ind_1/chain", None),
    ("GET", "/v1/industries/ind_1/policies", None),
    ("GET", "/v1/industries/ind_1/tech_roadmap", None),
    ("GET", "/v1/industries/ind_1/key_technologies", None),
    ("POST", "/v1/industries/ind_1/maturity", {}),
    ("POST", "/v1/technologies/compare", {}),
    # Valuations (4)
    ("POST", "/v1/valuations/search", {}),
    ("POST", "/v1/valuations/multiples", {}),
    ("POST", "/v1/valuations/compare", {}),
    ("POST", "/v1/valuations/distribution", {}),
    # Filings (5)
    ("POST", "/v1/filings/search", {}),
    ("GET", "/v1/filings/fil_1", None),
    ("POST", "/v1/filings/fil_1/extract", {}),
    ("POST", "/v1/filings/fil_1/risks", {}),
    ("POST", "/v1/filings/fil_1/financials", {}),
    # News & Events (3)
    ("POST", "/v1/news/search", {}),
    ("POST", "/v1/news/recent", {}),
    ("POST", "/v1/events/timeline", {}),
    # Tasks (1)
    ("POST", "/v1/screen", {}),
    # Watch (2)
    ("POST", "/v1/watch/create", {}),
    ("GET", "/v1/watch/watch_1/digest", None),
    # Search line — extra (filing extract / batch / jobs)
    ("POST", "/v1/extract/filing", {}),
    ("POST", "/v1/extract/batch", {}),
    ("GET", "/v1/jobs/job_test_id", None),
]


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
def test_endpoint_returns_200_with_envelope(client, auth_headers, method, path, body):
    if method == "GET":
        r = client.get(path, headers=auth_headers)
    else:
        r = client.post(path, headers=auth_headers, json=body or {})
    assert r.status_code == 200, f"{method} {path}: {r.status_code} {r.text[:200]}"
    data = r.json()
    # Some endpoints (research async + jobs) return JobAccepted/JobResult — different shape
    if path.startswith("/v1/research/") or "/jobs/" in path or path.endswith("/extract/batch"):
        assert "request_id" in data, f"{path}: missing request_id"
        return
    if path == "/v1/me":
        assert "plan" in data
        return
    if path == "/v1/usage":
        assert "items" in data
        return
    if path == "/v1/billing":
        assert "month" in data
        return
    # Generic data endpoints — must have metadata
    assert "metadata" in data, f"{path}: missing metadata in {data!r}"
    md = data["metadata"]
    assert "request_id" in md
    assert "credits_charged" in md


def test_research_sector_returns_job(client, auth_headers):
    r = client.post(
        "/v1/research/sector",
        headers=auth_headers,
        json={"input": "具身智能"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["request_id"].startswith("req_")
    assert body["status"] in {"completed", "pending", "running"}


def test_research_company(client, auth_headers):
    r = client.post(
        "/v1/research/company",
        headers=auth_headers,
        json={"input": "宁德时代"},
    )
    assert r.status_code == 200
    assert "request_id" in r.json()


def test_jobs_get_unknown(client, auth_headers):
    """Stub jobs endpoint synthesizes a result for any unknown id."""
    r = client.get("/v1/jobs/req_unknown_xyz", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"


def test_credits_in_envelope_match_endpoint(client, auth_headers):
    # companies/get → 0.5 credits per PRD
    r = client.get("/v1/companies/comp_x", headers=auth_headers)
    assert r.json()["metadata"]["credits_charged"] == 0.5
    # screen → 5
    r = client.post("/v1/screen", headers=auth_headers, json={})
    assert r.json()["metadata"]["credits_charged"] == 5
    # watch/digest → 10
    r = client.get("/v1/watch/w1/digest", headers=auth_headers)
    assert r.json()["metadata"]["credits_charged"] == 10
