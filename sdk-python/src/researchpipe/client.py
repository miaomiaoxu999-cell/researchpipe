"""Sync + Async ResearchPipe clients.

Auto-retries on 429 (respects retry_after_seconds) and 502/504 (exponential backoff).
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Iterable

import httpx

from .errors import RateLimitError, ResearchPipeError, UpstreamError

DEFAULT_BASE_URL = "https://rp.zgen.xin"
DEFAULT_TIMEOUT = 60.0
USER_AGENT = "researchpipe-python/0.1.0"


def _idempotency_key() -> str:
    return str(uuid.uuid4())


def _headers(api_key: str, extra: dict | None = None) -> dict:
    h = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
        "Idempotency-Key": _idempotency_key(),
    }
    if extra:
        h.update(extra)
    return h


def _raise_for_status(resp: httpx.Response):
    if 200 <= resp.status_code < 300:
        return
    try:
        body = resp.json()
    except Exception:
        body = {"detail": resp.text[:300]}
    raise ResearchPipeError.from_response_body(body, status_code=resp.status_code)


class _BaseClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ):
        if not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries


class ResearchPipe(_BaseClient):
    """Synchronous client."""

    def __init__(self, api_key: str, **kw):
        super().__init__(api_key, **kw)
        self._client = httpx.Client(timeout=self.timeout, headers={"User-Agent": USER_AGENT})

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        self._client.close()

    def _request(self, method: str, path: str, *, json: dict | None = None, params: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        attempts = 0
        last_exc: Exception | None = None
        while attempts < self.max_retries:
            attempts += 1
            try:
                resp = self._client.request(
                    method,
                    url,
                    json=json,
                    params=params,
                    headers=_headers(self.api_key),
                )
                _raise_for_status(resp)
                return resp.json()
            except RateLimitError as e:
                if attempts >= self.max_retries:
                    raise
                wait = e.retry_after_seconds or (2 ** attempts)
                time.sleep(min(wait, 30))
                last_exc = e
            except UpstreamError as e:
                if attempts >= self.max_retries:
                    raise
                time.sleep(2 ** attempts)
                last_exc = e
        if last_exc:
            raise last_exc
        raise RuntimeError("unreachable")

    # ─── Search ───────────────────────────────────────────────────────────

    def search(self, query: str, **kw) -> dict:
        body = {"query": query, **kw}
        return self._request("POST", "/v1/search", json=body)

    def extract(self, url: str, **kw) -> dict:
        body = {"url": url, **kw}
        return self._request("POST", "/v1/extract", json=body)

    def extract_research(self, url: str, **kw) -> dict:
        body = {"url": url, **kw}
        return self._request("POST", "/v1/extract/research", json=body)

    # ─── Research (async product line, but sync API from SDK side) ────────

    def research_sector(self, input: str, **kw) -> dict:
        body = {"input": input, **kw}
        job = self._request("POST", "/v1/research/sector", json=body)
        return self._poll_job(job["request_id"])

    def research_company(self, input: str, **kw) -> dict:
        body = {"input": input, **kw}
        job = self._request("POST", "/v1/research/company", json=body)
        return self._poll_job(job["request_id"])

    def research_valuation(self, input: str, **kw) -> dict:
        body = {"input": input, **kw}
        job = self._request("POST", "/v1/research/valuation", json=body)
        return self._poll_job(job["request_id"])

    def get_job(self, job_id: str) -> dict:
        return self._request("GET", f"/v1/jobs/{job_id}")

    def _poll_job(self, request_id: str, *, interval_s: int = 5, max_polls: int = 60) -> dict:
        for _ in range(max_polls):
            job = self.get_job(request_id)
            status = job.get("status")
            if status in {"completed", "failed"}:
                return job
            time.sleep(interval_s)
        raise UpstreamError(
            "research job timed out",
            code="upstream_timeout",
            hint_for_agent=f"Job {request_id} did not complete in {interval_s * max_polls}s. Try again or contact support.",
        )

    # ─── Data — Companies (6) ─────────────────────────────────────────────

    def companies_search(self, **kw) -> dict:
        return self._request("POST", "/v1/companies/search", json=kw)

    def companies_get(self, cid: str, **kw) -> dict:
        return self._request("GET", f"/v1/companies/{cid}", params=kw)

    def companies_deals(self, cid: str) -> dict:
        return self._request("GET", f"/v1/companies/{cid}/deals")

    def companies_peers(self, cid: str, **kw) -> dict:
        return self._request("POST", f"/v1/companies/{cid}/peers", json=kw)

    def companies_news(self, cid: str, **kw) -> dict:
        return self._request("GET", f"/v1/companies/{cid}/news", params=kw)

    def companies_founders(self, cid: str, deep: bool = False) -> dict:
        return self._request("GET", f"/v1/companies/{cid}/founders", params={"deep": deep})

    # ─── Data — Investors (5) ─────────────────────────────────────────────

    def investors_search(self, **kw) -> dict:
        return self._request("POST", "/v1/investors/search", json=kw)

    def investors_get(self, iid: str) -> dict:
        return self._request("GET", f"/v1/investors/{iid}")

    def investors_portfolio(self, iid: str, **kw) -> dict:
        return self._request("GET", f"/v1/investors/{iid}/portfolio", params=kw)

    def investors_preferences(self, iid: str) -> dict:
        return self._request("GET", f"/v1/investors/{iid}/preferences")

    def investors_exits(self, iid: str) -> dict:
        return self._request("GET", f"/v1/investors/{iid}/exits")

    # ─── Data — Deals (5) ─────────────────────────────────────────────────

    def deals_search(self, **kw) -> dict:
        return self._request("POST", "/v1/deals/search", json=kw)

    def deals_get(self, did: str) -> dict:
        return self._request("GET", f"/v1/deals/{did}")

    def deals_timeline(self, **kw) -> dict:
        return self._request("POST", "/v1/deals/timeline", json=kw)

    def deals_overseas(self, **kw) -> dict:
        return self._request("POST", "/v1/deals/overseas", json=kw)

    def deals_co_investors(self, did: str) -> dict:
        return self._request("GET", f"/v1/deals/{did}/co_investors")

    # ─── Account (3) ──────────────────────────────────────────────────────

    def me(self) -> dict:
        return self._request("GET", "/v1/me")

    def usage(self, **kw) -> dict:
        return self._request("GET", "/v1/usage", params=kw)

    def billing(self) -> dict:
        return self._request("GET", "/v1/billing")

    # ─── Watch (2) ────────────────────────────────────────────────────────

    def watch_create(self, **kw) -> dict:
        return self._request("POST", "/v1/watch/create", json=kw)

    def watch_digest(self, wid: str) -> dict:
        return self._request("GET", f"/v1/watch/{wid}/digest")

    # ─── Search line — extras (3) ────────────────────────────────────────

    def extract_filing(self, url: str, schema: str = "prospectus_v1", **kw) -> dict:
        return self._request("POST", "/v1/extract/filing", json={"url": url, "schema": schema, **kw})

    def extract_batch(self, urls: list[str], **kw) -> dict:
        return self._request("POST", "/v1/extract/batch", json={"urls": urls, **kw})

    # ─── Filings (5) ─────────────────────────────────────────────────────

    def filings_search(self, **kw) -> dict:
        return self._request("POST", "/v1/filings/search", json=kw)

    def filings_get(self, fid: str) -> dict:
        return self._request("GET", f"/v1/filings/{fid}")

    def filings_extract(self, fid: str, *, url: str | None = None, schema: str = "prospectus_v1") -> dict:
        body = {"schema": schema}
        if url:
            body["url"] = url
        return self._request("POST", f"/v1/filings/{fid}/extract", json=body)

    def filings_risks(self, fid: str, *, url: str | None = None) -> dict:
        body = {"url": url} if url else {}
        return self._request("POST", f"/v1/filings/{fid}/risks", json=body)

    def filings_financials(self, fid: str, *, url: str | None = None) -> dict:
        body = {"url": url} if url else {}
        return self._request("POST", f"/v1/filings/{fid}/financials", json=body)

    # ─── News & Events (3) ───────────────────────────────────────────────

    def news_search(self, query: str, **kw) -> dict:
        return self._request("POST", "/v1/news/search", json={"query": query, **kw})

    def news_recent(self, **kw) -> dict:
        return self._request("POST", "/v1/news/recent", json=kw)

    def events_timeline(self, **kw) -> dict:
        return self._request("POST", "/v1/events/timeline", json=kw)

    # ─── Tasks (1) ───────────────────────────────────────────────────────

    def screen(self, industry: str, **kw) -> dict:
        return self._request("POST", "/v1/screen", json={"industry": industry, **kw})

    # ─── Data — Industries (9) ───────────────────────────────────────────

    def industries_search(self, query: str, **kw) -> dict:
        return self._request("POST", "/v1/industries/search", json={"query": query, **kw})

    def industries_deals(self, ind: str) -> dict:
        return self._request("GET", f"/v1/industries/{ind}/deals")

    def industries_companies(self, ind: str) -> dict:
        return self._request("GET", f"/v1/industries/{ind}/companies")

    def industries_chain(self, ind: str) -> dict:
        return self._request("GET", f"/v1/industries/{ind}/chain")

    def industries_policies(self, ind: str) -> dict:
        return self._request("GET", f"/v1/industries/{ind}/policies")

    def industries_tech_roadmap(self, ind: str) -> dict:
        return self._request("GET", f"/v1/industries/{ind}/tech_roadmap")

    def industries_key_technologies(self, ind: str) -> dict:
        return self._request("GET", f"/v1/industries/{ind}/key_technologies")

    def industries_maturity(self, ind: str, **kw) -> dict:
        return self._request("POST", f"/v1/industries/{ind}/maturity", json=kw)

    def technologies_compare(self, tech_a: str, tech_b: str, **kw) -> dict:
        return self._request("POST", "/v1/technologies/compare", json={"tech_a": tech_a, "tech_b": tech_b, **kw})

    # ─── Data — Valuations (4) ───────────────────────────────────────────

    def valuations_search(self, **kw) -> dict:
        return self._request("POST", "/v1/valuations/search", json=kw)

    def valuations_multiples(self, industry: str, **kw) -> dict:
        return self._request("POST", "/v1/valuations/multiples", json={"industry": industry, **kw})

    def valuations_compare(self, industry: str, **kw) -> dict:
        return self._request("POST", "/v1/valuations/compare", json={"industry": industry, **kw})

    def valuations_distribution(self, industry: str, **kw) -> dict:
        return self._request("POST", "/v1/valuations/distribution", json={"industry": industry, **kw})


class AsyncResearchPipe(_BaseClient):
    """Async client (httpx.AsyncClient)."""

    def __init__(self, api_key: str, **kw):
        super().__init__(api_key, **kw)
        self._client = httpx.AsyncClient(timeout=self.timeout, headers={"User-Agent": USER_AGENT})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def close(self):
        await self._client.aclose()

    async def _request(self, method: str, path: str, *, json: dict | None = None, params: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        import asyncio

        attempts = 0
        last_exc: Exception | None = None
        while attempts < self.max_retries:
            attempts += 1
            try:
                resp = await self._client.request(
                    method,
                    url,
                    json=json,
                    params=params,
                    headers=_headers(self.api_key),
                )
                _raise_for_status(resp)
                return resp.json()
            except RateLimitError as e:
                if attempts >= self.max_retries:
                    raise
                wait = e.retry_after_seconds or (2 ** attempts)
                await asyncio.sleep(min(wait, 30))
                last_exc = e
            except UpstreamError as e:
                if attempts >= self.max_retries:
                    raise
                await asyncio.sleep(2 ** attempts)
                last_exc = e
        if last_exc:
            raise last_exc
        raise RuntimeError("unreachable")

    async def search(self, query: str, **kw) -> dict:
        return await self._request("POST", "/v1/search", json={"query": query, **kw})

    async def extract(self, url: str, **kw) -> dict:
        return await self._request("POST", "/v1/extract", json={"url": url, **kw})

    async def extract_research(self, url: str, **kw) -> dict:
        return await self._request("POST", "/v1/extract/research", json={"url": url, **kw})

    async def companies_get(self, cid: str, **kw) -> dict:
        return await self._request("GET", f"/v1/companies/{cid}", params=kw)

    async def me(self) -> dict:
        return await self._request("GET", "/v1/me")
