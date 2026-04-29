"""Industry alias resolver — qmp_data 的 industry tag 粒度问题：

很多客户语义"具身智能" / "AI 大模型" / "新能源汽车"在 qmp 不是顶层 industry，
而是 sub_industry / company_description 关键词。这个模块负责把客户输入扩展成 SQL 查询条件。

Schema:
  ALIASES = {
    "具身智能": {
      "industries": ["人工智能"],            # qmp.events.industry 完全匹配
      "sub_industries": ["人形机器人"],       # qmp.events.sub_industry 关键词
      "name_patterns": ["具身", "人形机器人"],  # qmp.events.company_name 模糊
    },
    ...
  }
"""
from __future__ import annotations

from typing import TypedDict


class _Alias(TypedDict):
    industries: list[str]
    sub_industries: list[str]
    name_patterns: list[str]


# Curated set — covers W1 验证赛道 + 高频客户场景
ALIASES: dict[str, _Alias] = {
    "具身智能": {
        "industries": ["人工智能", "硬件", "先进制造"],
        "sub_industries": ["人形机器人", "机器人"],
        "name_patterns": ["具身", "人形机器人", "机器人"],
    },
    "AI 大模型": {
        "industries": ["人工智能"],
        "sub_industries": ["大模型", "AIGC", "生成式 AI"],
        "name_patterns": ["大模型", "GPT", "通用智能"],
    },
    "AI 应用": {
        "industries": ["人工智能", "企业服务"],
        "sub_industries": ["AI 应用", "AIGC"],
        "name_patterns": ["AI ", "智能"],
    },
    "新能源汽车": {
        "industries": ["汽车交通", "能源电力"],
        "sub_industries": ["新能源汽车", "电动汽车"],
        "name_patterns": ["新能源", "电动汽车", "动力电池"],
    },
    "动力电池": {
        "industries": ["能源电力", "先进制造"],
        "sub_industries": ["动力电池", "锂电"],
        "name_patterns": ["电池", "锂电"],
    },
    "储能": {
        "industries": ["能源电力"],
        "sub_industries": ["储能"],
        "name_patterns": ["储能"],
    },
    "半导体": {
        "industries": ["生产制造", "硬件", "先进制造"],
        "sub_industries": ["半导体", "集成电路", "芯片"],
        "name_patterns": ["半导体", "芯片", "晶圆"],
    },
    "半导体设备": {
        "industries": ["生产制造"],
        "sub_industries": ["半导体设备"],
        "name_patterns": ["设备", "刻蚀", "光刻"],
    },
    "创新药": {
        "industries": ["医疗健康"],
        "sub_industries": ["创新药", "生物医药"],
        "name_patterns": ["药", "biotech", "生物"],
    },
    "创新药出海": {
        "industries": ["医疗健康"],
        "sub_industries": ["创新药"],
        "name_patterns": ["药", "biotech", "license"],
    },
    "AI 制药": {
        "industries": ["医疗健康", "人工智能"],
        "sub_industries": ["AI 制药"],
        "name_patterns": ["AI 药", "biotech", "新药"],
    },
    "机器人": {
        "industries": ["硬件", "先进制造"],
        "sub_industries": ["机器人", "人形机器人"],
        "name_patterns": ["机器人"],
    },
    "自动驾驶": {
        "industries": ["汽车交通", "人工智能"],
        "sub_industries": ["自动驾驶", "智能驾驶"],
        "name_patterns": ["自动驾驶", "智驾"],
    },
    "SaaS": {
        "industries": ["企业服务"],
        "sub_industries": ["SaaS"],
        "name_patterns": ["SaaS", "云"],
    },
}


def expand(industry: str) -> _Alias:
    """Look up alias. If not found, fall back to identity."""
    if industry in ALIASES:
        return ALIASES[industry]
    return {"industries": [industry], "sub_industries": [industry], "name_patterns": [industry]}


def build_industry_where_clause(query: str, params_offset: int = 0) -> tuple[str, list[str]]:
    """Build SQL WHERE fragment + parameter list for an aliased industry query.

    Returns:
      (sql_fragment, params)
      sql_fragment uses $1, $2, ... starting at params_offset+1
      params list of LIKE values

    Example:
      build_industry_where_clause("具身智能", 0) →
        ("(industry IN ($1, $2, $3) OR sub_industry ILIKE $4 OR sub_industry ILIKE $5
            OR company_name ILIKE $6 OR company_name ILIKE $7 OR company_name ILIKE $8)",
         ["人工智能", "硬件", "先进制造", "%人形机器人%", "%机器人%",
          "%具身%", "%人形机器人%", "%机器人%"])
    """
    alias = expand(query)
    parts: list[str] = []
    params: list[str] = []
    n = params_offset

    # industry IN (exact match)
    if alias["industries"]:
        placeholders = []
        for ind in alias["industries"]:
            n += 1
            placeholders.append(f"${n}")
            params.append(ind)
        parts.append(f"e.industry IN ({', '.join(placeholders)})")

    # sub_industry ILIKE
    for sub in alias["sub_industries"]:
        n += 1
        parts.append(f"e.sub_industry ILIKE ${n}")
        params.append(f"%{sub}%")

    # company_name ILIKE
    for kw in alias["name_patterns"]:
        n += 1
        parts.append(f"e.company_name ILIKE ${n}")
        params.append(f"%{kw}%")

    where_sql = "(" + " OR ".join(parts) + ")"
    return where_sql, params


def matched_aliases() -> list[str]:
    """Return list of all known alias keys (for docs / validation)."""
    return sorted(ALIASES.keys())
