"""Basic smoke tests — uses pytest-httpx to mock the API."""
from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from researchpipe import (
    AuthError,
    RateLimitError,
    ResearchPipe,
    ResearchPipeError,
    UpstreamError,
)


@pytest.fixture
def rp():
    client = ResearchPipe(api_key="rp-test", base_url="https://rp.test")
    yield client
    client.close()


def test_constructor_requires_api_key():
    with pytest.raises(ValueError):
        ResearchPipe(api_key="")


def test_search_happy_path(rp, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://rp.test/v1/search",
        json={"query": "test", "results": [{"title": "hello"}], "metadata": {"credits_charged": 1}},
    )
    r = rp.search(query="test")
    assert r["query"] == "test"
    assert r["results"][0]["title"] == "hello"


def test_extract_research_happy_path(rp, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://rp.test/v1/extract/research",
        json={
            "extraction": {"broker": "高盛", "core_thesis": "中国创新药崛起", "confidence_score": 0.9},
            "metadata": {"credits_charged": 5, "partial": False},
        },
    )
    r = rp.extract_research(url="https://example.com/article")
    assert r["extraction"]["broker"] == "高盛"
    assert r["metadata"]["credits_charged"] == 5


def test_auth_error_translation(rp, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://rp.test/v1/me",
        status_code=401,
        json={
            "detail": {
                "code": "auth_invalid",
                "message": "invalid api key",
                "hint_for_agent": "Set Authorization: Bearer rp-...",
            }
        },
    )
    with pytest.raises(AuthError) as exc:
        rp.me()
    assert exc.value.code == "auth_invalid"
    assert exc.value.hint_for_agent and "Bearer" in exc.value.hint_for_agent


def test_rate_limit_retries_then_succeeds(httpx_mock: HTTPXMock):
    rp = ResearchPipe(api_key="rp-test", base_url="https://rp.test", max_retries=3)

    httpx_mock.add_response(
        url="https://rp.test/v1/search",
        status_code=429,
        json={
            "error": {
                "code": "rate_limit_exceeded",
                "message": "60/min",
                "retry_after_seconds": 0,
                "hint_for_agent": "wait + retry",
            }
        },
    )
    httpx_mock.add_response(
        url="https://rp.test/v1/search",
        json={"query": "x", "results": []},
    )
    r = rp.search(query="x")
    assert r["query"] == "x"
    rp.close()


def test_upstream_failure_retries_then_raises(httpx_mock: HTTPXMock):
    rp = ResearchPipe(api_key="rp-test", base_url="https://rp.test", max_retries=2)
    for _ in range(2):
        httpx_mock.add_response(
            url="https://rp.test/v1/search",
            status_code=502,
            json={
                "error": {
                    "code": "upstream_failure",
                    "message": "Tavily down",
                    "hint_for_agent": "Try later",
                }
            },
        )
    with pytest.raises(UpstreamError):
        rp.search(query="x")
    rp.close()


def test_companies_get_url_path(rp, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://rp.test/v1/companies/comp_xyz",
        json={"id": "comp_xyz", "name": "Test"},
    )
    r = rp.companies_get("comp_xyz")
    assert r["id"] == "comp_xyz"


def test_companies_founders_deep(rp, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://rp.test/v1/companies/comp_xyz/founders?deep=true",
        json={"founders": [{"name": "Test"}]},
    )
    r = rp.companies_founders("comp_xyz", deep=True)
    assert r["founders"][0]["name"] == "Test"


def test_research_sector_polls_until_completed(httpx_mock: HTTPXMock):
    rp = ResearchPipe(api_key="rp-test", base_url="https://rp.test")
    httpx_mock.add_response(
        url="https://rp.test/v1/research/sector",
        json={"request_id": "req_abc", "status": "pending"},
    )
    httpx_mock.add_response(
        url="https://rp.test/v1/jobs/req_abc",
        json={"request_id": "req_abc", "status": "completed", "result": {"executive_summary": "OK"}},
    )
    r = rp.research_sector(input="具身智能")
    assert r["status"] == "completed"
    assert r["result"]["executive_summary"] == "OK"
    rp.close()
