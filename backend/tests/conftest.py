"""Pytest fixtures."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure src/ is on sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Use a test API key consistently
os.environ.setdefault("RP_DEV_API_KEY", "rp-test-key")
os.environ.setdefault("TAVILY_API_KEY", "tvly-test")
os.environ.setdefault("BAILIAN_API_KEY", "sk-test")

import pytest
from fastapi.testclient import TestClient

from researchpipe_api.main import app


@pytest.fixture(autouse=True)
def _reset_middleware_state():
    """Each test gets a fresh rate-limit bucket, Idempotency cache, and SQLite tables."""
    from researchpipe_api import middleware, storage

    middleware.ratelimit._tokens.clear()
    middleware.ratelimit._last.clear()
    middleware.idempotency._store.clear()
    # Reset SQLite tables that affect cross-test state
    try:
        with storage._conn() as c:
            c.execute("DELETE FROM idempotency")
            c.execute("DELETE FROM jobs")
            c.execute("DELETE FROM watchlists")
            c.execute("DELETE FROM usage_log")
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _mock_external_services(monkeypatch):
    """Skip real Tavily / V4 / Bocha / Serper calls in unit tests.

    Integration tests (test_integration.py) bypass this by importing real modules
    after their own load_dotenv(override=True).
    """
    from unittest.mock import AsyncMock, MagicMock

    from researchpipe_api import multi_search, tavily, web_combined

    # Tavily search/extract → return tiny mocks
    monkeypatch.setattr(
        tavily,
        "search",
        AsyncMock(
            return_value={
                "query": "test",
                "answer": None,
                "results": [{"title": "Mock", "url": "https://example.com", "content": "mock content", "score": 0.9}],
            }
        ),
    )
    monkeypatch.setattr(
        tavily,
        "extract",
        AsyncMock(
            return_value={
                "results": [{"url": "https://example.com", "title": "Mock", "raw_content": "mock content"}],
            }
        ),
    )

    # web_combined helpers
    monkeypatch.setattr(
        web_combined,
        "filings_extract",
        AsyncMock(
            return_value={
                "url": "mock://url",
                "schema": "prospectus_v1",
                "fields": {
                    "company_basic": {"name": "Mock"},
                    "major_risks": [{"category": "tech", "description": "Mock risk"}],
                    "financials_5y_summary": {"revenue_cny_m": [1, 2, 3, 4, 5]},
                },
                "metadata": {"data_sources_used": ["tavily", "deepseek-v4"], "credits_charged": 3, "request_id": "req_mock"},
            }
        ),
    )
    monkeypatch.setattr(
        web_combined,
        "filings_search",
        AsyncMock(
            return_value={
                "total": 1,
                "results": [{"id": "fil_mock", "filing_type": "prospectus", "title": "Mock", "publish_date": "2026-01-01", "source_url": "https://example.com", "score": 0.9}],
                "metadata": {"data_sources_used": ["tavily"], "credits_charged": 0.5, "request_id": "req_mock"},
            }
        ),
    )
    monkeypatch.setattr(
        web_combined,
        "synthesize_with_search",
        AsyncMock(
            return_value={
                "result": "mock synthesis",
                "citations": [{"url": "https://example.com", "title": "Mock"}],
                "metadata": {"data_sources_used": ["tavily", "deepseek-v4"], "request_id": "req_mock", "credits_charged": 1},
            }
        ),
    )
    monkeypatch.setattr(
        multi_search,
        "combined_search",
        AsyncMock(
            return_value={
                "query": "test",
                "answer": None,
                "results": [{"title": "Mock", "url": "https://example.com", "providers": ["tavily"], "rank_score": 1.0}],
                "metadata": {
                    "request_id": "req_mock",
                    "data_sources_used": ["tavily"],
                    "providers_attempted": ["tavily", "bocha", "serper"],
                    "total_results": 1,
                    "raw_results_before_dedup": 1,
                    "wall_time_ms": 1.0,
                    "warnings": None,
                    "partial": False,
                    "credits_charged": 1,
                },
            }
        ),
    )


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict:
    return {"Authorization": "Bearer rp-test-key"}
