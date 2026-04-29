"""Tests for industry alias expansion."""
from __future__ import annotations


def test_aliases_known_keys():
    from researchpipe_api import aliases

    keys = aliases.matched_aliases()
    assert "具身智能" in keys
    assert "新能源汽车" in keys
    assert "创新药" in keys
    assert "半导体" in keys


def test_expand_known():
    from researchpipe_api import aliases

    e = aliases.expand("具身智能")
    assert "人工智能" in e["industries"]
    assert any("人形" in s for s in e["sub_industries"])
    assert any("具身" in p for p in e["name_patterns"])


def test_expand_unknown_falls_back():
    from researchpipe_api import aliases

    e = aliases.expand("某种新兴行业 XYZ")
    # Identity fallback
    assert e["industries"] == ["某种新兴行业 XYZ"]
    assert e["sub_industries"] == ["某种新兴行业 XYZ"]
    assert e["name_patterns"] == ["某种新兴行业 XYZ"]


def test_build_where_clause_known_alias():
    from researchpipe_api import aliases

    sql, params = aliases.build_industry_where_clause("具身智能", params_offset=0)
    # Should generate IN clause for industries + ILIKE for sub_industries + ILIKE for names
    assert "e.industry IN" in sql
    assert "e.sub_industry ILIKE" in sql
    assert "e.company_name ILIKE" in sql
    # Params should include both raw industry names and %-wrapped patterns
    assert "人工智能" in params
    assert any("%" in p and "具身" in p for p in params)


def test_build_where_clause_unknown_falls_back():
    from researchpipe_api import aliases

    sql, params = aliases.build_industry_where_clause("罕见行业", params_offset=0)
    # Should still build a valid WHERE
    assert "OR" in sql or "IN" in sql
    assert any("罕见行业" in p for p in params)


def test_build_where_clause_offset_works():
    """When params_offset > 0, placeholders should start at $offset+1."""
    from researchpipe_api import aliases

    sql, params = aliases.build_industry_where_clause("半导体", params_offset=5)
    # First placeholder should be $6
    assert "$6" in sql
