"""End-to-end integration tests — call real Tavily / V4 / qmp_data postgres.

Skip by default; enable with `RUN_INTEGRATION=1 uv run pytest tests/test_integration.py`.
Each test costs ~¥0.05 in API + LLM calls.
"""
from __future__ import annotations

import os

import pytest

if os.environ.get("RUN_INTEGRATION") != "1":
    pytest.skip("Integration tests skipped (set RUN_INTEGRATION=1 to run)", allow_module_level=True)

# Conftest set fake keys; force-reload real keys from .env (override mode)
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)

# Reload settings module so module-level constants pick up the real keys
import importlib
from researchpipe_api import settings as _settings  # noqa: E402

importlib.reload(_settings)
from researchpipe_api import auth as _auth  # noqa: E402
from researchpipe_api import tavily as _tavily  # noqa: E402
from researchpipe_api import llm as _llm  # noqa: E402

importlib.reload(_auth)
importlib.reload(_tavily)
importlib.reload(_llm)


@pytest.fixture(scope="module")
def real_client():
    from fastapi.testclient import TestClient

    # Reload main to pick up reloaded settings/tavily
    import importlib

    from researchpipe_api import main as _main

    importlib.reload(_main)
    yield TestClient(_main.app)


@pytest.fixture
def auth_headers() -> dict:
    """Override conftest's auth_headers to use the real dev key from .env."""
    return {"Authorization": f"Bearer {_settings.RP_DEV_API_KEY}"}


def test_real_search_via_tavily(real_client, auth_headers):
    """Real Tavily Search — verifies network + key + shape."""
    r = real_client.post(
        "/v1/search",
        headers=auth_headers,
        json={"query": "China innovative drug 2026", "max_results": 3, "search_depth": "basic"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert len(data["results"]) >= 1
    assert data["metadata"]["data_sources_used"] == ["tavily"]
    assert data["metadata"]["credits_charged"] == 1


def test_real_extract_research_via_tavily_v4(real_client, auth_headers):
    """End-to-end: Tavily Extract + DeepSeek V4-Flash think → 11-field schema."""
    r = real_client.post(
        "/v1/extract/research",
        headers=auth_headers,
        json={
            "url": "https://www.goldmansachs.com/insights/articles/china-is-increasing-its-share-of-global-drug-development",
        },
    )
    assert r.status_code == 200
    data = r.json()
    extraction = data.get("extraction") or {}
    assert extraction.get("broker"), "broker field missing"
    assert extraction.get("broker_country") in {"US", "CN", "HK", "SG", "GB", "EU"}
    assert extraction.get("source_type") in {"broker", "consulting", "association", "corporate_research", "vc", "overseas_ib", "media"}
    assert extraction.get("language") in {"zh", "en"}
    assert "core_thesis" in extraction
    assert isinstance(extraction.get("confidence_score"), (int, float))
    assert data["metadata"]["partial"] is False or "warnings" in data["metadata"]


def test_real_companies_search_via_qmp(real_client, auth_headers):
    """Real qmp_data PostgreSQL query."""
    r = real_client.post(
        "/v1/companies/search",
        headers=auth_headers,
        json={"query": "智元", "limit": 5},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert data["metadata"]["data_sources_used"] == ["qmp_data"]
    # 智元机器人 should be in the result
    names = [r["company_name"] for r in data["results"]]
    assert any("智元" in n for n in names)


def test_real_deals_search_via_qmp(real_client, auth_headers):
    """Real qmp_data deals query."""
    r = real_client.post(
        "/v1/deals/search",
        headers=auth_headers,
        json={"industry": "人工智能", "time_range": "30d", "limit": 3},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 10  # AI is a hot sector with many deals
    assert data["metadata"]["data_sources_used"] == ["qmp_data"]


@pytest.mark.skipif(
    os.environ.get("RP_BACKEND_URL") is None,
    reason="needs RP_BACKEND_URL set to a running backend (asyncio.create_task in TestClient drops bg jobs)",
)
def test_real_research_sector_orchestrator(auth_headers):
    """Submit + poll until completed — full orchestrator (Tavily + qmp + V4 synthesis).

    Hits a running backend (default localhost:3725) because TestClient doesn't
    properly run the asyncio bg task that drives the orchestrator.
    """
    import time

    import httpx

    base = os.environ["RP_BACKEND_URL"].rstrip("/")
    cli = httpx.Client(timeout=120.0, headers=auth_headers)

    submit = cli.post(
        f"{base}/v1/research/sector",
        json={"input": "新能源汽车", "time_range": "12m"},
    )
    assert submit.status_code == 200
    rid = submit.json()["request_id"]

    # Poll up to 180s — orchestrator does 5 Tavily Extracts + V4 抽 + V4 synthesis
    for _ in range(60):
        time.sleep(3)
        res = cli.get(f"{base}/v1/jobs/{rid}")
        assert res.status_code == 200
        body = res.json()
        if body["status"] == "completed":
            result = body.get("result") or {}
            assert "executive_summary" in result
            assert "research_views" in result
            return
        if body["status"] == "failed":
            pytest.fail(f"sector research failed: {body}")
    pytest.fail("sector research did not complete in 180s")
