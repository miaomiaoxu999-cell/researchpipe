"""Unit tests for corpus filename parser (no DB dependency)."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

# corpus/ is at backend/corpus/ — add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_broker_dated_pattern():
    from corpus.manifest_builder import parse_filename

    p = parse_filename("11月外汇市场分析报告：人民币汇率升值加快-260104-中银证券-11页.pdf")
    assert p is not None
    assert p["filename_pattern"] == "broker_dated"
    assert p["title"] == "11月外汇市场分析报告：人民币汇率升值加快"
    assert p["broker"] == "中银证券"
    assert p["report_date"] == date(2026, 1, 4)
    assert p["pages"] == 11


def test_broker_dated_yymmdd_25year():
    from corpus.manifest_builder import parse_filename

    p = parse_filename("12月PMI数据点评：景气重返扩张区间-251231-麦高证券-10页.pdf")
    assert p is not None
    assert p["report_date"] == date(2025, 12, 31)


def test_titled_only_pattern():
    from corpus.manifest_builder import parse_filename

    p = parse_filename("2024中国水文年报-140页.pdf")
    assert p is not None
    assert p["filename_pattern"] == "titled_only"
    assert p["title"] == "2024中国水文年报"
    assert p["broker"] is None
    assert p["report_date"] is None
    assert p["pages"] == 140


def test_broker_first_pattern():
    from corpus.manifest_builder import parse_filename

    p = parse_filename("华源证券-资本补充工具月报-251229.pdf")
    assert p is not None
    assert p["filename_pattern"] == "broker_first_cn"
    assert p["broker"] == "华源证券"


def test_intl_dash_pattern():
    from corpus.manifest_builder import parse_filename

    p = parse_filename("Morgan Stanley-China Equity Strategy A-Share-120781929.pdf")
    assert p is not None
    assert p["filename_pattern"] == "intl_dash"
    assert p["broker"].startswith("Morgan Stanley")


def test_intl_underscore_pattern():
    from corpus.manifest_builder import parse_filename

    p = parse_filename("Barclays_China_Balanced_risks.pdf")
    assert p is not None
    assert p["filename_pattern"] == "intl_underscore"
    assert p["broker"] == "Barclays"


def test_full_paren_pages():
    from corpus.manifest_builder import parse_filename

    p = parse_filename("制造业企业智慧供应链：提升韧性和安全（61页）.pdf")
    assert p is not None
    assert p["filename_pattern"] == "full_paren_pages"
    assert p["pages"] == 61


def test_p8_title_fallback():
    """Final fallback — any .pdf gets at least a title."""
    from corpus.manifest_builder import parse_filename

    p = parse_filename("具身智能行业应用方案解决方案.pdf")
    assert p is not None
    assert p["filename_pattern"] == "title_fallback"
    assert "具身智能行业应用方案解决方案" in p["title"]


def test_non_pdf_returns_none():
    from corpus.manifest_builder import parse_filename

    assert parse_filename("random.txt") is None
    assert parse_filename("noextension") is None


def test_parse_library_strips_count():
    from corpus.manifest_builder import parse_library

    assert parse_library("01_重点报告-331份") == "01_重点报告"
    assert parse_library("02_国内券商报告-708份") == "02_国内券商报告"


def test_industry_tag_matching():
    from corpus.manifest_builder import match_industry_tags

    assert "半导体" in match_industry_tags("2026Q1半导体行业策略：AI驱动设备国产化")
    assert "新能源汽车" in match_industry_tags("动力电池产业链深度报告")
    assert "AI 应用" in match_industry_tags("AI 智能座舱行业报告")
    assert match_industry_tags("非银金融行业财富管理系列") == []


def test_yymmdd_parser():
    from corpus.manifest_builder import parse_yymmdd

    assert parse_yymmdd("260103") == date(2026, 1, 3)
    assert parse_yymmdd("251231") == date(2025, 12, 31)
    assert parse_yymmdd("invalid") is None
    assert parse_yymmdd("") is None
