"""Pydantic schemas for ResearchPipe v1 API.

Aligned to PRD ch6.x + EDD ch7.x. Field names match what frontend expects.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────
# Search
# ─────────────────────────────────────────────────────────────────────────


class SearchRequest(BaseModel):
    query: str
    type: Literal["web", "news", "research", "policy", "filing"] = "research"
    search_depth: Literal["basic", "advanced"] = "basic"
    include_answer: bool | Literal["basic", "advanced"] = False
    include_raw_content: bool = False
    max_results: int = Field(default=20, ge=1, le=100)
    regions: list[str] | None = None
    languages: list[str] | None = None
    time_range: str | None = "30d"
    source_types: list[str] | None = None
    # 套壳 / 组合策略：true → Tavily + Bocha + Serper 3 路并发去重排序；false → 单 Tavily（默认快）
    multi_source: bool = False


class SearchResultItem(BaseModel):
    title: str | None = None
    url: str | None = None
    snippet: str | None = None
    content: str | None = None
    score: float | None = None
    published_at: str | None = None
    source_type: str | None = None
    source_name: str | None = None
    # multi_source mode: which provider(s) returned this URL + composite rank score
    providers: list[str] | str | None = None
    rank_score: float | None = None


class SearchResponse(BaseModel):
    query: str | None = None
    answer: str | None = None
    results: list[SearchResultItem] = []
    metadata: dict[str, Any] = {}


# ─────────────────────────────────────────────────────────────────────────
# Extract
# ─────────────────────────────────────────────────────────────────────────


class ExtractRequest(BaseModel):
    url: str
    include_images: bool = False
    extract_depth: Literal["basic", "advanced"] = "advanced"


class ExtractResponse(BaseModel):
    url: str
    title: str | None = None
    content: str | None = None
    images: list[str] | None = None
    metadata: dict[str, Any] = {}


# ─────────────────────────────────────────────────────────────────────────
# Extract / Research (11 fields)
# ─────────────────────────────────────────────────────────────────────────


class TargetPrice(BaseModel):
    value: float | None = None
    currency: Literal["CNY", "USD", "HKD", "EUR", "JPY"] | None = None


class KeyDataPoint(BaseModel):
    metric: str
    # Accept str | number — LLMs (Kimi etc.) often output `value: 340` or `45.51` instead of "340"
    # Pydantic will coerce to str if needed; keep flexible.
    value: str | int | float
    source: str
    year: str | int | None = None


class ExtractResearchRequest(BaseModel):
    url: str
    language: Literal["zh", "en"] = "zh"
    include_raw_content: bool = False
    model: str | None = None  # auto / mini / pro / specific name


class ExtractResearchOutput(BaseModel):
    broker: str
    broker_country: str
    source_type: str
    source_name: str
    report_title: str
    report_date: str
    source_url: str | None = None
    language: Literal["zh", "en"] = "zh"
    core_thesis: str
    target_price: TargetPrice | None = None
    recommendation: str | None = None
    key_data_points: list[KeyDataPoint] = []
    risks: list[str] = []
    confidence_score: float = Field(ge=0.0, le=1.0)


class ExtractResearchResponse(BaseModel):
    # When schema_validation passes, this is a strict ExtractResearchOutput.
    # On partial success, we still return the LLM dict so agent can salvage what they can.
    extraction: dict[str, Any] | None = None
    metadata: dict[str, Any] = {}
    raw_content: str | None = None


# ─────────────────────────────────────────────────────────────────────────
# Research async
# ─────────────────────────────────────────────────────────────────────────


class ResearchSectorRequest(BaseModel):
    input: str
    time_range: str = "24m"
    regions: list[str] | None = None
    model: Literal["mini", "pro", "auto"] = "auto"
    output_schema: dict[str, Any] | None = None
    citation_format: Literal["numbered", "apa", "chicago"] = "numbered"
    stream: bool = False
    depth: Literal["summary", "standard", "full"] = "standard"


class ResearchCompanyRequest(BaseModel):
    input: str
    focus: list[str] = Field(default_factory=lambda: ["business", "financials", "risks"])
    model: Literal["mini", "pro", "auto"] = "auto"
    output_schema: dict[str, Any] | None = None
    citation_format: Literal["numbered", "apa", "chicago"] = "numbered"
    stream: bool = False
    depth: Literal["summary", "standard", "full"] = "standard"


class ResearchValuationRequest(BaseModel):
    input: str
    model: Literal["mini", "pro", "auto"] = "auto"
    regions: list[str] | None = None


class JobAccepted(BaseModel):
    request_id: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"


class JobResult(BaseModel):
    request_id: str
    status: Literal["pending", "running", "completed", "failed"]
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    metadata: dict[str, Any] = {}


# ─────────────────────────────────────────────────────────────────────────
# Account
# ─────────────────────────────────────────────────────────────────────────


class MeResponse(BaseModel):
    api_key_prefix: str
    plan: str
    credits_used_this_month: int
    credits_limit: int
    plan_resets_on: str


class UsageItem(BaseModel):
    date: str
    endpoint: str
    calls: int
    credits: float


class UsageResponse(BaseModel):
    items: list[UsageItem]
    metadata: dict[str, Any] = {}


class BillingResponse(BaseModel):
    month: str
    plan: str
    plan_fee_cny: int
    overage_credits: int
    overage_fee_cny: float
    total_due_cny: float


# ─────────────────────────────────────────────────────────────────────────
# Generic envelope for stub endpoints
# ─────────────────────────────────────────────────────────────────────────


class GenericEnvelope(BaseModel):
    request_id: str
    status: str = "ok"
    result: dict[str, Any] | None = None
    metadata: dict[str, Any] = {}
