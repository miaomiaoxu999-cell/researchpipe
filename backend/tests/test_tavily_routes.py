"""Test the real Tavily-backed routes — mock Tavily HTTP via httpx mock."""
from __future__ import annotations

from unittest.mock import patch, AsyncMock


def _mock_tavily_search_response():
    return {
        "query": "test",
        "answer": "OK",
        "results": [
            {
                "title": "Sample title",
                "url": "https://example.com/a",
                "content": "Sample content",
                "score": 0.9,
                "published_date": "2026-04-29",
            }
        ],
    }


def _mock_tavily_extract_response():
    return {
        "results": [
            {
                "url": "https://example.com/article",
                "title": "Sample Article",
                "raw_content": "Full article body here",
                "images": [],
            }
        ]
    }


def test_search_happy_path(client, auth_headers):
    with patch(
        "researchpipe_api.tavily.search",
        new=AsyncMock(return_value=_mock_tavily_search_response()),
    ):
        r = client.post(
            "/v1/search",
            headers=auth_headers,
            json={"query": "test", "max_results": 5},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["query"] == "test"
    assert len(body["results"]) == 1
    assert body["results"][0]["title"] == "Sample title"
    assert body["metadata"]["credits_charged"] == 1
    assert body["metadata"]["data_sources_used"] == ["tavily"]


def test_search_advanced_charges_2(client, auth_headers):
    with patch(
        "researchpipe_api.tavily.search",
        new=AsyncMock(return_value=_mock_tavily_search_response()),
    ):
        r = client.post(
            "/v1/search",
            headers=auth_headers,
            json={"query": "test", "search_depth": "advanced"},
        )
    assert r.status_code == 200
    assert r.json()["metadata"]["credits_charged"] == 2


def test_search_upstream_error(client, auth_headers):
    async def boom(*args, **kwargs):
        raise RuntimeError("Tavily down")

    with patch("researchpipe_api.tavily.search", new=boom):
        r = client.post("/v1/search", headers=auth_headers, json={"query": "x"})
    assert r.status_code == 502
    err = r.json()["detail"]
    assert err["code"] == "upstream_failure"
    assert "Retry" in err["hint_for_agent"]


def test_extract_happy_path(client, auth_headers):
    with patch(
        "researchpipe_api.tavily.extract",
        new=AsyncMock(return_value=_mock_tavily_extract_response()),
    ):
        r = client.post(
            "/v1/extract",
            headers=auth_headers,
            json={"url": "https://example.com/article"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["url"] == "https://example.com/article"
    assert body["title"] == "Sample Article"
    assert body["content"] == "Full article body here"


def test_extract_empty_returns_warning(client, auth_headers):
    with patch(
        "researchpipe_api.tavily.extract",
        new=AsyncMock(return_value={"results": []}),
    ):
        r = client.post(
            "/v1/extract",
            headers=auth_headers,
            json={"url": "https://blocked.example/"},
        )
    assert r.status_code == 200
    md = r.json()["metadata"]
    assert "warnings" in md
    assert md["warnings"][0]["code"] == "extract_empty"


def test_extract_research_full_pipeline(client, auth_headers):
    with patch(
        "researchpipe_api.tavily.extract",
        new=AsyncMock(return_value=_mock_tavily_extract_response()),
    ), patch(
        "researchpipe_api.routes.search.chat_json",
        return_value=(
            {
                "broker": "Sample",
                "broker_country": "CN",
                "source_type": "broker",
                "source_name": "Sample",
                "report_title": "Sample Title",
                "report_date": "2026-04-29",
                "source_url": None,
                "language": "zh",
                "core_thesis": "Sample thesis",
                "target_price": None,
                "recommendation": None,
                "key_data_points": [],
                "risks": [],
                "confidence_score": 0.9,
            },
            {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150, "model": "deepseek-v4-flash"},
        ),
    ):
        r = client.post(
            "/v1/extract/research",
            headers=auth_headers,
            json={"url": "https://example.com/article"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["extraction"]["broker"] == "Sample"
    assert body["extraction"]["confidence_score"] == 0.9
    assert body["metadata"]["partial"] is False
    assert body["metadata"]["credits_charged"] == 5


def test_extract_research_schema_partial_fallback(client, auth_headers):
    """When LLM returns invalid schema, response should still come back with partial=True."""
    with patch(
        "researchpipe_api.tavily.extract",
        new=AsyncMock(return_value=_mock_tavily_extract_response()),
    ), patch(
        "researchpipe_api.routes.search.chat_json",
        return_value=(
            {"broker": "X", "missing": "many fields"},
            {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150, "model": "test"},
        ),
    ):
        r = client.post(
            "/v1/extract/research",
            headers=auth_headers,
            json={"url": "https://example.com/article"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["metadata"]["partial"] is True
    assert "warnings" in body["metadata"]
    assert body["metadata"]["warnings"][0]["code"] == "schema_validation_partial"


def test_extract_research_empty_content_422(client, auth_headers):
    with patch(
        "researchpipe_api.tavily.extract",
        new=AsyncMock(return_value={"results": []}),
    ):
        r = client.post(
            "/v1/extract/research",
            headers=auth_headers,
            json={"url": "https://blocked.example"},
        )
    assert r.status_code == 422
    err = r.json()["detail"]
    assert err["code"] == "extract_empty"
