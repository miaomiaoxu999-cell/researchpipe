"""Output schema for extract/research (PRD 6.6 / 6.13 / memory v3)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SourceType = Literal[
    "broker",
    "consulting",
    "association",
    "corporate_research",
    "vc",
    "overseas_ib",
    "media",
]


class TargetPrice(BaseModel):
    value: float | None = None
    currency: Literal["CNY", "USD", "HKD", "EUR", "JPY"] | None = None


class KeyDataPoint(BaseModel):
    metric: str
    # 接受 str | number（部分 LLM 如 Kimi 会直接输出数字）
    value: str | int | float
    source: str
    # 研报里 year 自然是 "2025" / "2025E" / "2023-2025" / "Q3 2025" 等多形态
    # 不强约束 int，agent 拿到后自己解析
    year: str | int | None = None


class ExtractResearchOutput(BaseModel):
    """11-field schema W1 must hit."""

    broker: str = Field(description="券商 / 机构 / 出版方名称")
    broker_country: str = Field(description="ISO 国家码：CN / US / HK / SG / GB / JP / EU")
    source_type: SourceType
    source_name: str
    report_title: str
    report_date: str = Field(description="YYYY-MM-DD")
    source_url: str | None = None
    language: Literal["zh", "en"] = "zh"
    core_thesis: str = Field(max_length=400, description="≤ 200 中文字 LLM 综合（柔性约束）")
    target_price: TargetPrice | None = None
    recommendation: str | None = Field(
        default=None, description="买入 / 增持 / 中性 / 减持 / 卖出 / null"
    )
    key_data_points: list[KeyDataPoint] = Field(min_length=0, default_factory=list)
    risks: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
