"""20 user-case test definitions covering diverse query types.

Each case has:
  id: stable identifier
  category: one of {sector, single_stock, hybrid, niche, english, metadata,
                    timeseries, comparative, hot_topic, policy, macro, ticker,
                    ambiguous, deep_chain, claim_check, commodity, off_topic,
                    technical, multi_step, factual_lookup}
  query: the user prompt
  expects: list of qualitative checks (used for manual review)
"""

CASES = [
    # ── Sector overviews (corpus-heavy) ───────────────────────────────
    {
        "id": "uc01_semiconductor",
        "category": "sector",
        "query": "半导体设备国产化进展如何？哪些公司值得关注？",
        "expects": [
            "国产化率数字（百分比）",
            "至少 3 家具体公司名",
            "细分环节（光刻/刻蚀/CMP等）",
            "≥3 个不同 broker 引用",
        ],
    },
    {
        "id": "uc02_solar_chain",
        "category": "sector",
        "query": "光伏产业链当前价格走势如何？硅料、电池片、组件分别什么状态？",
        "expects": ["价格区间数字", "供需评论", "各环节分别讨论"],
    },
    {
        "id": "uc03_innovation_drug",
        "category": "sector",
        "query": "中国创新药出海现状？哪些 license-out 交易值得关注？",
        "expects": ["BD 交易金额", "公司名（如百济、信达、君实等）", "靶点/适应症"],
    },

    # ── Single-stock fundamental ──────────────────────────────────────
    {
        "id": "uc04_catl_solid_state",
        "category": "single_stock",
        "query": "宁德时代固态电池量产进度如何？",
        "expects": ["量产时间表", "技术路线（硫化物/氧化物等）", "行业地位"],
    },
    {
        "id": "uc05_byd_overseas",
        "category": "single_stock",
        "query": "比亚迪海外销量增长情况？欧洲和东南亚市场各做得怎么样？",
        "expects": ["销量数字", "区域细分", "时间序列"],
    },

    # ── Hybrid (corpus + web) ─────────────────────────────────────────
    {
        "id": "uc06_deepseek_impact",
        "category": "hybrid",
        "query": "DeepSeek 的崛起对国内算力需求和云厂商资本支出有什么影响？",
        "expects": ["算力需求评估", "云厂商动作", "可能的 web 引用"],
    },

    # ── Niche / less-covered ──────────────────────────────────────────
    {
        "id": "uc07_drone_defense",
        "category": "niche",
        "query": "无人机军用市场国内有哪些公司？",
        "expects": ["公司名", "如果 corpus 不足应通过 web 补充"],
    },

    # ── English query ─────────────────────────────────────────────────
    {
        "id": "uc08_english_query",
        "category": "english",
        "query": "How is BYD's overseas EV expansion progressing? What are the key markets?",
        "expects": ["可中文回答（不强制英文）", "数据有引用"],
    },

    # ── Metadata-only (filename based) ────────────────────────────────
    {
        "id": "uc09_metadata_search",
        "category": "metadata",
        "query": "列出最近中信证券发布的关于半导体的研报",
        "expects": ["≥3 篇研报", "都是中信证券", "都涉及半导体"],
    },

    # ── Time-series question ──────────────────────────────────────────
    {
        "id": "uc10_lithium_price",
        "category": "timeseries",
        "query": "近 3 年碳酸锂价格走势如何？目前处在什么位置？",
        "expects": ["价格数字", "时间点", "趋势判断"],
    },

    # ── Comparative ──────────────────────────────────────────────────
    {
        "id": "uc11_catl_vs_lg",
        "category": "comparative",
        "query": "宁德时代和 LG 新能源在动力电池市场的份额对比？",
        "expects": ["双方市占率", "区域差异", "技术路线对比"],
    },

    # ── Hot topic / breaking ─────────────────────────────────────────
    {
        "id": "uc12_ai_capex",
        "category": "hot_topic",
        "query": "国内 AI 算力 capex 2025 年规模有多大？",
        "expects": ["数字", "云厂商分布", "时间锚定"],
    },

    # ── Policy ────────────────────────────────────────────────────────
    {
        "id": "uc13_xinchuang",
        "category": "policy",
        "query": "信创产业最新进展？政策推进到哪个阶段？",
        "expects": ["政策文件名", "覆盖范围（党政/行业）", "受益公司"],
    },

    # ── Macro ─────────────────────────────────────────────────────────
    {
        "id": "uc14_tech_valuation",
        "category": "macro",
        "query": "目前 A 股科技股估值水平和历史相比如何？",
        "expects": ["PE/PB 数字", "行业拆解", "结论"],
    },

    # ── Specific ticker ──────────────────────────────────────────────
    {
        "id": "uc15_ticker_300750",
        "category": "ticker",
        "query": "300750 这家公司最新一季业绩怎么样？",
        "expects": ["识别为宁德时代", "业绩数字", "环比/同比"],
    },

    # ── Ambiguous / minimal query ────────────────────────────────────
    {
        "id": "uc16_ambiguous",
        "category": "ambiguous",
        "query": "你好",
        "expects": ["不应崩", "应主动询问需求或介绍能力"],
    },

    # ── Deep industry chain ──────────────────────────────────────────
    {
        "id": "uc17_pcb_chain",
        "category": "deep_chain",
        "query": "PCB 涨价是什么原因？产业链上谁受益？",
        "expects": ["原因分析（铜价/订单等）", "上下游公司", "受益逻辑"],
    },

    # ── Claim that needs citation ────────────────────────────────────
    {
        "id": "uc18_humanoid_robot",
        "category": "claim_check",
        "query": "人形机器人 2025 年商业化前景如何？特斯拉 Optimus 交付节奏？",
        "expects": ["具体节奏数字", "≥1 个 web 引用", "国内对标公司"],
    },

    # ── Commodity-driven ─────────────────────────────────────────────
    {
        "id": "uc19_copper_impact",
        "category": "commodity",
        "query": "铜价上涨对哪些 A 股公司有利？",
        "expects": ["铜价数据", "受益公司分类（矿/加工）", "弹性测算"],
    },

    # ── Off-topic / refusal ──────────────────────────────────────────
    {
        "id": "uc20_off_topic",
        "category": "off_topic",
        "query": "今天北京天气怎么样？",
        "expects": ["不应假装查询", "应礼貌说明范围或拒绝"],
    },
]

assert len(CASES) == 20
assert len({c["id"] for c in CASES}) == 20
