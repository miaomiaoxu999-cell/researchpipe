// Mock JSON responses for Playground.
// Flagship endpoints get rich mocks; everything else gets a templated fallback.

type Mock = Record<string, unknown>;

const SEARCH_MOCK: Mock = {
  query: "半导体设备 国产化",
  type: "research",
  answer:
    "国内半导体设备国产化率从 2020 年 ~10% 提升至 2026 年 ~30%，前道刻蚀（中微）/ 薄膜（拓荆）/ 清洗（盛美）已实现量产突破，光刻机仍是核心瓶颈。",
  results: [
    {
      title: "半导体设备国产化深度报告：从 0 到 1 突破",
      url: "https://research.example.com/semi-equipment-2026",
      content: "我们认为国产化进程在 2026 年进入加速通道...",
      score: 0.94,
      source_type: "broker",
      source_name: "中信证券",
      published_at: "2026-04-12",
    },
    {
      title: "China's semiconductor equipment ecosystem 2026",
      url: "https://research.example.com/intl-semi-cn",
      content: "China's domestic semiconductor equipment market reached $42B in 2025...",
      score: 0.91,
      source_type: "overseas_ib",
      source_name: "Goldman Sachs",
      published_at: "2026-03-28",
    },
  ],
  metadata: {
    total_results: 23,
    data_sources_used: ["qmp_research", "web_search", "bocha"],
    request_id: "req_8f29ab",
    credits_charged: 1,
  },
};

const RESEARCH_SECTOR_MOCK: Mock = {
  request_id: "req_x82fhq",
  status: "completed",
  result: {
    industry: "具身智能",
    snapshot_date: "2026-04-28",
    executive_summary:
      "具身智能赛道 2025 年起进入资本加速期，2026 Q1 单季融资额 ¥184 亿，同比 +320%。技术路径分化为 Tesla Optimus 派 / 谷歌 RT-2 派 / 国产 Figure 派三大阵营，国内头部公司估值 $1-3B 区间，二级市场尚无对应标的。",
    research_views: [
      {
        broker: "中信建投",
        source_type: "broker",
        report_title: "具身智能：从概念到量产的关键一年",
        report_date: "2026-03-22",
        core_thesis: "2026 是具身智能从 demo 走向小批量交付的关键拐点，硬件方案趋于收敛...",
        target_price: null,
        recommendation: "增持",
      },
      {
        broker: "Goldman Sachs",
        source_type: "overseas_ib",
        report_title: "Embodied AI in China: 18 startups to watch",
        report_date: "2026-04-08",
        core_thesis: "We see China's embodied AI race resembling EV in 2018 — abundant capital, fragmented...",
        recommendation: "neutral",
      },
    ],
    deals: {
      domestic: [
        { company: "智元机器人", amount_cny_m: 1200, stage: "B+", date: "2026-03-14", lead_investors: ["高瓴", "红杉中国"] },
        { company: "宇树科技", amount_cny_m: 800, stage: "C", date: "2026-02-20", lead_investors: ["美团龙珠", "阿里"] },
      ],
      overseas: [
        { company: "Figure AI", amount_usd_m: 700, stage: "C", date: "2026-02-29", lead_investors: ["Microsoft", "Nvidia"] },
      ],
      summary: { total_deals: 47, total_amount_cny_b: 18.4, yoy_change: "+320%" },
    },
    valuation_anchors: {
      ps_median: 18,
      latest_priced_rounds: [
        { company: "智元机器人", post_money_usd_b: 2.1, source: "qmp_deal_8f2" },
        { company: "Figure AI", post_money_usd_b: 26, source: "web_news" },
      ],
    },
    key_companies: [
      { name: "智元机器人", stage: "B+", latest_valuation_usd_b: 2.1, lead_investors: ["高瓴", "红杉中国"] },
      { name: "宇树科技", stage: "C", latest_valuation_usd_b: 1.4, lead_investors: ["美团龙珠"] },
      { name: "银河通用", stage: "B", latest_valuation_usd_b: 0.8, lead_investors: ["IDG"] },
    ],
    active_investors: [
      { name: "高瓴", deals_in_sector_24m: 8 },
      { name: "红杉中国", deals_in_sector_24m: 6 },
      { name: "IDG", deals_in_sector_24m: 5 },
    ],
    risks: [
      { category: "tech", description: "灵巧手成本未压缩到量产水平", severity: "high" },
      { category: "regulatory", description: "AI 通用智能安全监管框架未明", severity: "medium" },
    ],
    outlook: {
      catalysts_12m: ["头部公司小批量交付", "Tesla Optimus 量产数据公布"],
      threats_12m: ["美国出口管制升级", "估值泡沫破裂"],
    },
    citations: [
      { id: 1, source_url: "https://research.example.com/csc-embodied-ai", quote: "..." },
      { id: 2, source_url: "https://qmp.research/sector_8f2", quote: "..." },
    ],
    metadata: {
      data_sources_used: ["qmp_research", "qmp_deals", "web_search", "bocha"],
      request_id: "req_x82fhq",
      model: "pro",
      credits_charged: 50,
      generated_in_seconds: 47,
      partial: false,
    },
  },
};

const RESEARCH_COMPANY_MOCK: Mock = {
  request_id: "req_n2x9k1",
  status: "completed",
  result: {
    company_basic: {
      name: "宁德时代",
      ticker: "300750.SZ",
      sector: "动力电池",
      founded_year: 2011,
      hq_city: "宁德",
    },
    snapshot_date: "2026-04-28",
    executive_summary:
      "宁德时代 2025 年全球动力电池市占率 37.3%，连续 9 年第一。海外产能扩张 + 储能业务放量是 2026 主线，但欧美市场地缘风险与 LFP 价格战是核心担忧。",
    business_profile: {
      revenue_mix: { 动力电池: 0.71, 储能: 0.18, 材料及回收: 0.07, 其他: 0.04 },
      top_5_customers_concentration: 0.42,
      products: ["麒麟电池", "神行超充电池", "EnerC 储能系统"],
    },
    peers_dd: [
      { name: "比亚迪", ps_2025: 1.2, market_share: 0.15 },
      { name: "LG Energy", ps_2025: 1.8, market_share: 0.13 },
    ],
    valuation_anchor: {
      pe_ttm: 18.4,
      ps_2025: 2.1,
      industry_median_ps: 1.6,
    },
    filing_risks: {
      ipo_status: "已上市",
      key_risks: [
        { level: "high", description: "美国 IRA 法案 FEOC 限制对北美产能影响" },
        { level: "medium", description: "LFP 价格下行影响毛利" },
      ],
    },
    financials_summary: {
      revenue_5y_cny_b: [130.4, 173.6, 328.6, 400.9, 363.0],
      net_profit_5y_cny_b: [5.6, 15.9, 30.7, 44.1, 50.7],
    },
    founders_background: [
      {
        name: "曾毓群",
        title: "董事长",
        brief: "上海交大物理学硕士，1989 创办 ATL，2011 拆分动力电池业务成立 CATL",
      },
    ],
    major_investors: [
      { name: "本田", type: "strategic", stake: 0.04 },
      { name: "Apple", type: "strategic", note: "通过 Tier-1 间接合作" },
    ],
    recent_news: [
      { title: "宁德时代港股上市获联交所聆讯通过", published_at: "2026-04-22", sentiment: "positive" },
    ],
    red_flags: [
      { category: "geo", description: "北美工厂因 FEOC 暂缓，资本开支不确定", severity: "medium" },
      { category: "concentration", description: "Top 5 客户占比 42%，依赖头部车厂", severity: "low" },
    ],
    outlook: {
      short_term: "Q2 储能订单放量",
      mid_term: "港股上市 + 欧洲产能爬坡",
      long_term: "固态电池量产竞赛",
    },
    citations: [
      { id: 1, source_url: "https://www.szse.cn/disclosure/listed/...prospectus", quote: "..." },
    ],
    metadata: {
      data_sources_used: ["qmp_filings", "qmp_deals", "web_search"],
      model: "pro",
      credits_charged: 50,
      partial: false,
    },
  },
};

const EXTRACT_RESEARCH_MOCK: Mock = {
  url: "https://example.com/csc-semi-equipment.pdf",
  language: "zh",
  metadata: {
    broker: "中信证券",
    broker_country: "CN",
    source_type: "broker",
    report_title: "半导体设备国产化深度报告",
    report_date: "2026-04-12",
    source_url: "https://example.com/csc-semi-equipment.pdf",
  },
  core_thesis:
    "国产半导体设备进入加速突破期，前道刻蚀 / 薄膜 / 清洗 已具量产能力，预计 2027 年整体国产化率突破 35%。",
  target_price: { value: 220, currency: "CNY" },
  recommendation: "买入",
  key_data_points: [
    { metric: "2026E 设备市场规模", value: "$420 亿", source: "SEMI", year: 2026 },
    { metric: "国产化率（前道）", value: "32%", source: "中信证券测算", year: 2026 },
  ],
  risks: ["中美科技制裁升级", "12 寸先进制程产线投放低于预期", "海外设备厂技术迭代加速"],
  confidence_score: 0.91,
  metadata_extras: { credits_charged: 5, request_id: "req_e7c2af" },
};

const COMPANIES_GET_MOCK: Mock = {
  id: "comp_2x9bka",
  name: "宁德时代新能源科技股份有限公司",
  short_name: "宁德时代",
  name_en: "CATL",
  sector: { id: "ind_battery", name: "动力电池" },
  business_overview: "全球领先的动力电池及储能系统供应商...",
  products: ["麒麟电池", "神行超充电池", "EnerC"],
  founders: [{ name: "曾毓群", title: "董事长" }],
  funding_rounds: [
    { stage: "A", date: "2015-08", amount_cny_m: 200 },
    { stage: "B", date: "2017-03", amount_cny_m: 1000 },
    { stage: "IPO", date: "2018-06-11", market: "深交所创业板" },
  ],
  latest_valuation: { source: "secondary_market", value_cny_b: 1080, as_of: "2026-04-28" },
  major_investors: [{ id: "inv_a1", name: "本田" }, { id: "inv_b2", name: "高瓴" }],
  employees: 113000,
  ipo_status: "listed",
  related_companies: [{ name: "邦普循环", relation: "子公司" }, { name: "时代电服", relation: "联营" }],
  _meta: { last_updated_at: "2026-04-26", data_age_days: 2, freshness_status: "fresh" },
};

const DEALS_SEARCH_MOCK: Mock = {
  total: 47,
  results: [
    { id: "deal_8f2", company: "智元机器人", industry: "具身智能", stage: "B+", amount_cny_m: 1200, date: "2026-03-14", lead_investors: [{ id: "inv_h", name: "高瓴" }] },
    { id: "deal_2k9", company: "宇树科技", industry: "具身智能", stage: "C", amount_cny_m: 800, date: "2026-02-20", lead_investors: [{ id: "inv_m", name: "美团龙珠" }] },
    { id: "deal_a1c", company: "银河通用", industry: "具身智能", stage: "B", amount_cny_m: 500, date: "2026-01-10", lead_investors: [{ id: "inv_idg", name: "IDG" }] },
  ],
  metadata: { credits_charged: 1, data_sources_used: ["qmp_deals"] },
};

const REGISTRY: Record<string, Mock> = {
  search: SEARCH_MOCK,
  "research-sector": RESEARCH_SECTOR_MOCK,
  "research-company": RESEARCH_COMPANY_MOCK,
  "extract-research": EXTRACT_RESEARCH_MOCK,
  "companies-get": COMPANIES_GET_MOCK,
  "companies-search": {
    total: 12,
    results: [
      { id: "comp_2x9", name: "宁德时代", sector: "动力电池", stage: "ipo" },
      { id: "comp_3y4", name: "比亚迪", sector: "动力电池", stage: "ipo" },
    ],
  },
  "deals-search": DEALS_SEARCH_MOCK,
  extract: {
    url: "https://example.com/article",
    title: "Sample article title",
    content: "Full article content extracted as markdown...",
    metadata: { credits_charged: 2 },
  },
  "extract-filing": {
    filing_id: "fil_x29",
    schema: "prospectus_v1",
    fields: {
      company_basic: { name: "示例科技", ticker: "688999.SH" },
      business_overview: "...",
      core_products: [{ name: "产品 A", revenue_share: 0.62 }],
      financials_5y_summary: { revenue_cny_m: [120, 180, 245, 310, 405] },
      major_risks: [{ category: "tech", description: "..." }],
    },
    metadata: { credits_charged: 3, confidence_score: 0.88 },
  },
};

export function getMock(key: string | undefined, endpointId: string): Mock {
  if (key && REGISTRY[key]) return REGISTRY[key];
  if (REGISTRY[endpointId]) return REGISTRY[endpointId];
  // Generic fallback
  return {
    request_id: `req_${Math.random().toString(36).slice(2, 10)}`,
    status: "ok",
    result: {
      message:
        "这是一个示例响应（mock）。生产 API 会返回针对该端点的真实结构化数据。",
      endpoint: endpointId,
    },
    metadata: {
      data_sources_used: ["qmp_data", "qmp_research"],
      credits_charged: 1,
      partial: false,
    },
  };
}

// Sample errors with hint_for_agent
export const SAMPLE_ERRORS = {
  rate_limit: {
    error: {
      code: "rate_limit_exceeded",
      message: "Rate limit exceeded: 60 req/min",
      retry_after_seconds: 12,
      hint_for_agent:
        "Wait `retry_after_seconds`, then retry. Consider switching to async polling for /research endpoints to avoid burst.",
      documentation_url: "https://rp.zgen.xin/docs/rate-limits",
    },
  },
  partial: {
    metadata: {
      partial: true,
      warnings: [
        {
          code: "data_source_unavailable",
          source: "web_search",
          message: "Web search upstream returned 503; falling back to secondary source",
          hint_for_agent:
            "Result is still usable. If you need cross-source coverage, retry in 30s with same Idempotency-Key.",
        },
      ],
    },
  },
};
