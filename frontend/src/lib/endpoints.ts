// ResearchPipe 端点元数据 —— 来自 PRD 6.2-6.6
// 50+ 端点全收录；旗舰端点（star: true）参数表单 + mock 响应较精细，其他通用
// 表单 schema 由 zod 推导，但这里用纯 JS 对象描述，避免运行时复杂度

export type ParamKind =
  | "text"
  | "textarea"
  | "number"
  | "select"
  | "multi-select"
  | "toggle"
  | "tags";

export interface ParamSpec {
  name: string;
  label: string;
  kind: ParamKind;
  required?: boolean;
  default?: string | number | boolean | string[];
  options?: { value: string; label: string }[];
  placeholder?: string;
  help?: string;
  // for credits multiplier (e.g. depth=full *2)
  costMultiplier?: Record<string, number>;
}

export type ProductLine = "Search" | "Research" | "Data" | "Watch" | "Account";

export type DataGroup =
  | "Companies"
  | "Investors"
  | "Deals"
  | "Industries"
  | "Valuations"
  | "Filings"
  | "News & Events"
  | "Tasks";

export interface Endpoint {
  id: string; // unique slug used in URL ?endpoint=
  code: string; // PRD code (e.g. "S1", "D12")
  name: string; // display name
  path: string; // e.g. POST /v1/search
  method: "GET" | "POST";
  line: ProductLine;
  group?: DataGroup;
  credits: number; // baseline; can be modified by params
  creditsRange?: string; // displayed
  phase: "M1" | "M2" | "M3";
  star?: boolean; // 差异化旗舰
  desc: string; // 1-line
  params: ParamSpec[];
  mockKey?: string; // mock JSON file key
}

// ─────────────────────────────────────────────────────────────────────────
// SEARCH (6)
// ─────────────────────────────────────────────────────────────────────────
const SEARCH: Endpoint[] = [
  {
    id: "search",
    code: "S1",
    name: "search",
    path: "POST /v1/search",
    method: "POST",
    line: "Search",
    credits: 1,
    creditsRange: "1–2",
    phase: "M1",
    desc: "通用搜索（type 分流：web / news / research / policy / filing）",
    params: [
      { name: "query", label: "Query", kind: "text", required: true, placeholder: "半导体设备 国产化" },
      {
        name: "type",
        label: "Type",
        kind: "select",
        default: "research",
        options: [
          { value: "web", label: "web" },
          { value: "news", label: "news" },
          { value: "research", label: "research" },
          { value: "policy", label: "policy" },
          { value: "filing", label: "filing" },
        ],
      },
      {
        name: "search_depth",
        label: "Search depth",
        kind: "select",
        default: "basic",
        options: [
          { value: "basic", label: "basic (1c)" },
          { value: "advanced", label: "advanced (2c)" },
        ],
        costMultiplier: { basic: 1, advanced: 2 },
      },
      {
        name: "include_answer",
        label: "Include LLM answer",
        kind: "select",
        default: "false",
        options: [
          { value: "false", label: "false" },
          { value: "basic", label: "basic" },
          { value: "advanced", label: "advanced" },
        ],
      },
      { name: "max_results", label: "Max results", kind: "number", default: 20 },
      { name: "time_range", label: "Time range", kind: "text", default: "30d", placeholder: "30d / 6m / 24m" },
      { name: "regions", label: "Regions", kind: "tags", default: ["a-share", "hk", "us"] },
      { name: "languages", label: "Languages", kind: "tags", default: ["zh", "en"] },
    ],
    mockKey: "search",
  },
  {
    id: "extract",
    code: "S2",
    name: "extract",
    path: "POST /v1/extract",
    method: "POST",
    line: "Search",
    credits: 2,
    phase: "M1",
    desc: "单 URL → 全文 / 结构化抽取",
    params: [
      { name: "url", label: "URL", kind: "text", required: true, placeholder: "https://..." },
      { name: "include_images", label: "Include images", kind: "toggle", default: false },
    ],
    mockKey: "extract",
  },
  {
    id: "extract-research",
    code: "S3",
    name: "extract / research",
    path: "POST /v1/extract/research",
    method: "POST",
    line: "Search",
    credits: 5,
    phase: "M1",
    star: true,
    desc: "研报字段抽取（含英→中翻译合并一步）",
    params: [
      { name: "url", label: "URL", kind: "text", required: true, placeholder: "券商研报 PDF / 链接" },
      { name: "language", label: "Output language", kind: "select", default: "zh", options: [{ value: "zh", label: "zh" }, { value: "en", label: "en" }] },
      { name: "include_raw_content", label: "Include raw content", kind: "toggle", default: false },
      { name: "model", label: "Model", kind: "select", default: "auto", options: [{ value: "auto", label: "auto" }, { value: "deepseek-v4", label: "deepseek-v4" }] },
    ],
    mockKey: "extract-research",
  },
  {
    id: "extract-filing",
    code: "S4",
    name: "extract / filing",
    path: "POST /v1/extract/filing",
    method: "POST",
    line: "Search",
    credits: 3,
    phase: "M2",
    star: true,
    desc: "上市文件抽取（5 套 schema：prospectus / inquiry / sponsor / audit / legal）",
    params: [
      { name: "filing_id", label: "Filing ID or URL", kind: "text", required: true },
      {
        name: "schema",
        label: "Schema",
        kind: "select",
        default: "prospectus_v1",
        options: [
          { value: "prospectus_v1", label: "prospectus_v1" },
          { value: "inquiry_v1", label: "inquiry_v1" },
          { value: "sponsor_v1", label: "sponsor_v1" },
          { value: "audit_v1", label: "audit_v1" },
          { value: "legal_v1", label: "legal_v1" },
        ],
      },
    ],
    mockKey: "extract-filing",
  },
  {
    id: "extract-batch",
    code: "S5",
    name: "extract / batch",
    path: "POST /v1/extract/batch",
    method: "POST",
    line: "Search",
    credits: 0,
    creditsRange: "内层叠加",
    phase: "M2",
    desc: "批量 URL 异步抽取（≤100 / 批）",
    params: [
      { name: "urls", label: "URLs", kind: "tags", required: true },
      { name: "schema", label: "Schema", kind: "select", default: "research", options: [{ value: "research", label: "research" }, { value: "filing", label: "filing" }] },
    ],
  },
  {
    id: "jobs",
    code: "S6",
    name: "jobs / get",
    path: "GET /v1/jobs/{id}",
    method: "GET",
    line: "Search",
    credits: 0,
    phase: "M2",
    desc: "查异步 job 状态（batch + research 共用）",
    params: [{ name: "id", label: "Job ID", kind: "text", required: true }],
  },
];

// ─────────────────────────────────────────────────────────────────────────
// RESEARCH (3) ★ flagship
// ─────────────────────────────────────────────────────────────────────────
const RESEARCH: Endpoint[] = [
  {
    id: "research-sector",
    code: "R1",
    name: "research / sector",
    path: "POST /v1/research/sector",
    method: "POST",
    line: "Research",
    credits: 50,
    creditsRange: "20 / 50",
    phase: "M3",
    star: true,
    desc: "赛道全景研究 — 16 字段默认 schema + citations",
    params: [
      { name: "input", label: "Sector / topic", kind: "text", required: true, placeholder: "具身智能" },
      { name: "time_range", label: "Time range", kind: "text", default: "24m" },
      { name: "regions", label: "Regions", kind: "tags", default: ["a-share", "hk", "us"] },
      {
        name: "model",
        label: "Model",
        kind: "select",
        default: "auto",
        options: [
          { value: "mini", label: "mini (20c)" },
          { value: "pro", label: "pro (50c)" },
          { value: "auto", label: "auto" },
        ],
        costMultiplier: { mini: 0.4, pro: 1, auto: 1 },
      },
      {
        name: "depth",
        label: "Depth",
        kind: "select",
        default: "standard",
        options: [
          { value: "summary", label: "summary" },
          { value: "standard", label: "standard (12K)" },
          { value: "full", label: "full (25K)" },
        ],
      },
      { name: "citation_format", label: "Citation format", kind: "select", default: "numbered", options: [{ value: "numbered", label: "numbered" }, { value: "apa", label: "apa" }, { value: "chicago", label: "chicago" }] },
      { name: "stream", label: "Stream (SSE)", kind: "toggle", default: false },
      { name: "output_schema", label: "Custom output_schema (JSON)", kind: "textarea", placeholder: "null = 默认 16 字段 schema" },
    ],
    mockKey: "research-sector",
  },
  {
    id: "research-company",
    code: "R2",
    name: "research / company",
    path: "POST /v1/research/company",
    method: "POST",
    line: "Research",
    credits: 50,
    creditsRange: "20 / 50",
    phase: "M3",
    star: true,
    desc: "公司尽调研究 — red_flags + 16 字段默认 schema",
    params: [
      { name: "input", label: "Company name or ID", kind: "text", required: true, placeholder: "宁德时代" },
      { name: "focus", label: "Focus", kind: "tags", default: ["business", "financials", "risks"], help: "可选：business / financials / risks / patents / peers / news" },
      { name: "model", label: "Model", kind: "select", default: "auto", options: [{ value: "mini", label: "mini" }, { value: "pro", label: "pro" }, { value: "auto", label: "auto" }] },
      { name: "depth", label: "Depth", kind: "select", default: "standard", options: [{ value: "summary", label: "summary" }, { value: "standard", label: "standard" }, { value: "full", label: "full" }] },
      { name: "citation_format", label: "Citation format", kind: "select", default: "numbered", options: [{ value: "numbered", label: "numbered" }, { value: "apa", label: "apa" }, { value: "chicago", label: "chicago" }] },
      { name: "stream", label: "Stream (SSE)", kind: "toggle", default: false },
    ],
    mockKey: "research-company",
  },
  {
    id: "research-valuation",
    code: "R3",
    name: "research / valuation",
    path: "POST /v1/research/valuation",
    method: "POST",
    line: "Research",
    credits: 50,
    creditsRange: "20 / 50",
    phase: "M3",
    desc: "估值锚研究 — 行业 PS/PE + 近期 priced rounds",
    params: [
      { name: "input", label: "Sector or company", kind: "text", required: true },
      { name: "model", label: "Model", kind: "select", default: "auto", options: [{ value: "mini", label: "mini" }, { value: "pro", label: "pro" }, { value: "auto", label: "auto" }] },
      { name: "regions", label: "Regions", kind: "tags", default: ["a-share", "us"] },
    ],
  },
];

// ─────────────────────────────────────────────────────────────────────────
// DATA (38)
// ─────────────────────────────────────────────────────────────────────────
const DATA: Endpoint[] = [
  // Companies
  { id: "companies-search", code: "D1", name: "companies / search", path: "POST /v1/companies/search", method: "POST", line: "Data", group: "Companies", credits: 0.5, phase: "M1",
    desc: "公司搜索（名称/行业/地区/阶段）",
    params: [
      { name: "query", label: "Query", kind: "text", placeholder: "宁德 / 半导体" },
      { name: "industry", label: "Industry", kind: "text" },
      { name: "stage", label: "Stage", kind: "select", default: "any", options: [{ value: "any", label: "any" }, { value: "seed", label: "seed" }, { value: "a", label: "A" }, { value: "b", label: "B" }, { value: "growth", label: "growth" }, { value: "ipo", label: "ipo" }] },
      { name: "limit", label: "Limit", kind: "number", default: 20 },
    ], mockKey: "companies-search" },
  { id: "companies-get", code: "D2", name: "companies / get", path: "GET /v1/companies/{id}", method: "GET", line: "Data", group: "Companies", credits: 0.5, phase: "M1",
    desc: "公司画像（10 字段 M1 必出）",
    params: [
      { name: "id", label: "Company ID", kind: "text", required: true, placeholder: "comp_2x9..." },
      { name: "exclude_fields", label: "Exclude fields", kind: "tags" },
      { name: "expand", label: "Expand", kind: "tags", help: "investors / filings / peers" },
    ], mockKey: "companies-get" },
  { id: "companies-deals", code: "D3", name: "companies / deals", path: "GET /v1/companies/{id}/deals", method: "GET", line: "Data", group: "Companies", credits: 1, phase: "M1", desc: "该公司所有融资事件", params: [{ name: "id", label: "Company ID", kind: "text", required: true }] },
  { id: "companies-peers", code: "D4", name: "companies / peers", path: "POST /v1/companies/{id}/peers", method: "POST", line: "Data", group: "Companies", credits: 2, phase: "M2", desc: "对标公司",
    params: [{ name: "id", label: "Company ID", kind: "text", required: true }, { name: "n", label: "Count", kind: "number", default: 5 }] },
  { id: "companies-news", code: "D5", name: "companies / news", path: "GET /v1/companies/{id}/news", method: "GET", line: "Data", group: "Companies", credits: 1, phase: "M1", desc: "公司相关新闻",
    params: [{ name: "id", label: "Company ID", kind: "text", required: true }, { name: "time_range", label: "Time range", kind: "text", default: "90d" }] },
  { id: "companies-founders", code: "D6", name: "companies / founders ★", path: "GET /v1/companies/{id}/founders", method: "GET", line: "Data", group: "Companies", credits: 1, creditsRange: "1 / 3", phase: "M2", star: true, desc: "创始团队（默认精简；deep=true 出深度背景）",
    params: [{ name: "id", label: "Company ID", kind: "text", required: true }, { name: "deep", label: "Deep mode", kind: "toggle", default: false, costMultiplier: { true: 3, false: 1 } }] },

  // Investors
  { id: "investors-search", code: "D7", name: "investors / search", path: "POST /v1/investors/search", method: "POST", line: "Data", group: "Investors", credits: 0.5, phase: "M1", desc: "机构搜索",
    params: [{ name: "query", label: "Query", kind: "text", placeholder: "高瓴 / IDG" }, { name: "type", label: "Type", kind: "select", default: "any", options: [{ value: "any", label: "any" }, { value: "vc", label: "VC" }, { value: "pe", label: "PE" }, { value: "cvc", label: "CVC" }] }] },
  { id: "investors-get", code: "D8", name: "investors / get", path: "GET /v1/investors/{id}", method: "GET", line: "Data", group: "Investors", credits: 0.5, phase: "M1", desc: "机构画像", params: [{ name: "id", label: "Investor ID", kind: "text", required: true }] },
  { id: "investors-portfolio", code: "D9", name: "investors / portfolio", path: "GET /v1/investors/{id}/portfolio", method: "GET", line: "Data", group: "Investors", credits: 1, phase: "M1", desc: "投过的项目",
    params: [{ name: "id", label: "Investor ID", kind: "text", required: true }, { name: "limit", label: "Limit", kind: "number", default: 50 }] },
  { id: "investors-preferences", code: "D10", name: "investors / preferences", path: "GET /v1/investors/{id}/preferences", method: "GET", line: "Data", group: "Investors", credits: 0.5, phase: "M2", desc: "投资偏好（行业 / 轮次画像）", params: [{ name: "id", label: "Investor ID", kind: "text", required: true }] },
  { id: "investors-exits", code: "D11", name: "investors / exits ★", path: "GET /v1/investors/{id}/exits", method: "GET", line: "Data", group: "Investors", credits: 1, phase: "M2", star: true, desc: "退出案例（一级市场新增）", params: [{ name: "id", label: "Investor ID", kind: "text", required: true }] },

  // Deals
  { id: "deals-search", code: "D12", name: "deals / search", path: "POST /v1/deals/search", method: "POST", line: "Data", group: "Deals", credits: 1, phase: "M1", desc: "融资事件搜索（多维筛选）",
    params: [
      { name: "industry", label: "Industry", kind: "text", placeholder: "具身智能" },
      { name: "stage", label: "Stage", kind: "select", default: "any", options: [{ value: "any", label: "any" }, { value: "seed", label: "seed" }, { value: "a", label: "A" }, { value: "b", label: "B" }, { value: "growth", label: "growth" }] },
      { name: "amount_min", label: "Min amount (¥M)", kind: "number" },
      { name: "time_range", label: "Time range", kind: "text", default: "12m" },
      { name: "limit", label: "Limit", kind: "number", default: 20 },
    ], mockKey: "deals-search" },
  { id: "deals-get", code: "D13", name: "deals / get", path: "GET /v1/deals/{id}", method: "GET", line: "Data", group: "Deals", credits: 0.5, phase: "M1", desc: "单事件详情", params: [{ name: "id", label: "Deal ID", kind: "text", required: true }] },
  { id: "deals-timeline", code: "D14", name: "deals / timeline", path: "POST /v1/deals/timeline", method: "POST", line: "Data", group: "Deals", credits: 2, phase: "M2", desc: "公司融资时间线", params: [{ name: "company_id", label: "Company ID", kind: "text", required: true }] },
  { id: "deals-overseas", code: "D15", name: "deals / overseas", path: "POST /v1/deals/overseas", method: "POST", line: "Data", group: "Deals", credits: 2, phase: "M2", desc: "海外创投 deal",
    params: [{ name: "industry", label: "Industry", kind: "text" }, { name: "country", label: "Country", kind: "text", default: "us" }] },
  { id: "deals-co-investors", code: "D16", name: "deals / co_investors ★", path: "GET /v1/deals/{id}/co_investors", method: "GET", line: "Data", group: "Deals", credits: 2, phase: "M2", star: true, desc: "co-investor 网络分析（一级市场新增）", params: [{ name: "id", label: "Deal ID", kind: "text", required: true }] },

  // Industries
  { id: "industries-search", code: "D17", name: "industries / search", path: "POST /v1/industries/search", method: "POST", line: "Data", group: "Industries", credits: 0.5, phase: "M1", desc: "关键词 → 标准行业 tag", params: [{ name: "query", label: "Query", kind: "text", required: true, placeholder: "AI 制药" }] },
  { id: "industries-deals", code: "D18", name: "industries / deals", path: "GET /v1/industries/{id}/deals", method: "GET", line: "Data", group: "Industries", credits: 1, phase: "M1", desc: "赛道融资事件",
    params: [{ name: "id", label: "Industry ID", kind: "text", required: true }, { name: "time_range", label: "Time range", kind: "text", default: "12m" }] },
  { id: "industries-companies", code: "D19", name: "industries / companies", path: "GET /v1/industries/{id}/companies", method: "GET", line: "Data", group: "Industries", credits: 1, phase: "M1", desc: "赛道公司列表", params: [{ name: "id", label: "Industry ID", kind: "text", required: true }] },
  { id: "industries-chain", code: "D20", name: "industries / chain", path: "GET /v1/industries/{id}/chain", method: "GET", line: "Data", group: "Industries", credits: 2, phase: "M2", desc: "上下游产业链图谱", params: [{ name: "id", label: "Industry ID", kind: "text", required: true }] },
  { id: "industries-policies", code: "D21", name: "industries / policies", path: "GET /v1/industries/{id}/policies", method: "GET", line: "Data", group: "Industries", credits: 1, phase: "M2", desc: "相关政策 + impact_assessment", params: [{ name: "id", label: "Industry ID", kind: "text", required: true }] },
  { id: "industries-tech-roadmap", code: "D22", name: "industries / tech_roadmap ★", path: "GET /v1/industries/{id}/tech_roadmap", method: "GET", line: "Data", group: "Industries", credits: 3, phase: "M2", star: true, desc: "技术路线图（新增）", params: [{ name: "id", label: "Industry ID", kind: "text", required: true }] },
  { id: "industries-key-tech", code: "D23", name: "industries / key_technologies ★", path: "GET /v1/industries/{id}/key_technologies", method: "GET", line: "Data", group: "Industries", credits: 2, phase: "M2", star: true, desc: "核心技术清单 + 国产化率（新增）", params: [{ name: "id", label: "Industry ID", kind: "text", required: true }] },
  { id: "industries-maturity", code: "D24", name: "industries / maturity ★", path: "POST /v1/industries/{id}/maturity", method: "POST", line: "Data", group: "Industries", credits: 5, phase: "M3", star: true, desc: "技术成熟度（Gartner 曲线）（新增）", params: [{ name: "id", label: "Industry ID", kind: "text", required: true }] },
  { id: "technologies-compare", code: "D25", name: "technologies / compare ★", path: "POST /v1/technologies/compare", method: "POST", line: "Data", group: "Industries", credits: 5, phase: "M3", star: true, desc: "技术路线对比（新增）",
    params: [{ name: "tech_a", label: "Tech A", kind: "text", required: true }, { name: "tech_b", label: "Tech B", kind: "text", required: true }] },

  // Valuations
  { id: "valuations-search", code: "D26", name: "valuations / search", path: "POST /v1/valuations/search", method: "POST", line: "Data", group: "Valuations", credits: 1, phase: "M1", desc: "估值数据查询",
    params: [{ name: "industry", label: "Industry", kind: "text" }, { name: "stage", label: "Stage", kind: "text" }] },
  { id: "valuations-multiples", code: "D27", name: "valuations / multiples", path: "POST /v1/valuations/multiples", method: "POST", line: "Data", group: "Valuations", credits: 1, phase: "M1", desc: "行业 PS/PE 倍数",
    params: [{ name: "industry", label: "Industry", kind: "text", required: true }, { name: "metric", label: "Metric", kind: "select", default: "ps", options: [{ value: "ps", label: "PS" }, { value: "pe", label: "PE" }, { value: "pb", label: "PB" }] }] },
  { id: "valuations-compare", code: "D28", name: "valuations / compare", path: "POST /v1/valuations/compare", method: "POST", line: "Data", group: "Valuations", credits: 3, phase: "M2", desc: "跨市场对标（A / HK / US 同赛道）",
    params: [{ name: "industry", label: "Industry", kind: "text", required: true }, { name: "markets", label: "Markets", kind: "tags", default: ["a-share", "hk", "us"] }] },
  { id: "valuations-distribution", code: "D29", name: "valuations / distribution ★", path: "POST /v1/valuations/distribution", method: "POST", line: "Data", group: "Valuations", credits: 2, phase: "M2", star: true, desc: "估值带分布 + 独角兽阈值（一级市场新增）",
    params: [{ name: "industry", label: "Industry", kind: "text", required: true }, { name: "stage", label: "Stage", kind: "text" }] },

  // Filings
  { id: "filings-search", code: "D30", name: "filings / search", path: "POST /v1/filings/search", method: "POST", line: "Data", group: "Filings", credits: 0.5, phase: "M2", desc: "文件搜索（公司 / 类型 / 时间）",
    params: [
      { name: "company_id", label: "Company ID", kind: "text" },
      { name: "filing_type", label: "Filing type", kind: "select", default: "any", options: [{ value: "any", label: "any" }, { value: "prospectus", label: "prospectus" }, { value: "inquiry", label: "inquiry" }, { value: "sponsor", label: "sponsor" }, { value: "audit", label: "audit" }, { value: "legal", label: "legal" }] },
      { name: "time_range", label: "Time range", kind: "text", default: "24m" },
    ] },
  { id: "filings-get", code: "D31", name: "filings / get", path: "GET /v1/filings/{id}", method: "GET", line: "Data", group: "Filings", credits: 0.5, phase: "M2", desc: "文件元数据 + 直链", params: [{ name: "id", label: "Filing ID", kind: "text", required: true }] },
  { id: "filings-extract", code: "D32", name: "filings / extract ★", path: "POST /v1/filings/{id}/extract", method: "POST", line: "Data", group: "Filings", credits: 3, phase: "M2", star: true, desc: "5 套 schema 字段抽取",
    params: [
      { name: "id", label: "Filing ID", kind: "text", required: true },
      { name: "schema", label: "Schema", kind: "select", default: "prospectus_v1", options: [{ value: "prospectus_v1", label: "prospectus_v1" }, { value: "inquiry_v1", label: "inquiry_v1" }, { value: "sponsor_v1", label: "sponsor_v1" }, { value: "audit_v1", label: "audit_v1" }, { value: "legal_v1", label: "legal_v1" }] },
    ] },
  { id: "filings-risks", code: "D33", name: "filings / risks", path: "POST /v1/filings/{id}/risks", method: "POST", line: "Data", group: "Filings", credits: 2, phase: "M2", desc: "风险点抽取（高 / 中 / 低）", params: [{ name: "id", label: "Filing ID", kind: "text", required: true }] },
  { id: "filings-financials", code: "D34", name: "filings / financials", path: "POST /v1/filings/{id}/financials", method: "POST", line: "Data", group: "Filings", credits: 2, phase: "M3", desc: "5 年财务数据抽取", params: [{ name: "id", label: "Filing ID", kind: "text", required: true }] },

  // News & Events
  { id: "news-search", code: "D35", name: "news / search", path: "POST /v1/news/search", method: "POST", line: "Data", group: "News & Events", credits: 1, phase: "M1", desc: "新闻搜索",
    params: [{ name: "query", label: "Query", kind: "text", required: true }, { name: "time_range", label: "Time range", kind: "text", default: "30d" }] },
  { id: "news-recent", code: "D36", name: "news / recent", path: "POST /v1/news/recent", method: "POST", line: "Data", group: "News & Events", credits: 0.5, phase: "M1", desc: "最新新闻流（按行业 / 公司过滤）",
    params: [{ name: "industry", label: "Industry", kind: "text" }, { name: "company_id", label: "Company ID", kind: "text" }] },
  { id: "events-timeline", code: "D37", name: "events / timeline", path: "POST /v1/events/timeline", method: "POST", line: "Data", group: "News & Events", credits: 2, phase: "M2", desc: "综合事件时间线（合 deals + filings + news + policy）",
    params: [{ name: "company_id", label: "Company ID", kind: "text" }, { name: "industry", label: "Industry", kind: "text" }] },

  // Tasks
  { id: "screen", code: "D38", name: "screen", path: "POST /v1/screen", method: "POST", line: "Data", group: "Tasks", credits: 5, phase: "M2", desc: "赛道筛选器（多条件 → 公司列表）",
    params: [
      { name: "industry", label: "Industry", kind: "text", required: true },
      { name: "min_funding", label: "Min funding (¥M)", kind: "number" },
      { name: "stage", label: "Stage", kind: "text" },
      { name: "geo", label: "Geo", kind: "text", default: "cn" },
    ] },
];

// ─────────────────────────────────────────────────────────────────────────
// WATCH (2)
// ─────────────────────────────────────────────────────────────────────────
const WATCH: Endpoint[] = [
  { id: "watch-create", code: "W1", name: "watch / create", path: "POST /v1/watch/create", method: "POST", line: "Watch", credits: 0, phase: "M2", desc: "创建 watchlist（行业 / 公司 / 机构组合 + filter）",
    params: [
      { name: "name", label: "Watchlist name", kind: "text", required: true },
      { name: "industries", label: "Industries", kind: "tags" },
      { name: "company_ids", label: "Company IDs", kind: "tags" },
      { name: "investor_ids", label: "Investor IDs", kind: "tags" },
      { name: "cron", label: "Cron schedule", kind: "text", default: "0 8 * * 1", placeholder: "0 8 * * 1 = 周一 8:00" },
    ] },
  { id: "watch-digest", code: "W2", name: "watch / digest", path: "GET /v1/watch/{id}/digest", method: "GET", line: "Watch", credits: 10, phase: "M2", star: true, desc: "Watchlist 摘要（昨日 deal + news + filings + LLM 摘要）",
    params: [{ name: "id", label: "Watchlist ID", kind: "text", required: true }] },
];

// ─────────────────────────────────────────────────────────────────────────
// ACCOUNT (3)
// ─────────────────────────────────────────────────────────────────────────
const ACCOUNT: Endpoint[] = [
  { id: "me", code: "A1", name: "me", path: "GET /v1/me", method: "GET", line: "Account", credits: 0, phase: "M1", desc: "当前 key 信息（档位 + quota）", params: [] },
  { id: "usage", code: "A2", name: "usage", path: "GET /v1/usage", method: "GET", line: "Account", credits: 0, phase: "M1", desc: "用量历史（按端点 / 日期）",
    params: [{ name: "from", label: "From", kind: "text", placeholder: "2026-04-01" }, { name: "to", label: "To", kind: "text", placeholder: "2026-04-30" }] },
  { id: "billing", code: "A3", name: "billing", path: "GET /v1/billing", method: "GET", line: "Account", credits: 0, phase: "M1", desc: "当月账单预估", params: [] },
];

export const ENDPOINTS: Endpoint[] = [
  ...SEARCH,
  ...RESEARCH,
  ...DATA,
  ...WATCH,
  ...ACCOUNT,
];

export const ENDPOINTS_BY_LINE: Record<ProductLine, Endpoint[]> = {
  Search: SEARCH,
  Research: RESEARCH,
  Data: DATA,
  Watch: WATCH,
  Account: ACCOUNT,
};

export const DATA_GROUPS: DataGroup[] = [
  "Companies",
  "Investors",
  "Deals",
  "Industries",
  "Valuations",
  "Filings",
  "News & Events",
  "Tasks",
];

export function findEndpoint(id: string): Endpoint | undefined {
  return ENDPOINTS.find((e) => e.id === id);
}

// Compute estimated credits given current values
export function estimateCredits(ep: Endpoint, values: Record<string, unknown>): number {
  let cost = ep.credits;
  for (const p of ep.params) {
    if (!p.costMultiplier) continue;
    const v = values[p.name];
    const key = String(v);
    if (key in p.costMultiplier) {
      cost = ep.credits * p.costMultiplier[key];
      break;
    }
  }
  return Math.max(0, Math.round(cost * 10) / 10);
}
