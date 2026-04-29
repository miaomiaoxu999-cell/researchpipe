"""Tests for FIX2: filings_extract URL type detection."""
from __future__ import annotations


def test_detect_prospectus():
    from researchpipe_api.web_combined import _detect_filing_type

    text = "招股说明书\n\n首次公开发行股票并在创业板上市\n\n保荐人：中信证券\n\n本公司发行人声明……"
    assert _detect_filing_type(text) == "prospectus_v1"


def test_detect_inquiry():
    from researchpipe_api.web_combined import _detect_filing_type

    text = "审核问询函\n\n问询函编号：xxx\n\n关于本次首发上市的回复\n\n问询回复"
    assert _detect_filing_type(text) == "inquiry_v1"


def test_detect_audit():
    from researchpipe_api.web_combined import _detect_filing_type

    text = "审计报告\n\n会计师事务所\n\n审计意见……" + "x" * 100
    assert _detect_filing_type(text) == "audit_v1"


def test_detect_research_report_returns_none():
    """A typical research/analyst report should NOT match any filing schema."""
    from researchpipe_api.web_combined import _detect_filing_type

    text = (
        "证券研究报告\n\n2026 年度半导体设备行业策略：\n\n"
        "AI 驱动先进逻辑与存储扩产，全球半导体设备市场持续创新高。"
    )
    # Research reports lack listing-filing keywords
    assert _detect_filing_type(text) is None
