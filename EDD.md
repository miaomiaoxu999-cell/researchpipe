# 投资研报结构化提取 API — 工程设计文档（EDD）

| 项目 | 内容 |
|---|---|
| 项目代号 | ResearchPipe |
| 编写日期 | 2026-04-28 |
| 文档状态 | v3 - 中国版 Tavily / 4 产品线 / 50 端点 / Tavily 模式（Search 同步 + Research 异步） / 一级市场聚焦 |
| 配套 PRD | 同目录 PRD.md |

---

## 一、系统总览

### 1.1 架构总图

```
   ┌──────────────┐   ┌───────────────┐   ┌─────────────────┐
   │ HTTP Client  │   │ Python/Node   │   │ Claude Desktop  │
   │ (curl/n8n等) │   │ SDK           │   │ Cursor / Cline  │
   └───────┬──────┘   └───────┬───────┘   └────────┬────────┘
           │                  │                    │
           │                  │           ┌────────▼────────┐
           │                  │           │  MCP Server     │
           │                  │           │ (researchpipe-  │
           │                  │           │  mcp, npm/uvx)  │
           │                  │           └────────┬────────┘
           │                  │                    │
           └──────────────────┴────────────────────┘
                              │ HTTPS + API Key
                ┌─────────────▼────────────┐
                │   Next.js 前端           │ Vercel 部署
                │  Landing / Playground    │ - 访客 demo 限频
                │  Docs / Dashboard        │ - 登录后 API Key 管理
                └─────────────┬────────────┘
                              │ 内部代理转发
                ┌─────────────▼────────────┐
                │   API Gateway (Nginx)    │ 限流 / 鉴权 / 日志
                └─────────────┬────────────┘
                              │
                ┌─────────────▼────────────┐
                │   ResearchPipe API       │ FastAPI（扩展 ventureos/QMPData）
                │   - API Key 鉴权         │
                │   - Credits 计费 / quota │
                │   - 端点路由（9 组）     │
                           │
                ┌──────────▼──────────┐
                │   多源查询编排器       │ ★ 核心组件
                │  Source Orchestrator  │
                │  本地优先 + API fallback │
                └─┬───┬───┬───┬───┬───┘
                  │   │   │   │   │
        ┌─────────┘   │   │   │   └─────────┐
        │             │   │   │             │
   ┌────▼────┐ ┌─────▼┐ ┌▼──────┐ ┌────────▼────────────┐
   │qmp_data │ │filings│ │news   │ │A 线 4 渠道路由器     │
   │PG+pgvec │ │ kcb   │ │flash  │ │┌──────────────────┐│
   │(已就位) │ │ cyb   │ │       │ ││ Tavily（搜+抓）  ││
   └────▲────┘ └───▲──┘ └───▲───┘ ││ Bocha（中文搜）  ││
        │          │        │     ││ Serper（海外搜） ││
        │   ┌──────┴────────┴───┐ ││ Firecrawl（抓取）││
        │   │ 抓取流水线（B线） │ │└──────────────────┘│
        │   │ scrape_qmp_*.py   │ └──────────▲──────────┘
        │   │ + cron 调度       │            │
        │   └───────▲───────────┘            │
        │           │                        │
        │     ┌─────▼──────┐                 │
        │     │企名片 API  │ DES 解密         │
        │     │ pro.qmp.cn │ Token JWT        │
        │     └────────────┘                 │
        │                                    │
        └────────────┬───────────────────────┘
                     │
            ┌────────▼────────┐
            │ DeepSeek V4 抽取 │ DashScope 阿里云百炼
            │ - 字段抽取       │ Fallback: V3.2 → Qwen3
            │ - 翻译合并一步   │
            │ - JSON schema 校 │
            └────────┬────────┘
                     │
            ┌────────▼────────┐
            │  统一输出 schema │ 归一化 JSON
            │  + 缓存 Redis    │
            └─────────────────┘
```

### 1.2 核心数据流

**写入路径（B 线，爬虫 + 异步抽取）**
```
scrape_qmp_reports.py
  → DES 解密 → CSV 落盘 → 入 PostgreSQL（rp_filings.raw 表）
  → PDF 下载 Worker → MinIO 缓存
  → pdftotext -layout → rp_filings.raw_text
  → 抽取 Worker → DeepSeek V4 → rp_filing_extractions
  → pgvector 向量索引
```

**读取路径（客户查询）**
```
客户 → API Gateway → 鉴权 → 编排器
  → [并行] 自建库（qmp_data + rp_*） + A 线 API
  → 结果合并去重
  → DeepSeek 衍生分析（仅 sector-snapshot）
  → Redis 缓存 + 返回 + 异步入库
```

### 1.3 关键复用资源清单

| 资源 | 路径 | 复用方式 |
|---|---|---|
| qmp_data DB | Docker `qmp_postgres:5432` | 直连，新增表用 `rp_*` 前缀 |
| qmp 抓取流水线 | `/home/muye/qimingpian/` | 扩展 `scrape_qmp_reports.py`（已写） |
| qmp API 客户端 | `qimingpian_api.py`（已有 DES + 速率控制 + GeeTest 检测）| 直接 import |
| FastAPI 服务 | `/home/muye/ventureos/QMPData/api/main.py` | 增加新路由文件 `routes/research_pipe.py` |
| mockrogo LLM 适配器 | `mockrogo/backend/src/services/llm` | fork 简化 |
| mockrogo RAG | `mockrogo/backend/src/services/rag` | 上市文件 PDF 抽取流水线复用 |
| Redis | Docker `qmp_redis:6379` | 缓存复用 |
| Token 保活 | `cookie_keepalive.py` + `token_checker.py` | 已稳定运行 |

**复用预计可省 60-70% 开发时间。**

---

## 二、技术栈选型

### 2.1 选型决策表

| 组件 | 选型 | 理由 | 备选 |
|---|---|---|---|
| API 服务层 | Python FastAPI（扩展 ventureos/QMPData）| 复用现有 99 天稳定运行的 24 端点服务 | Express |
| **前端** | **Next.js 14 (App Router) + Tailwind + shadcn/ui** | Cursor / Claude Code 配合最顺；Vercel 一键部署 | Vue + Naive UI |
| **Python SDK** | 手写薄包装（httpx + pydantic）| 投研客户主流栈；生态最成熟 | OpenAPI 自动生成 |
| **Node SDK** | TypeScript + axios + zod | Next.js 后端 / 自家 web app 直用 | OpenAPI 自动生成 |
| **MCP Server** | TypeScript（@modelcontextprotocol/sdk）| Anthropic 官方 SDK，Claude Desktop 默认支持 | Python MCP |
| LLM 主 | DeepSeek V4（DashScope 阿里云百炼）| ¥0.5/1M-in、¥1.5/1M-out、中文质量好、长上下文 | — |
| LLM 备 | DeepSeek V3.2（蓝耘）→ Qwen3-235B → GLM | Failover；mockrogo 已配 | — |
| 关系数据库 | PostgreSQL 15 + pgvector | qmp_data 已就位 | — |
| 缓存 | Redis 7 | qmp_redis 已运行 | — |
| 对象存储 | MinIO（自部署）| 上市 PDF 67K × 5MB ≈ 350GB，自部署 ¥200/月 vs 阿里 OSS ¥800/月。**M1 不需要**（A 线套壳不存 PDF），M2 上市文件抽取流水线启动时再部署 | 阿里 OSS |
| 爬虫框架 | Python + DES（企名片专用）+ Playwright（券商官网）| 复用 qimingpian_api.py | — |
| 任务调度 | crontab + node-cron + BullMQ | 复用 mockrogo + qmp 现有 cron | Celery |
| **Research 异步 worker** | **BullMQ + Redis pubsub + FastAPI SSE** | Research 多步 LLM 编排需异步；BullMQ 排队 / pubsub 推 SSE / FastAPI 原生 SSE 支持 | Celery + RabbitMQ |
| **Research jobs 持久化** | PostgreSQL `rp_research_jobs` 表 | 客户 7 天内可查历史 jobs | Redis only（数据丢失风险）|
| **幂等性** | PostgreSQL `rp_idempotency_keys` 表 | 24h 内同 key 同请求只扣一次费 | Redis（24h TTL 自动清理但需写入路径处理重启）|
| **实体去重** | PostgreSQL `rp_entity_aliases` 表 + fuzzy match + LLM 兜底 | 多源同一公司去重，结果落库下次直接命中 | RapidFuzz + 自建模型 |
| 部署 | **自托管（WSL / Ubuntu laptop / 自购服务器）** + frp/cloudflare tunnel | M1 走零云成本路线，rp.zgen.xin 子域名暴露公网 | 阿里云 ECS（流量上来后迁） |
| 前端部署 | Vercel | Next.js 原生支持 + 全球 CDN + 免费起步 | 自托管 Nginx |
| 反向代理 | Nginx | 标准 | Caddy |
| 监控 | Prometheus + Grafana + Loki | 标准栈 | — |
| API 文档 | OpenAPI 3.0（FastAPI 内置）+ Mintlify / Stoplight 美化 | 自动生成 + 投研垂类 Cookbook 手写 | — |

### 2.2 复用 mockrogo 的具体模块

| 模块 | 路径 | 复用方式 |
|---|---|---|
| LLM 适配器（多模型切换）| mockrogo/backend/src/services/llm | fork + 简化 |
| Sequelize 模型基类 | mockrogo/backend/src/models | 直接复用 |
| Redis 装饰器 | mockrogo/backend/src/cache | 直接复用 |
| RAG pipeline（PDF→向量→LLM）| mockrogo/backend/src/services/rag | 字段抽取重用 |
| 调度器 | mockrogo/backend/src/services/scheduler | 爬虫调度复用 |
| DashScope 客户端 | mockrogo/backend/src/services/llm/dashscope | 直接复用 |

---

## 三、数据库 schema

### 3.1 复用 qmp_data 已有表（不动）

`events` / `institutions` / `institution_profiles` / `institution_industry_preferences` / `institution_round_preferences` / `valuations` / `industry_ps_multiples` / `investment_cases`（向量索引已就位）

### 3.2 新增 ResearchPipe 专用表（`rp_` 前缀，避免冲突）

```sql
-- 上市文件原始记录（来自 kcb_reports / cyb_reports CSV）
CREATE TABLE rp_filings (
  id              BIGSERIAL PRIMARY KEY,
  market          VARCHAR(10),            -- 'kcb' | 'cyb' | 'main'
  company         VARCHAR(255) NOT NULL,
  file_title      TEXT NOT NULL,
  file_type       VARCHAR(50),            -- 招股说明书/问询与回复/审计报告/法律意见书
  publish_date    DATE,
  file_size       VARCHAR(50),
  file_url        TEXT UNIQUE NOT NULL,   -- 直链上交所/深交所 CDN
  pdf_local_path  TEXT,                   -- MinIO 缓存路径
  raw_text        TEXT,                   -- pdftotext 输出
  text_extracted_at TIMESTAMP,
  created_at      TIMESTAMP DEFAULT now()
);
CREATE INDEX idx_rp_filings_company ON rp_filings(company);
CREATE INDEX idx_rp_filings_type ON rp_filings(file_type);
CREATE INDEX idx_rp_filings_date ON rp_filings(publish_date);

-- 上市文件字段抽取结果
CREATE TABLE rp_filing_extractions (
  id              BIGSERIAL PRIMARY KEY,
  filing_id       BIGINT REFERENCES rp_filings(id) ON DELETE CASCADE,
  schema_version  VARCHAR(20),            -- 'prospectus_v1' / 'inquiry_v1' 等
  extracted_data  JSONB,
  quality_score   FLOAT,
  extractor_model VARCHAR(50),
  extracted_at    TIMESTAMP DEFAULT now()
);
CREATE INDEX idx_rp_filing_ext_data ON rp_filing_extractions USING gin(extracted_data);

-- 自爬研报原始（B 线 P2 备用）
CREATE TABLE rp_raw_reports (
  id              UUID PRIMARY KEY,
  broker_id       INT,
  broker_name     VARCHAR(100),
  source_url      TEXT,
  pdf_hash        VARCHAR(64) UNIQUE,
  pdf_minio_path  TEXT,
  report_title    TEXT,
  report_date     DATE,
  language        VARCHAR(2),
  raw_text        TEXT,
  crawled_at      TIMESTAMP,
  extraction_status VARCHAR(20)
);

-- 研报字段抽取
CREATE TABLE rp_structured_reports (
  id                UUID PRIMARY KEY,
  raw_report_id     UUID REFERENCES rp_raw_reports(id),
  core_thesis       TEXT,
  business_logic    TEXT,
  valuation_assumptions JSONB,
  key_data_points   JSONB,
  risks             JSONB,
  target_price      VARCHAR,
  recommendation    VARCHAR,
  companies_covered TEXT[],
  sector            VARCHAR,
  extracted_at      TIMESTAMP,
  extractor_model   VARCHAR,
  quality_score     FLOAT
);

-- pgvector 索引
CREATE TABLE rp_embeddings (
  id              UUID PRIMARY KEY,
  ref_table       VARCHAR(50),  -- 'rp_filing_extractions' | 'rp_structured_reports'
  ref_id          BIGINT,
  embedding       vector(1024),
  indexed_at      TIMESTAMP DEFAULT now()
);
CREATE INDEX idx_rp_emb ON rp_embeddings USING ivfflat (embedding vector_cosine_ops);

-- 实时新闻
CREATE TABLE rp_news_flash (
  id              BIGSERIAL PRIMARY KEY,
  qmp_time        TIMESTAMP NOT NULL,
  content         TEXT NOT NULL,
  link            TEXT,
  hash            VARCHAR(64) UNIQUE,
  related_companies TEXT[],
  related_industries TEXT[],
  embedding       vector(1024),
  created_at      TIMESTAMP DEFAULT now()
);

-- 政策库
CREATE TABLE rp_policies (
  id              BIGSERIAL PRIMARY KEY,
  title           TEXT NOT NULL,
  source          VARCHAR(100),           -- 国务院/发改委/工信部
  publish_date    DATE,
  full_text       TEXT,
  related_industries TEXT[],
  policy_type     VARCHAR(50),
  embedding       vector(1024),
  created_at      TIMESTAMP DEFAULT now()
);

-- 产业链
CREATE TABLE rp_industry_chain (
  id              BIGSERIAL PRIMARY KEY,
  industry        VARCHAR(100) NOT NULL,
  level           INT,
  parent_id       BIGINT REFERENCES rp_industry_chain(id),
  description     TEXT,
  related_companies TEXT[],
  position        VARCHAR(20),            -- 上游/中游/下游
  created_at      TIMESTAMP DEFAULT now()
);

-- API 调用日志（计费 + 审计）
CREATE TABLE rp_api_logs (
  id              BIGSERIAL PRIMARY KEY,
  api_key_id      BIGINT,
  endpoint        VARCHAR(100),
  request_body    JSONB,
  data_sources    TEXT[],                 -- ['qmp_events','filings','tavily']
  response_size   INT,
  processing_ms   INT,
  cost_credits    FLOAT,
  status_code     INT,
  client_ip       INET,
  created_at      TIMESTAMP DEFAULT now()
);
CREATE INDEX idx_rp_logs_key ON rp_api_logs(api_key_id, created_at);

-- API Key 管理
CREATE TABLE rp_api_keys (
  id              BIGSERIAL PRIMARY KEY,
  key_hash        VARCHAR(64) UNIQUE NOT NULL,
  customer_name   VARCHAR(255),
  customer_email  VARCHAR(255),
  tier            VARCHAR(20),            -- free/hobby/starter/pro/enterprise/flagship
  monthly_credits INT,                    -- ★ 改为 credits 计费（不再是调用次数）
  used_credits    FLOAT DEFAULT 0,        -- 当月已用 credits（浮点，单端点消耗 0.5-50）
  reset_at        TIMESTAMP,
  expires_at      TIMESTAMP,
  active          BOOLEAN DEFAULT true,
  created_at      TIMESTAMP DEFAULT now()
);

-- Watchlist：客户订阅的赛道/公司/机构组合（M2）
CREATE TABLE rp_watchlist (
  id              BIGSERIAL PRIMARY KEY,
  api_key_id      BIGINT REFERENCES rp_api_keys(id) ON DELETE CASCADE,
  name            VARCHAR(255),           -- "我的具身智能监控"
  industries      TEXT[],                 -- ['具身智能','人形机器人']
  companies       TEXT[],                 -- ['宇树科技','智元机器人']
  investors       TEXT[],                 -- ['红杉中国','高瓴']
  filters         JSONB,                  -- 自定义过滤（轮次/估值带/地区等）
  notify_email    VARCHAR(255),           -- 摘要邮件目的地（可选）
  schedule_cron   VARCHAR(50),            -- 客户端 cron 表达式（参考用，非必填）
  created_at      TIMESTAMP DEFAULT now(),
  updated_at      TIMESTAMP DEFAULT now()
);
CREATE INDEX idx_rp_watch_key ON rp_watchlist(api_key_id);

-- Watchlist 摘要历史（缓存 + 客户回看）
CREATE TABLE rp_watchlist_digest (
  id              BIGSERIAL PRIMARY KEY,
  watchlist_id    BIGINT REFERENCES rp_watchlist(id) ON DELETE CASCADE,
  digest_data     JSONB,                  -- {events:[], news:[], filings:[], summary:"..."}
  digest_summary  TEXT,                   -- DeepSeek 生成的摘要文本
  events_count    INT,
  news_count      INT,
  filings_count   INT,
  generated_at    TIMESTAMP DEFAULT now()
);
CREATE INDEX idx_rp_digest_watch ON rp_watchlist_digest(watchlist_id, generated_at DESC);

-- ★ Research 异步任务表（v3 新增，支撑 Research 产品线）
CREATE TABLE rp_research_jobs (
  id              UUID PRIMARY KEY,        -- 客户拿到的 request_id
  api_key_id      BIGINT REFERENCES rp_api_keys(id),
  endpoint        VARCHAR(50),              -- research/sector | research/company | research/valuation
  input_payload   JSONB NOT NULL,           -- 完整请求体（input + output_schema + model 等）
  status          VARCHAR(20) NOT NULL,     -- pending | running | completed | failed
  model_used      VARCHAR(20),              -- mini | pro
  result          JSONB,                    -- 完成后的输出（按 output_schema 严格 JSON）
  citations       JSONB,                    -- citations 数组
  error           JSONB,                    -- 失败时的 error 对象
  warnings        JSONB,                    -- partial success warnings
  credits_charged FLOAT,                    -- 实际扣费（mini 20 / pro 50）
  steps_log       JSONB,                    -- SSE stream 步骤日志（["searching news", "extracting filings", ...]）
  started_at      TIMESTAMP,
  completed_at    TIMESTAMP,
  expires_at      TIMESTAMP DEFAULT (now() + interval '7 days'),  -- 7 天后清理
  created_at      TIMESTAMP DEFAULT now()
);
CREATE INDEX idx_rp_jobs_key ON rp_research_jobs(api_key_id, created_at DESC);
CREATE INDEX idx_rp_jobs_status ON rp_research_jobs(status, expires_at);

-- ★ Idempotency Keys（v3 新增，学 Stripe 防重复扣费）
CREATE TABLE rp_idempotency_keys (
  id              BIGSERIAL PRIMARY KEY,
  api_key_id      BIGINT REFERENCES rp_api_keys(id),
  idempotency_key VARCHAR(255) NOT NULL,
  request_hash    VARCHAR(64) NOT NULL,    -- sha256(method + path + body) 用于校验同 key 同请求
  endpoint        VARCHAR(100),
  response_status INT,
  response_body   JSONB,                    -- 缓存的原始响应，下次同 key 直接返回
  credits_charged FLOAT,
  created_at      TIMESTAMP DEFAULT now(),
  expires_at      TIMESTAMP DEFAULT (now() + interval '24 hours'),
  UNIQUE (api_key_id, idempotency_key)
);
CREATE INDEX idx_rp_idem_expires ON rp_idempotency_keys(expires_at);

-- ★ 实体别名 / 去重表（v3 新增，多源同一实体合并）
CREATE TABLE rp_entity_aliases (
  id              BIGSERIAL PRIMARY KEY,
  entity_type     VARCHAR(20) NOT NULL,     -- company | investor | industry
  canonical_id    BIGINT NOT NULL,          -- 主 ID（去重后保留的那个）
  alias_id        BIGINT,                   -- 别名 ID（被合并的那个，可选）
  alias_name      VARCHAR(500),             -- 别名（CATL / 宁德时代 / Contemporary Amperex）
  source          VARCHAR(50),              -- 来源（qmp / tavily / 上市文件 / 客户上报）
  confidence      FLOAT,                    -- 合并置信度（0-1，LLM 兜底时存）
  resolution_method VARCHAR(20),            -- exact_match | fuzzy | alias_table | llm
  created_at      TIMESTAMP DEFAULT now(),
  UNIQUE (entity_type, alias_name, source)
);
CREATE INDEX idx_rp_alias_canonical ON rp_entity_aliases(entity_type, canonical_id);
CREATE INDEX idx_rp_alias_lookup ON rp_entity_aliases(entity_type, alias_name);

-- ★ 技术路线图（v3 新增，industries/tech_roadmap 端点支撑）
CREATE TABLE rp_tech_roadmap (
  id              BIGSERIAL PRIMARY KEY,
  industry        VARCHAR(100) NOT NULL,
  technology_name VARCHAR(255) NOT NULL,
  parent_tech_id  BIGINT REFERENCES rp_tech_roadmap(id),
  description     TEXT,
  maturity_stage  VARCHAR(20),              -- emerging | growth | mature | declining
  representative_companies TEXT[],
  key_papers      JSONB,                    -- 核心论文/专利列表
  domestic_progress JSONB,                  -- 国产化进度
  source_reports  TEXT[],                   -- 来源研报 URL 列表
  created_at      TIMESTAMP DEFAULT now(),
  updated_at      TIMESTAMP DEFAULT now()
);
CREATE INDEX idx_rp_tech_industry ON rp_tech_roadmap(industry);

-- ★ rp_filings 加 source_type 字段（v3：研报/上市文件来源类型扩展）
-- 在已有 rp_filings 表基础上增加：
ALTER TABLE rp_filings ADD COLUMN IF NOT EXISTS source_type VARCHAR(30);
-- source_type 枚举：broker | consulting | association | corporate_research | vc | overseas_ib | media | exchange_official
-- 之前 broker_country 字段保留作为补充 metadata
```

### 3.3 缓存分层

| 层级 | 介质 | TTL | 用途 |
|---|---|---|---|
| L1 | Redis | 5 分钟 | 完整查询结果 |
| L2 | Redis | 24 小时 | 抽取后的字段 JSON |
| L3 | PostgreSQL | 永久 | rp_filing_extractions / rp_structured_reports |
| L4 | MinIO | 永久 | PDF 原文 |

---

## 四、A 线详细设计：4 渠道 API 路由器

### 4.1 渠道凭据与预算（v3 调整）

| 渠道 | 端点 | 鉴权 | 用途 | 月预算 |
|---|---|---|---|---|
| Tavily Search | `https://api.tavily.com/search` | Bearer | 中英文搜索（multi_source 主源）| ¥150 |
| Tavily Extract | `https://api.tavily.com/extract` | Bearer | URL → 全文（**替代 Firecrawl**）| ¥600 |
| Tavily Research | `https://api.tavily.com/research` | Bearer | 30-60s 异步深度报告 | ¥200 |
| Bocha Web | `https://api.bochaai.com/v1/web-search` | Bearer | 中文搜索（multi_source 中文源）| ¥250 |
| Serper | `https://google.serper.dev/search` | X-API-KEY | Google 海外搜索（multi_source 海外源）| ¥10 |
| ~~Firecrawl~~ | — | — | ❌ **不注册**（Tavily Extract 替代）| ¥0 |
| 阿里百炼 (V4 / GLM / Kimi) | `https://dashscope.aliyuncs.com/compatible-mode/v1` | Bearer | 字段抽取 + 多源合成 | 走 API 用量 |
| **合计** | | | | **~¥1,000-1,500/月**（实测 W1 约 ¥22 总开销）|

凭据已就位（VIA `find_tool` / `get_tool`）：
- `tavily-search` → tvly-dev-...
- `bocha` → sk-f5b...
- `serper` → 04ee15919c... (EDD v2 已记录)
- `aliyun-bailian` → sk-4325b80268... (主端点) + sk-sp-b0b4aab... (coding 端点)
- ~~FIRECRAWL_API_KEY~~ — 不需要

**multi_source 模式**（M1 已实装）：客户传 `multi_source: true` → 后端并发调 Tavily + Bocha + Serper → URL 去重 → rank score 加权排序 → partial 容错。代码：`backend/src/researchpipe_api/multi_search.py`

### 4.2 路由器决策算法

```
function route(query):
    场景识别（语言 + 地区 + 实时性）
    
    if 中文 A 股 + 非实时：       策略 = ChineseDeepResearch
    elif 海外英文：               策略 = EnglishCrossMarket  
    elif 跨市场：                 策略 = MultiMarket
    elif 实时新闻：               策略 = RealtimeNews
    else:                         策略 = Default
    
    return 策略.execute(query)
```

### 4.3 4 个场景策略

**ChineseDeepResearch（中文 A 股深度，占 70%）**
1. Bocha 搜索 → 拿 8-10 个 PDF 链接
2. 链接喂 Firecrawl 批量抓 PDF（并发 5）
3. DeepSeek V4 抽取（合并翻译/抽取一步）
4. 异步存自建库
- 单次成本：约 ¥0.09

**EnglishCrossMarket（海外英文中文化，占 20%）**
1. Serper 搜索 → 拿英文 PDF 链接
2. Tavily Extract（海外抓取更稳）
3. DeepSeek V4 一步翻译+抽取
- 单次成本：约 ¥0.25

**MultiMarket（跨市场对比，占 5%）**
1. Bocha + Serper 双发并发
2. Tavily search 主跑（中英都能）
3. Firecrawl 兜底失败链接
4. DeepSeek 抽取所有结果统一字段
- 单次成本：约 ¥0.50

**RealtimeNews（实时新闻验证，占 5%）**
1. Bocha + Serper news 双发
2. 不抓全文，只取 title + snippet + url
3. DeepSeek 快速摘要
- 单次成本：约 ¥0.005

### 4.4 错误处理与 Fallback 链

```
Bocha 失败 → Cloudsway（备胎，未启用）→ 返回 partial
Serper 失败 → Brave（备胎，未启用）→ 返回 partial
Tavily 抓取失败 → Firecrawl → Jina（充值后）→ 标记 unreachable
DeepSeek V4 失败 → DeepSeek V3.2 → Qwen3-235B → 返回 raw_content
```

**关键原则**：单家 API 故障不能引发 502，必须返回 partial 结果（可用字段 + error 标记）。

### 4.5 字段抽取 Prompt（核心）

```
SYSTEM: 你是投资研究字段抽取专家。从给定研报中精确提取以下字段，
        严格按 JSON schema 输出，不输出 schema 之外内容。
        如原文为英文，所有抽取字段直接输出中文（合并翻译步骤）。

USER: <PDF 全文文本，5K-30K 字符>

A: <严格符合 schema 的 JSON>
```

参数：
- temperature: 0.1
- response_format: `{"type": "json_object"}`
- 重试：JSON 解析失败 → 重试 1 次 → 仍失败标记 partial

---

## 五、B 线详细设计（v3 大幅瘦身）

> **v3 战略调整（2026-04-29）**：M1-M2 B 线只保 qmp 一级 deal 数据（events 26K + institutions 5K + valuations 2.8K，已通过 weekly_pipeline.py 在跑增量）。其他自爬 / 抓取流水线（kcb / cyb / news 上市文件首爬 + 17 子库 + 30 家券商自爬）**全部推到 M3+ 可选**。
>
> **当前 M1 实装**：所有研报 / 政策 / 产业链 / 专利 / 海外 deal / 实时新闻 → 走 A 线 Tavily Search + Tavily Extract + V4 实时套壳，**不预爬不落库**。
>
> 下面 5.1-5.5 章节描述的"上市文件首爬 + 30 家券商爬虫架构"作为 **M3+ 可选启动方案** 保留供参考。即使启动也只覆盖最有价值的 5-10% 文件，不做全量。

### 5.1 已就绪：scrape_qmp_reports.py（**M3+ 可选启动**）

**位置**：`/home/muye/qimingpian/scrape_qmp_reports.py`

**支持端点**（`--endpoint`）：
- `kcb` → `/Kcb/kcbCompanyReport`（科创板 22,659 份）
- `cyb` → `/Cyb/cybCompanyReport`（创业板 45,009 份）
- `news` → `/Information/qmpNewsList`（新闻 12.2 万）
- `product` → `/Product/productReportData`（产品库）

**特性**：
- 复用 `qimingpian_api.QimingpianAPI`（DES 解密 + GeeTest 检测）
- 速率控制（2-5s 间隔 + 每 20 次长休 30-60s + 每小时上限 50）
- 进度持久化（`output/<endpoint>_progress.json`），中断后断点续抓
- 去重机制（每个端点不同 dedup_field）
- 失败保护：GeeTest 触发 / 接口异常 → 立即保存进度并停止
- CSV 输出至 `output/<endpoint>.csv`，UTF-8 with BOM

**已通过冒烟测试**：
```
$ python scrape_qmp_reports.py --endpoint kcb --num 20 --max-pages 2 --reset
[INFO] kcb: total=22659, pages=1133, num/page=20
[PROGRESS] kcb page 1/2: +20 new
[PROGRESS] kcb page 2/2: +20 new
[DONE] kcb: 40 rows in /home/muye/qimingpian/output/kcb.csv
```

### 5.2 cron 调度集成

在现有 crontab 基础上追加：

```cron
# === ResearchPipe 抓取 ===
# 每周日 11:30 - 错峰原 weekly_pipeline 后跑上市文件抓取
30 11 * * 0 cd ~/qimingpian && .venv/bin/python scrape_qmp_reports.py --endpoint kcb --num 50 >> logs/rp_kcb.log 2>&1
0  12 * * 0 cd ~/qimingpian && .venv/bin/python scrape_qmp_reports.py --endpoint cyb --num 50 >> logs/rp_cyb.log 2>&1

# 每天 8:00 - 新闻流增量
0 8 * * * cd ~/qimingpian && .venv/bin/python scrape_qmp_reports.py --endpoint news --num 50 --max-pages 20 >> logs/rp_news.log 2>&1

# 每天 8:30 - 产品库增量
30 8 * * * cd ~/qimingpian && .venv/bin/python scrape_qmp_reports.py --endpoint product --num 50 --max-pages 10 >> logs/rp_product.log 2>&1
```

**首次全量预估**（按 50/小时节流）：
- kcb 22,659 / 50 = ~454 页 → 9 周日（每周 8 小时窗口约 50 页）
- cyb 45,009 / 50 = ~900 页 → 18 周日
- **现实做法**：首次开放更大窗口（周日跑 24 小时），4-6 周完成全量；之后增量每周仅几百份

### 5.3 PDF 下载 + 文本化（M2 接入）

抓取脚本只拉**索引 metadata**（CSV 含 file_url）。PDF 实际下载由独立 Worker 异步执行：

```
Worker 流程:
  rp_filings WHERE pdf_local_path IS NULL ORDER BY publish_date DESC
    → curl -O file_url → MinIO 存储
    → pdftotext -layout → rp_filings.raw_text
    → 触发抽取 Worker
```

**关键点**：file_url 全是上交所/深交所官方 CDN，无反爬，下载稳定。

### 5.4 ~~P2~~ **M5+** 可选：30 家券商爬虫架构（**实测全部反爬**）

> **2026-04-29 实证**：30 家券商主页 + 8 公开站点 audit，**0 家可走 naive HTTP 直接爬**（0 easy / 12 moderate / 26 hard）。100% 需要 Playwright 全家桶 + 反爬代理 + 验证码处理。单家从"能爬"到"稳定爬"工时 1-2 周，30 家全做 ~半年人年。
>
> **决策**：M1-M4 完全跳过自爬，所有研报走 A 线 Tavily Search/Extract 套壳。M5+ 客户付费要求专属源 / 第三方覆盖不足时再考虑启动。下面架构作为参考保留：


```
┌────────────────────────────────────────────┐
│       调度器（每日凌晨 2:00 启动）          │
│  - 读取 enabled_brokers 列表               │
│  - 为每家创建独立 Job                       │
└────────────────┬───────────────────────────┘
                 │
       ┌─────────┴─────────┐
       │                   │
  ┌────▼────┐         ┌────▼────┐
  │ Worker 1 │  ...    │ Worker N │
  │ 中信证券 │         │ 申万宏源 │
  └────┬────┘         └────┬────┘
       │                   │
  ┌────▼─────────────────────────┐
  │  Playwright + 反爬策略        │
  │  - User-Agent 轮换            │
  │  - IP 池（如需要）            │
  │  - 请求间隔 3-10s             │
  │  - 失败重试 3 次              │
  └────┬─────────────────────────┘
       │
  ┌────▼─────────────────────────┐
  │  PDF 下载 + SHA256 哈希去重    │
  │  → MinIO 存储                  │
  │  → pdftotext -layout 转文本    │
  │  → 入 rp_raw_reports           │
  │  → 触发抽取 Worker             │
  └─────────────────────────────┘
```

**温和爬虫原则**：
- 请求间隔 ≥ 3 秒
- 每家券商每日上限 200 次请求
- 总并发 ≤ 5
- robots.txt 遵守
- 失败 3 次该 URL 进入冷却 24h

**遇到反爬升级时的应对优先级**：
1. 加大请求间隔
2. 切换 IP（云函数代理 / 自建 IP 池）
3. 降级到 Playwright headful 模式
4. 仍失败 → 该数据源标记为"不可用"，路由器自动 fallback 到 API 渠道

### 5.5 法律合规边界（爬虫硬编码）

- ✅ Whitelist 模式：只爬列入 `enabled_brokers` 表的官网域名
- ❌ 永远不爬慧博、东方财富、新浪财经、同花顺、Wind 任何子页
- ✅ 每条入库强制保留 `source_url`，对外展示带"源链接"
- ✅ 法务下架接口：人工触发后立即从对外查询结果中过滤指定 broker
- ✅ 用户协议明确：服务为"指引性聚合"，不替代原文

---

## 六、字段抽取流水线

### 6.1 上市文件按 file_type 分流（5 套 schema）

```
- 招股说明书 (prospectus_v1):
    发行人基本情况 / 主营业务 / 核心技术 / 财务数据 5 年 / 同行业可比公司
    / 募投项目 / 实控人 / 重大风险

- 问询与回复 (inquiry_v1):
    问题分类 / 监管关注点 / 公司答复要点 / 数据修正 / 风险提示

- 发行保荐书 (sponsor_v1):
    保荐机构尽调结论 / 财务核查关键发现 / 推荐意见

- 审计报告 (audit_v1):
    审计意见类型 / 关键审计事项 / 财务异常项

- 法律意见书 (legal_v1):
    法律合规情况 / 重大诉讼 / 关联交易 / 实控人变更
```

### 6.2 字段 schema 详细定义

参见 PRD 第 6.4 节。补充工程细节：

**valuation_assumptions（jsonb）**：
```json
{
  "method": "DCF" | "PE" | "PB" | "EV/EBITDA" | "其他",
  "key_inputs": {
    "discount_rate": "10%",
    "terminal_growth": "3%",
    "target_pe": "25x"
  },
  "scenario": "base" | "bull" | "bear",
  "raw_text": "<原文相关段落>"
}
```

**key_data_points**：
```json
[{
  "metric": "市场规模",
  "value": "1500亿",
  "year": 2026,
  "source": "公司年报 / 行业协会 / 估算",
  "raw_text": "..."
}]
```

**risks**：
```json
[{
  "category": "宏观/政策/技术/竞争/财务/其他",
  "description": "...",
  "severity": "high" | "medium" | "low",
  "raw_text": "..."
}]
```

### 6.3 抽取统一参数

```
model:           deepseek-v4 (DashScope)
fallback model:  deepseek-v3.2 (LanYun) → qwen3-235b
temperature:     0.1
response_format: {"type": "json_object"}
max_tokens:      4096
prompt 模板:     基于 file_type 路由到对应 schema prompt
重试:            JSON 解析失败 → 重试 1 次 → 标记 partial
```

### 6.4 抽取质量评分

每条入库记录由 Worker 自动给 quality_score（0-1）：

| 评分维度 | 权重 |
|---|---|
| 必填字段完整度 | 0.4 |
| 字段长度合理性（非过短/过长）| 0.2 |
| 关键数据点数量 ≥ 3 | 0.2 |
| 风险点数量 ≥ 2 | 0.2 |

quality_score < 0.6 标记 `needs_review`，定期人工 spot check。

### 6.5 单文档成本预估

- 招股说明书 ~50-100 页 = 30-50K token in
- 提取 ~3K token out
- DeepSeek V4 单价：¥0.5/M-in + ¥1.5/M-out
- 单份成本：¥0.02-0.04
- **67K 全量首次成本：¥1,500-2,500**（一次性）
- **之后每周增量 ~500 份：¥15-25/周**

---

## 七、API 服务层

### 7.1 在现有 FastAPI 上扩展（按 4 产品线重组）

**入口**：`/home/muye/ventureos/QMPData/api/main.py`（已运行 99 天）

**新增路由文件**（按 PRD v3 6.1 的 4 产品线对齐）：

```
api/routes/rp/
  ├─ __init__.py                  # 总注册
  │
  ├─ search/                      # 产品线 1：Search（同步秒级）
  │   ├─ search.py                 # POST /v1/search (type=web/news/research/policy/filing)
  │   ├─ extract.py                # POST /v1/extract（URL → 全文）
  │   ├─ extract_research.py       # POST /v1/extract/research ★
  │   ├─ extract_filing.py         # POST /v1/extract/filing ★
  │   ├─ extract_batch.py          # POST /v1/extract/batch
  │   └─ jobs.py                   # GET /v1/jobs/{id}（共用 batch + research）
  │
  ├─ research/                    # 产品线 2：Research（异步多步）
  │   ├─ sector.py                 # POST /v1/research/sector ★
  │   ├─ company.py                # POST /v1/research/company ★
  │   └─ valuation.py              # POST /v1/research/valuation
  │
  ├─ data/                        # 产品线 3：Data（38 端点）
  │   ├─ companies.py              # 6 端点（含 founders deep mode）
  │   ├─ investors.py              # 5 端点（含 exits）
  │   ├─ deals.py                  # 5 端点（含 co_investors）
  │   ├─ industries.py             # 9 端点（含 tech_roadmap / key_technologies / maturity）
  │   ├─ technologies.py           # 1 端点（POST /v1/technologies/compare）
  │   ├─ valuations.py             # 4 端点（含 distribution）
  │   ├─ filings.py                # 5 端点
  │   ├─ news.py                   # 2 端点
  │   ├─ events.py                 # 1 端点（events/timeline）
  │   └─ screen.py                 # 1 端点
  │
  ├─ watch/                       # 产品线 4：Watch
  │   ├─ create.py                 # POST /v1/watch/create
  │   └─ digest.py                 # GET /v1/watch/{id}/digest
  │
  ├─ account/                     # 账户管理
  │   ├─ me.py
  │   ├─ usage.py
  │   └─ billing.py
  │
  └─ admin/                       # 内部运营
      └─ takedown.py

api/middleware/
  ├─ auth.py                      # API Key 鉴权（学 Anthropic）
  ├─ credits.py                   # Credits 计费（@credits_cost decorator）
  ├─ rate_limit.py                # Token bucket（60/min sustained + burst 10）
  ├─ idempotency.py               # ★ Idempotency-Key 处理（学 Stripe）
  ├─ error_handler.py             # ★ 统一错误格式 + hint_for_agent
  ├─ partial_success.py           # ★ partial warnings 收集器
  └─ versioning.py                # /v1/ 路径版本号

api/orchestrator/
  ├─ search_router.py             # Search 产品线 4 渠道路由（Tavily/Bocha/Serper/Firecrawl）
  ├─ extractor.py                 # DeepSeek V4 抽取
  ├─ entity_resolver.py           # ★ 实体去重（fuzzy + 别名 + LLM 兜底）
  ├─ field_merger.py               # ★ 多源字段冲突解决（硬编码优先级 + alternatives）
  ├─ research_composer/            # Research 产品线编排
  │   ├─ sector.py                 # research/sector 多步编排
  │   ├─ company.py                # research/company 多步编排
  │   └─ valuation.py
  ├─ schema_validator.py           # ★ output_schema 校验 + 严格输出
  └─ citation_builder.py           # ★ citations 数组构建（按 format: numbered/apa/chicago）

api/workers/
  ├─ research_worker.py            # ★ BullMQ worker 处理 research jobs
  ├─ extraction_worker.py          # 上市文件抽取 worker
  ├─ scrape_worker.py              # 抓取 worker
  └─ sse_publisher.py              # ★ Redis pubsub → SSE 推送
```

### 7.2 鉴权 + Credits + Idempotency 中间件链

请求处理链（FastAPI middleware stack）：

```
HTTP 请求
  → versioning（/v1/ 路径校验）
  → auth（API Key 鉴权 + 加载 tier / credits）
  → idempotency（如有 Idempotency-Key header，查缓存 → 命中直接返）
  → rate_limit（token bucket：sustained 60/min + burst 10）
  → credits_cost decorator（按端点扣 credits）
  → 业务路由（routes/rp/...）
  → partial_success 收集器（合并 multi-source warnings）
  → error_handler（统一错误格式 + hint_for_agent）
  → 响应 header（Cache-Control / X-RateLimit-* / X-Credits-*）
```

```python
# api/middleware/auth.py
async def verify_api_key(x_api_key: str = Header(...)):
    key = await db.fetch_one(
        "SELECT * FROM rp_api_keys WHERE key_hash = $1 AND active",
        sha256(x_api_key))
    if not key:
        raise APIError(401, "auth_invalid", "Invalid API key",
                       hint_for_agent="Verify the API key is correct and active.")
    return key

# api/middleware/credits.py
@router.post("/v1/extract/research")
@credits_cost(5)  # 5 credits per call
async def extract_research(...):
    ...

async def credits_middleware(request, call_next):
    api_key = request.state.api_key
    cost = ENDPOINT_CREDITS.get(request.url.path, 1)
    if api_key.used_credits + cost > api_key.monthly_credits:
        raise APIError(402, "credits_exceeded",
                       f"Monthly credits exceeded ({api_key.monthly_credits})",
                       hint_for_agent="Wait until reset_at or upgrade tier.",
                       documentation_url="https://docs.researchpipe.com/errors/credits")
    response = await call_next(request)
    if response.status_code < 500:
        await charge_credits(api_key.id, cost)
    return response

# api/middleware/idempotency.py（学 Stripe）
async def idempotency_middleware(request, call_next):
    idem_key = request.headers.get("Idempotency-Key")
    if not idem_key:
        return await call_next(request)
    request_hash = sha256(f"{request.method}{request.url.path}{await request.body()}")
    existing = await db.fetch_one(
        "SELECT response_body, response_status FROM rp_idempotency_keys "
        "WHERE api_key_id=$1 AND idempotency_key=$2 AND expires_at > now()",
        request.state.api_key.id, idem_key)
    if existing:
        if existing['request_hash'] != request_hash:
            raise APIError(409, "idempotency_conflict",
                           "Same idempotency key used with different request body",
                           hint_for_agent="Use a different Idempotency-Key for new request.")
        return JSONResponse(content=existing['response_body'],
                            status_code=existing['response_status'])
    response = await call_next(request)
    if response.status_code < 500:
        await db.execute("INSERT INTO rp_idempotency_keys ...")
    return response
```

### 7.3 错误处理 + Partial Warnings 规范

**APIError 类**（统一抛出）：

```python
# api/middleware/error_handler.py
class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str,
                 hint_for_agent: str = "", retry_after_seconds: int = None,
                 documentation_url: str = ""):
        self.status_code = status_code
        self.error = {
            "code": code,                          # 英文 enum，给 LLM 看
            "message": message,                     # 中文，给人看
            "hint_for_agent": hint_for_agent,       # 英文，给 LLM 决策
            "documentation_url": documentation_url
        }
        if retry_after_seconds:
            self.error["retry_after_seconds"] = retry_after_seconds

# 错误码枚举（在 docs 单独章节列出）
ERROR_CODES = {
    "auth_invalid": (401, "Verify the API key is correct and active."),
    "credits_exceeded": (402, "Wait until reset_at or upgrade tier."),
    "rate_limit_exceeded": (429, "Wait retry_after_seconds and retry. Reduce frequency or use Idempotency-Key."),
    "validation_failed": (400, "Check request body matches schema."),
    "resource_not_found": (404, "Verify the resource ID exists. Use search endpoints to find valid IDs."),
    "upstream_timeout": (504, "Retry after a brief delay; results may be partial."),
    "internal_error": (500, "Retry with exponential backoff. Contact support if persists."),
    "idempotency_conflict": (409, "Use a different Idempotency-Key for new request body."),
}
```

**Partial Success 机制**：

```python
# api/middleware/partial_success.py
class PartialContext:
    def __init__(self):
        self.warnings = []
    def add_warning(self, code: str, source: str, message: str, hint: str):
        self.warnings.append({
            "code": code, "source": source,
            "message": message, "hint_for_agent": hint
        })

# 端点内部使用：
@router.get("/v1/research/sector/{industry}")
async def sector_research(industry: str, ctx: PartialContext = Depends()):
    try:
        tavily_data = await fetch_tavily(...)
    except UpstreamTimeout:
        ctx.add_warning(
            "data_source_unavailable", "tavily",
            "Tavily timeout, fallback to Bocha used",
            "Results may be less complete. Retry might get more sources."
        )
        tavily_data = await fetch_bocha_fallback(...)
    return {"results": ..., "metadata": {"warnings": ctx.warnings, "partial": bool(ctx.warnings)}}

# Warning code 枚举
WARNING_CODES = [
    "data_source_unavailable",   # 上游某 API 不可用
    "partial_result_due_timeout", # 部分结果因超时
    "cache_stale",                # 返回了陈旧缓存
    "quality_score_low",          # 抽取质量低
    "fallback_model_used",        # 用了 fallback LLM 模型
    "entity_disambiguation_required",  # 模糊匹配出多个 entity
]
```

### 7.4 Research 异步实现（核心创新）

`POST /v1/research/sector` —— 学 Tavily Research 的异步 + SSE 模式。

**架构**：

```
┌─────────────────────────────────────────────────────────────┐
│ 客户调 POST /v1/research/sector                                │
└──────────────────────┬──────────────────────────────────────┘
                       │ stream=false 默认
                       ↓
┌──────────────────────────────────────────────────────────────┐
│ FastAPI handler:                                              │
│ 1. 校验 output_schema（如果传了）                              │
│ 2. 落库 rp_research_jobs（status=pending）                    │
│ 3. 推 BullMQ queue                                           │
│ 4. 立即返回 {request_id, status: "pending"}                   │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│ ResearchWorker（BullMQ 后台 worker）                           │
│ 1. 从 queue 拉 job                                            │
│ 2. 更新 status=running                                        │
│ 3. 多步 orchestration：                                        │
│    - 并发拉 8 类数据（asyncio.gather）                         │
│    - DeepSeek V4 多次调用合成                                  │
│    - schema_validator 校验输出                                 │
│    - citation_builder 构建 citations                           │
│    - 每步通过 Redis pubsub 发 progress 事件                   │
│ 4. 完成后 result 落库 rp_research_jobs（status=completed）   │
│ 5. 扣 credits（mini=20 / pro=50）                            │
└──────────────────────────────────────────────────────────────┘

stream=true 时:
  客户调 POST + 持有连接
  FastAPI 订阅 Redis pubsub channel `research:{request_id}`
  Worker 推 progress → SSE 实时推给客户
```

```python
# api/routes/rp/research/sector.py
@router.post("/v1/research/sector")
@credits_cost_dynamic  # 按 model 动态扣 credits
async def research_sector(
    body: ResearchSectorRequest,
    api_key: APIKey = Depends(verify_api_key),
):
    # 校验 output_schema
    if body.output_schema:
        schema_validator.validate(body.output_schema)

    request_id = uuid4()
    await db.execute(
        "INSERT INTO rp_research_jobs (id, api_key_id, endpoint, input_payload, status, model_used) "
        "VALUES ($1, $2, 'research/sector', $3, 'pending', $4)",
        request_id, api_key.id, body.dict(), body.model
    )

    # 推 BullMQ
    await research_queue.add("sector", {"request_id": str(request_id)})

    if body.stream:
        # SSE 流式：订阅 pubsub
        return StreamingResponse(
            stream_research_progress(request_id),
            media_type="text/event-stream"
        )
    else:
        # 默认异步：立即返回 request_id
        return JSONResponse(
            status_code=201,
            content={
                "request_id": str(request_id),
                "status": "pending",
                "model": body.model,
                "estimated_seconds": 45 if body.model == "pro" else 20
            }
        )

# api/routes/rp/search/jobs.py
@router.get("/v1/jobs/{job_id}")
async def get_job(job_id: UUID, api_key: APIKey = Depends(verify_api_key)):
    job = await db.fetch_one(
        "SELECT * FROM rp_research_jobs WHERE id=$1 AND api_key_id=$2",
        job_id, api_key.id
    )
    if not job:
        raise APIError(404, "resource_not_found", "Job not found",
                       hint_for_agent="Verify the request_id is correct or check expires_at.")
    return {
        "request_id": job_id,
        "status": job['status'],
        "result": job['result'],
        "citations": job['citations'],
        "error": job['error'],
        "metadata": {
            "warnings": job['warnings'],
            "credits_charged": job['credits_charged'],
            "model_used": job['model_used'],
            "started_at": job['started_at'],
            "completed_at": job['completed_at']
        }
    }
```

**SSE 流式实现**（学 Tavily Research）：

```python
async def stream_research_progress(request_id: UUID):
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"research:{request_id}")

    yield f"event: started\ndata: {json.dumps({'request_id': str(request_id)})}\n\n"

    async for msg in pubsub.listen():
        if msg['type'] != 'message':
            continue
        data = json.loads(msg['data'])
        event_type = data.get('event')  # step | completed | failed
        yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        if event_type in ('completed', 'failed'):
            break
    await pubsub.unsubscribe()
```

### 7.5 实体去重 + 字段冲突解决

```python
# api/orchestrator/entity_resolver.py
class EntityResolver:
    async def resolve(self, entity_type: str, name: str, source: str) -> int:
        # 1. 别名表查询（最快）
        alias = await db.fetch_one(
            "SELECT canonical_id FROM rp_entity_aliases "
            "WHERE entity_type=$1 AND alias_name=$2",
            entity_type, name
        )
        if alias:
            return alias['canonical_id']

        # 2. Fuzzy match（rapidfuzz score >= 90）
        candidates = await fuzzy_match(entity_type, name)
        if candidates and candidates[0].score >= 90:
            await self._record_alias(entity_type, name, candidates[0].id, source, "fuzzy", 0.9)
            return candidates[0].id

        # 3. LLM 兜底（模棱两可）
        if candidates and 70 <= candidates[0].score < 90:
            decision = await llm_judge(name, candidates[:3])
            if decision.is_match:
                await self._record_alias(entity_type, name, decision.matched_id, source, "llm", decision.confidence)
                return decision.matched_id

        # 4. 创建新实体
        new_id = await db.execute("INSERT INTO companies ...")
        await self._record_alias(entity_type, name, new_id, source, "exact_match", 1.0)
        return new_id

# api/orchestrator/field_merger.py
SOURCE_PRIORITY = {
    "qmp_filing": 100, "qmp_official": 90, "qmp_event": 80,
    "research_report": 70, "tavily": 50, "bocha": 40, "serper": 30
}

def merge_field(values: list[dict]) -> dict:
    """values = [{'value': 1000, 'source': 'qmp_event', 'date': ...}, ...]"""
    if not values:
        return None
    sorted_values = sorted(values, key=lambda x: -SOURCE_PRIORITY.get(x['source'], 0))
    primary = sorted_values[0]
    alternatives = sorted_values[1:] if len(sorted_values) > 1 else []
    return {
        "value": primary['value'],
        "_source": primary['source'],
        "_alternatives": alternatives  # 仅在 metadata.alternatives 时展开
    }
```

### 7.6 旗舰端点 research/sector 实现细节

`POST /v1/research/sector` —— 异步多步 LLM 编排，输出按 `output_schema` 严格 JSON。

**Worker 内部步骤**（`api/workers/research_worker.py` 处理 BullMQ job）：

```
1. 缓存查询：Redis 24h 内 same (input + output_schema_hash + model) snapshot → 命中直接返回
   pubsub: {event: "started"} → {event: "completed", result: ...}

2. 并发拉 8 类数据（asyncio.gather）：
   - qmp_data.events（行业 + time_range 过滤）
   - qmp_data.valuations
   - qmp_data.institutions（行业偏好匹配）
   - rp_filings（最近 IPO 文件 + 抽取字段）
   - rp_news_flash（向量检索 + 时间）
   - rp_policies（政策库 + impact_assessment）
   - rp_industry_chain（产业链）
   - rp_tech_roadmap（v3 新增）
   - 海外：Tavily 搜索补位（如 regions 含 us/global）
   - 多源研报：按 source_types 过滤抓取
   pubsub: {event: "step", step: "fetching data", progress: 0.3}

3. 实体去重：调 EntityResolver 把多源 entity 合并到 canonical_id
   pubsub: {event: "step", step: "resolving entities", progress: 0.5}

4. DeepSeek V4 多步合成：
   - mini 模型：1 次 LLM 调用合成所有字段
   - pro 模型：2-3 次 LLM 调用，每次聚焦不同字段集合
   pubsub: {event: "step", step: "llm synthesis", progress: 0.7}

5. Schema 校验 + 严格输出：
   - 如果 output_schema 是 null，走默认 16 字段 schema
   - 如果客户传了 output_schema，schema_validator 校验输出严格符合
   - 不符合时让 LLM 重试一次
   pubsub: {event: "step", step: "validating schema", progress: 0.9}

6. Citations 构建：
   - 按 citation_format（numbered/apa/chicago）组织
   - 每条 citation 含 {source_url, filing_id, quote, accessed_at}

7. 归一化输出 + 写缓存（24h TTL）+ 落库 rp_research_jobs.result
   pubsub: {event: "completed", result: {...}}
```

**性能目标**：
- mini model: P50 < 15s, P95 < 30s, 单次成本 ¥0.15-0.25
- pro model: P50 < 30s, P95 < 60s, 单次成本 ¥0.40-0.60
- cache hit: < 100ms

**research/company 同样 pattern**，多步骤 + output_schema + citations。

### 7.7 数据新鲜度策略 + freshness 标注

每个 entity 响应中带 `_meta`：

```json
{
  "company": {
    "name": "宁德时代",
    "_meta": {
      "last_updated_at": "2026-04-25T10:00:00Z",
      "data_age_days": 3,
      "freshness_status": "fresh",
      "next_refresh_eta": "2026-05-02"
    }
  }
}
```

**freshness_status 阈值**（按数据类型）：

| 数据类型 | fresh | stale | outdated |
|---|---|---|---|
| 实时新闻 | < 6h | 6h-24h | > 24h |
| 一级 deal | < 7d | 7d-30d | > 30d |
| 上市文件 metadata | < 3d | 3d-30d | > 30d |
| 上市文件抽取字段 | < 30d | 30d-180d | > 180d |
| 研报 | < 24h | 24h-7d | > 7d |
| 政策 | < 7d | 7d-90d | > 90d |
| 公司画像 | < 30d | 30d-180d | > 180d |
| 估值数据 | < 30d | 30d-180d | > 180d |
| 产业链 | < 90d | 90d-365d | > 365d |
| 专利 | < 90d | 不标 | 不标 |

**陈旧数据策略**：照常返回 + 标 stale，**不强制触发实时刷新**（避免突发 API 成本爆炸 + agent 自决策）。客户传 `min_freshness=fresh` 才强制实时刷新（贵）。

### 7.8 Cache 策略 + Rate Limit + Response Headers

**缓存 TTL 按产品线分**：

| 产品线 | TTL | 实现 |
|---|---|---|
| Search 实时类（news / web）| 5 min | Redis SET EX 300 |
| Search research / extract | 24h | Redis SET EX 86400 |
| Research（sector / company / valuation）| 24h | 同 input + output_schema_hash + model 缓存 |
| Data 列表查询 | 1h | Redis SET EX 3600 |
| Data 单查询（{id}）| 5 min | Redis SET EX 300 |
| Watch digest | 不缓存 | 每次重算（cron 友好）|

**Rate limit 实现**（token bucket）：

```python
# api/middleware/rate_limit.py
class TokenBucket:
    def __init__(self, capacity=10, refill_per_sec=1):  # 60/min sustained = 1/sec refill, burst 10
        self.capacity = capacity
        self.refill_per_sec = refill_per_sec

    async def consume(self, key: str) -> tuple[bool, int]:
        # Lua atomic operation in Redis
        # 返回 (allowed, retry_after_sec)
        ...

async def rate_limit_middleware(request, call_next):
    api_key = request.state.api_key
    bucket = TokenBucket(capacity=10, refill_per_sec=1)
    allowed, retry_after = await bucket.consume(f"rl:{api_key.id}")
    if not allowed:
        raise APIError(429, "rate_limit_exceeded",
                       f"60 req/min limit reached. Retry after {retry_after}s.",
                       hint_for_agent=f"Wait {retry_after}s and retry the same request.",
                       retry_after_seconds=retry_after)
    response = await call_next(request)
    # 加响应 header
    response.headers["X-RateLimit-Limit"] = "60"
    response.headers["X-RateLimit-Remaining"] = str(bucket.remaining)
    response.headers["X-RateLimit-Reset"] = str(bucket.reset_at)
    return response
```

**响应 Header 规范**（每个端点必带）：

```
Cache-Control: max-age=300            # 客户端 SDK 知道缓存多久
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 47
X-RateLimit-Reset: 1714299600
X-Credits-Cost: 5                     # 本次扣的 credits
X-Credits-Remaining: 1840             # 本月剩余
X-Request-Id: 7a8b9c0d-...            # 客户报问题时带这个
```

### 7.9 Schema 演进 + API 版本控制

- **加字段永远兼容**：所有 v1 端点的响应 schema 持续追加字段，不删不改类型
- **改字段类型 / 删字段**：必须走 v2，路径 `/v2/...`
- **v1 至少保留 12 个月** after v2 上线
- **必填字段全输出**：value 为 null 也输出 `null`，不省略 key（agent 不用写 if-exists 判断）

```python
# 响应序列化模式：
class CompanyResponse(BaseModel):
    name: str
    sector: Optional[str] = None
    revenue_2025: Optional[float] = None
    # 即使所有字段都 null 也全部输出，agent 拿到稳定 schema

    class Config:
        # 关键：null 字段也包含在 JSON 里
        exclude_none = False
```

### 7.10 Credits 计费中间件（替代原 quota）

**原理**：每个端点在路由 decorator 上声明 `@credits_cost(N)`，请求成功后扣除。失败（5xx）不扣。

```python
# api/middleware/credits.py
@router.post("/v1/extract/research")
@credits_cost(5)  # 5 credits per call
async def extract_research(...):
    ...

# 中间件实现
async def credits_middleware(request, call_next):
    api_key = await verify_api_key(request)
    cost = get_endpoint_cost(request.url.path)
    if api_key.used_credits + cost > api_key.monthly_credits:
        raise HTTPException(402, "Credits exceeded, please upgrade")
    response = await call_next(request)
    if response.status_code < 500:
        await charge_credits(api_key.id, cost)
    return response
```

**端点 → Credits 映射**（统一在 `api/config/credits.py`）：
```python
ENDPOINT_CREDITS = {
    "POST /v1/search":               1,
    "POST /v1/extract":              2,
    "POST /v1/extract/research":     5,
    "POST /v1/extract/filing":       3,
    "POST /v1/companies/search":     0.5,
    "GET  /v1/companies/{id}":       0.5,
    # ... 共 40 个端点
    "GET  /v1/sector-snapshot/{}":   50,
    "POST /v1/dd/company":           30,
}
```

### 7.11 Python SDK 设计

**包名**：`researchpipe`（PyPI 注册）

**目录结构**：
```
researchpipe-python/
├─ researchpipe/
│   ├─ __init__.py
│   ├─ client.py              # Client 主类
│   ├─ resources/
│   │   ├─ search.py          # client.search.web/news/research
│   │   ├─ extract.py         # client.extract.research/filing
│   │   ├─ companies.py       # client.companies.search/get/peers
│   │   ├─ investors.py
│   │   ├─ industries.py
│   │   ├─ valuations.py
│   │   ├─ filings.py
│   │   ├─ news.py
│   │   ├─ flagship.py        # sector_snapshot / dd_company / screen / watch
│   │   └─ account.py
│   ├─ models.py              # pydantic 数据模型（与 API schema 对齐）
│   └─ exceptions.py
├─ tests/
└─ pyproject.toml
```

**使用示例（学 Anthropic SDK 风格）**：
```python
from researchpipe import Client

client = Client(api_key="rp-xxx")  # 也支持环境变量 RESEARCHPIPE_API_KEY

# 1. 研报抽取（A 线核心）
result = client.extract.research(
    query="半导体设备 国产化",
    time_range="30d",
    regions=["a-share", "hk"],
    max_results=20
)
for r in result.results:
    print(r.broker, r.core_thesis, r.target_price)

# 2. 公司链式调用（学 Stripe SDK）
company = client.companies.get("xx-id")
deals = client.companies.deals("xx-id")
peers = client.companies.peers("xx-id")

# 3. 旗舰
snapshot = client.sector_snapshot("具身智能", time_range="24m")

# 4. Async 版本
async with client.async_client() as c:
    snapshot = await c.sector_snapshot("具身智能")
```

**关键设计**：
- 同步 + 异步双版本（httpx 同时支持）
- 自动重试（指数退避，仅对 5xx 和 429）
- 类型严格（pydantic v2 + mypy strict）
- 错误清晰：`AuthenticationError` / `CreditsExceededError` / `RateLimitError` / `ServerError`

### 7.12 Node SDK 设计

**包名**：`@researchpipe/sdk`（npm 注册）

**目录结构**：基本镜像 Python SDK，TS + axios + zod

**使用示例**：
```typescript
import { ResearchPipe } from '@researchpipe/sdk';

const client = new ResearchPipe({ apiKey: process.env.RESEARCHPIPE_API_KEY });

const result = await client.extract.research({
  query: '半导体设备 国产化',
  timeRange: '30d',
  regions: ['a-share', 'hk'],
});

const snapshot = await client.sectorSnapshot('具身智能', { timeRange: '24m' });
```

### 7.13 MCP Server 设计（v3：8 个智能 Tool 取代旧 25 个）

**包名**：`@researchpipe/mcp-server`（npm 注册，`npx @researchpipe/mcp-server` 或 `uvx researchpipe-mcp` 即用）

**实现**：基于 `@modelcontextprotocol/sdk`，TypeScript

**安装方式**（Claude Desktop / Cursor / Cline 通用）：
```json
// claude_desktop_config.json
{
  "mcpServers": {
    "researchpipe": {
      "command": "npx",
      "args": ["@researchpipe/mcp-server"],
      "env": {
        "RESEARCHPIPE_API_KEY": "rp-xxx"
      }
    }
  }
}
```

**v3 决策：8 个中粒度智能 Tool（取代 v2 的 25 个细 tool）**

**Why**：Claude Desktop 当 tool 数量超过 10-15 个时选 tool 准确率下降；8 个中粒度 tool 是甜蜜点（按"实体 + 任务"分组）。

**8 个 MCP Tool（按 4 产品线对齐）**：

| # | Tool 名 | 内部 orchestrate | 说明 |
|---|---|---|---|
| 1 | `researchpipe_search` | Search 产品线（type=web/news/research/policy/filing 5 in 1）| 通用搜索 |
| 2 | `researchpipe_extract` | URL/research/filing 三个 extract 合并 | 单 URL 或字段抽取 |
| 3 | `researchpipe_research_sector` | research/sector（异步，内部 poll）| 赛道全景研究 |
| 4 | `researchpipe_research_company` | research/company（异步，内部 poll）| 公司尽调研究 |
| 5 | `researchpipe_company_data` | companies search/get/peers/deals/news/founders（6 in 1，op 参数）| 公司及关联数据 |
| 6 | `researchpipe_industry_data` | industries deals/companies/chain/policies/tech_roadmap（5 in 1，op 参数）| 行业及关联数据 |
| 7 | `researchpipe_investor_data` | investors search/get/portfolio/preferences/exits（5 in 1）| 机构画像 + portfolio |
| 8 | `researchpipe_watch` | watch create/digest（2 in 1）| 订阅 / cron 摘要 |

**Tool description 规范**（学 Anthropic Tool Use 最佳实践）：

```typescript
// @researchpipe/mcp-server/src/tools/research_company.ts
{
  name: "researchpipe_research_company",
  description: `Performs comprehensive due diligence research on a company.
Returns structured analysis: business profile, peer comparison, valuation anchor,
filing risks, founders background, red flags, and outlook.

Use this when the user asks to:
- "Analyze [company name]"
- "Do due diligence on [company]"
- "Research a company's investment value"

For just basic company info (name, sector, funding), use researchpipe_company_data instead.

<examples>
  <example>
    <user_query>分析一下宁德时代</user_query>
    <tool_call>{"input": "宁德时代", "model": "auto"}</tool_call>
  </example>
  <example>
    <user_query>帮我深度看下英伟达，重点看一级估值参考</user_query>
    <tool_call>{"input": "NVIDIA", "focus": ["business","valuation_anchor","peers"]}</tool_call>
  </example>
</examples>`,
  inputSchema: {
    type: "object",
    properties: {
      input: { type: "string", description: "Company name or ID" },
      focus: { type: "array", items: { type: "string" }, default: ["business","financials","risks"] },
      model: { type: "string", enum: ["mini","pro","auto"], default: "auto" }
    },
    required: ["input"]
  }
}
```

**关键设计**：
- **Description 用英文**（Claude 选 tool 准确率最高），但内嵌 `<examples>` 用中文（客户读 docs 直观）
- **每个 tool 的 op 参数有清晰枚举**，agent 不会传错
- **Research 类 tool 内部封装 poll**：MCP Server 调 HTTP 后台 poll，对 Claude 透明（看到的是同步返回）
- **不暴露写操作**：`watch_create` 是白名单允许的例外，其他写操作不开放

**安装方式**（Claude Desktop / Cursor / Cline 通用）：

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "researchpipe": {
      "command": "npx",
      "args": ["@researchpipe/mcp-server"],
      "env": {
        "RESEARCHPIPE_API_KEY": "rp-xxx"
      }
    }
  }
}
```

**MCP 与 SDK 的关系**：MCP Server 内部调 Node SDK（`@researchpipe/sdk`），不直接接 HTTP。SDK 升级 → MCP 自动升级。

**实现路径**：

```
@researchpipe/mcp-server/
├─ src/
│   ├─ index.ts                    # MCP server 入口
│   ├─ tools/
│   │   ├─ search.ts
│   │   ├─ extract.ts
│   │   ├─ research_sector.ts      # 内部封装 poll
│   │   ├─ research_company.ts     # 内部封装 poll
│   │   ├─ company_data.ts         # op 分流
│   │   ├─ industry_data.ts        # op 分流
│   │   ├─ investor_data.ts        # op 分流
│   │   └─ watch.ts                # create + digest
│   ├─ client.ts                   # 包装 @researchpipe/sdk
│   └─ poll_helper.ts              # ★ 异步 poll 封装（用户透明）
└─ package.json
```

---

## 八、安全合规

### 8.1 三层法律防护（工程实现）

**第一层：数据来源合法性**
- 数据源白名单硬编码 + DB 配置双层
- 每条入库强制 `source_url`，永久保留
- 不爬付费墙、终端导出、注册账户专享

**第二层：账号商业化分离**
- 当前 qmp 账号 `muye.m.li@shell.com`（壳牌资本-机构版）
- M3 末必须申请独立企名片企业账号（年费 ¥5-10 万）
- 旧账号数据保留为研发存档，停止增量；新账号独立流水线

**第三层：输出形态合规**
- API 响应只含**衍生分析**（聚合统计、向量推荐、字段抽取后归纳）
- 不输出原始数据库副本
- 上市文件标注 source_url + "原文请访问交易所官网"
- 法务下架接口（POST /admin/takedown）：立即过滤指定数据源
- 数据保留：研报 / 上市文件永久（公开内容）+ 用户查询日志 90 天

### 8.2 API 安全

| 措施 | 实现 |
|---|---|
| API Key 鉴权 | sha256(key) 比对 + 月度 quota |
| HMAC 防重放 | 可选，企业版以上启用 |
| 限流单 Key | 60 req/min |
| 限流单 IP | 120 req/min |
| 全局限流 | 1000 req/sec |
| 单查询超时 | 30 秒 |
| 异常检测 | 单 key 5 分钟超 100 调用自动暂停 |
| 审计日志 | rp_api_logs 表，保留 90 天 |

---

## 九、性能与成本

### 9.1 性能目标

| 指标 | M1（A 线主导）| M6（B 线主导）|
|---|---|---|
| P50 延迟 | 4 秒 | 800ms |
| P95 延迟 | 8 秒 | 2 秒 |
| P99 延迟 | 15 秒 | 5 秒 |
| Redis 缓存命中率 | 30% | 70% |
| 自建库命中率 | 30% | 80% |

### 9.2 月度成本结构

| 项目 | M1 | M6 | M12 |
|---|---|---|---|
| 服务器（复用 + 扩容）| ¥0（复用现有）| ¥1,500 | ¥3,000 |
| qmp_postgres 存储扩展 | ¥0 | ¥500 | ¥1,000 |
| MinIO（67K × 5MB ≈ 350GB）| ¥0 | ¥600 | ¥800 |
| API 调用（A 线 4 渠道）| ¥3,600 | ¥1,500 | ¥800 |
| LLM 抽取 | ¥1,500 | ¥3,000 | ¥5,000 |
| 监控/日志/带宽 | ¥400 | ¥1,500 | ¥2,000 |
| **合计** | **¥5,500** | **¥8,600** | **¥12,600** |

| 单查询毛利 | M1 | M6 |
|---|---|---|
| 平均收费 | ¥0.5 | ¥0.5 |
| 平均成本 | ¥0.20 | ¥0.04 |
| 毛利率 | 60% | 92% |

### 9.3 容量规划

- M1：原 qmp_data + 1K kcb/cyb 入库
- M3：上市文件 67K 全量入库，350GB MinIO
- M6：+ 政策 / 产业链 / 国外创投 / 专利子库，500GB
- M12：800GB 总存储，全 17 子库

---

## 十、监控与告警

### 10.1 关键指标看板（Grafana）

**业务侧**：
- 当日 / 本月 API 调用次数
- 各端点调用 QPS
- sector-snapshot 来源数据分布
- 各档位订阅数 / MRR / 客户增长曲线
- 各场景策略调用占比（中文 / 海外 / 跨市场 / 实时）

**技术侧**：
- 各 qmp 抓取任务成功率（kcb / cyb / news / product）
- Token 健康（剩余天数）
- 各 API 渠道（Tavily/Bocha/Serper/Firecrawl）可用性 / 延迟 / 失败率
- DeepSeek V4 调用失败率 + 平均 quality_score
- 入库速度（份/小时）

**法律侧**：
- 法务下架接口触发次数
- 每条响应是否包含 source_url（强制校验）

**成本侧**：
- 各 API 渠道日消耗
- LLM 累计 token 消耗
- 单查询平均成本

### 10.2 告警规则

| 严重 | 触发 | 通知 |
|---|---|---|
| P0 | 任一抓取任务连续 2 周失败 | 邮件 + 电话 |
| P0 | qmp Token 剩余 < 3 天 | 邮件 |
| P0 | API 整体可用性 < 99% 持续 5 分钟 | 短信 + 邮件 + 钉钉 |
| P0 | sector-snapshot P95 > 15s | 钉钉 |
| P1 | 任一外部 API 失败率 > 20% | 邮件 |
| P1 | DeepSeek 抽取失败率 > 10% | 邮件 |
| P2 | 单查询成本超阈值 ¥2 | 日报 |

---

## 十一、部署架构

### 11.1 单机起步（M1-M3）

```
┌─────────────────────────────────────────┐
│   单台 ECS：8C16G + 1TB SSD               │
│  ┌──────────────────────────────────┐   │
│  │ docker-compose.yml                │   │
│  │  ├─ nginx (api gateway)           │   │
│  │  ├─ fastapi (ventureos/QMPData)   │   │
│  │  ├─ extraction-worker (× 4)       │   │
│  │  ├─ crawler-worker (× 5)          │   │
│  │  ├─ scheduler                     │   │
│  │  ├─ postgres (qmp_data + rp_*)    │   │
│  │  ├─ redis                         │   │
│  │  ├─ minio                         │   │
│  │  ├─ prometheus + grafana + loki   │   │
│  │  └─ playwright (headless)         │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

**月成本**：¥500-800（阿里云）

### 11.2 横向扩展（M6+）

- API 服务：3 节点 + LB
- 爬虫 Worker：独立 2 节点（避免影响主服务）
- PostgreSQL：主从 + 读写分离
- Redis：哨兵模式
- MinIO：3 节点集群

---

## 十二、第 1 个月开发计划（v3 重排，对齐 4 产品线）

**v3 重排逻辑**：
- v3 产品架构变成 4 产品线（Search / Research / Data / Watch）。M1 上线 **20 个端点**（Search 3 + Data 14 + 账户 3）—— 不上 Research（M3）和 Watch（M2）
- W1 仍然先验证 prompt（research/sector 默认 schema），但因为 Research 是 M3 端点，W1 改为**验证 extract/research 的字段抽取质量**作为 M1 的核心 LLM 决策
- 单干 + Claude Code，但用户决定不砍范围（M1 全做：Python SDK + Node SDK + MCP + 前端 + Docs）
- 部署改为自托管 + frp/cloudflare tunnel + rp.zgen.xin 子域名（零云成本）

### M1 上线 20 端点清单（按 PRD v3 6.7）

```
Search（3）：
  S1. POST /v1/search                     1c
  S2. POST /v1/extract                    2c
  S3. POST /v1/extract/research ★        5c

Data（14）：
  D1. POST /v1/companies/search           0.5c
  D2. GET  /v1/companies/{id}             0.5c
  D3. GET  /v1/companies/{id}/deals       1c
  D5. GET  /v1/companies/{id}/news        1c
  D7. POST /v1/investors/search           0.5c
  D8. GET  /v1/investors/{id}             0.5c
  D9. GET  /v1/investors/{id}/portfolio   1c
  D12. POST /v1/deals/search              1c
  D13. GET  /v1/deals/{id}                0.5c
  D17. POST /v1/industries/search         0.5c
  D18. GET  /v1/industries/{id}/deals     1c
  D19. GET  /v1/industries/{id}/companies 1c
  D26. POST /v1/valuations/search         1c
  D27. POST /v1/valuations/multiples      1c
  D35. POST /v1/news/search               1c
  D36. POST /v1/news/recent               0.5c

账户（3）：
  A1. GET /v1/me
  A2. GET /v1/usage
  A3. GET /v1/billing
```

### Week 1（M1.1-M1.7）—— 抽取 prompt 验证 + 基础设施

| 日 | 任务 | 关键交付 |
|---|---|---|
| D1 | 项目骨架（fork ventureos/QMPData → 分支 research-pipe）+ 所有 rp_* 表落地（含 v3 新加 rp_research_jobs / rp_idempotency_keys / rp_entity_aliases）| DB schema 就位 |
| D2 | mockrogo LLM 适配器移植 + DeepSeek V4 客户端 + 错误处理框架（APIError + hint_for_agent）| LLM 调用 + 错误规范通 |
| D3 | **核心 prompt 验证**：用 qmp_data 拉 5 篇真实研报 → 喂 DeepSeek V4 抽取 11 字段（M1 必出）→ 自评质量 | **关键里程碑**：extract/research 字段抽取质量 ≥ 0.7（自评 / 朋友盲测）。不通过立即调 prompt |
| D4 | 同样验证 5 个赛道的 search/research（A 线 4 渠道路由） + 抓取热门招股书 priority list（B+D 决策）| 多源研报路由 + 抓取列表 |
| D5 | scrape_qmp_reports.py 加 `--priority-list` + 加入 cron（kcb/cyb/news 三端点）| 抓取流水线启动 + 优先抓 ~3K 份热门招股书 |
| D6 | 鉴权 + Credits 中间件 + Idempotency-Key + Token Bucket Rate Limit + 响应 header（X-RateLimit-* / X-Credits-*）| 中间件链全通 |
| D7 | Entity resolver（fuzzy + 别名表）+ 实体去重端到端测试 | 多源去重就位 |

**W1 末关键检查点**：extract/research 抽取 11 字段质量 ≥ 0.7（5 篇朋友盲测）。不通过立即调 prompt 或放弃 Search 系列。

### Week 2（M1.8-M1.14）—— 20 端点全跑通

| 日 | 任务 | 端点 |
|---|---|---|
| D8 | 4 渠道 API 客户端（Tavily/Bocha/Serper/Firecrawl）+ Search 路由器 | S1, S2 |
| D9 | extract/research 完整实现 + 字段抽取流水线 | S3 ★ |
| D10 | Companies + Investors（Data 产品线 B+C 组）| D1, D2, D3, D5, D7, D8, D9 |
| D11 | Industries + Deals（Data 产品线 D+Deals 组）| D12, D13, D17, D18, D19 |
| D12 | Valuations + News（Data 产品线 E+G 组）| D26, D27, D35, D36 |
| D13 | 账户 + 实体去重 + 多源字段冲突合并 + freshness `_meta` | A1, A2, A3 |
| D14 | 端点联调 + Postman Collection + OpenAPI 3.0 spec 自动生成 | 20 端点全通 |

**W2 末**：M1 范围 20 端点全部可调用 + Credits 计费 + Idempotency-Key 跑通 + 错误返回带 hint_for_agent。

### Week 3（M1.15-M1.21）—— SDK + MCP + 前端 + Docs

| 日 | 任务 | 关键交付 |
|---|---|---|
| D15 | Python SDK（researchpipe）覆盖 20 个端点 + httpx + pydantic v2 + async/sync 双版本 + 自动重试 + 类型严格 | `pip install researchpipe` 可用 |
| D16 | Python SDK 发布 PyPI（0.1.0 alpha）+ 写 5 个 Cookbook 示例代码 | PyPI 上线 |
| D17 | Node SDK（@researchpipe/sdk）TypeScript + axios + zod，覆盖 20 端点 | `npm install` 可用 |
| D18 | **MCP Server**（@researchpipe/mcp-server）8 个智能 tool + Tool description 英文 + 中文 examples + Research 异步 poll 封装 | `@researchpipe` 在 Claude Desktop 可用 ★ |
| D19 | Next.js 14 前端骨架（rp.zgen.xin 子域名 + Vercel 部署）：Landing + Playground + Dashboard | 前端上线 |
| D20 | Docs 站（rp.zgen.xin/docs）：OpenAPI 自动生成 + llms.txt + llms-full.txt + 每页 .md + 5 个 Cookbook | docs 上线 |
| D21 | system prompt 模板（让 Cursor/Claude Code 喂入即用）+ Docs 第 1 屏 60 秒 Quickstart | "60 秒上手"承诺达成 |

**W3 末**：客户能从 `pip install researchpipe` 到第一次成功调用 < 60 秒。MCP Server 在 Claude Desktop 跑通 8 个智能 tool。

### Week 4（M1.22-M1.28）—— 客户验证 + 上线

| 日 | 任务 |
|---|---|
| D22 | 监控看板（Grafana 看 API 调用 / Credits / 错误率 / freshness）+ 法务声明定稿 |
| D23 | 上线 rp.zgen.xin，开放 Free 注册（100 credits / 月）|
| D24-25 | 5 个种子用户邀测（朋友圈 + 即刻 + 微信群，A+C+F 渠道）+ 1 对 1 上手 |
| D26 | 在即刻 / 微信群发布"用 Cursor + ResearchPipe 30 分钟做研报扫描器"demo 视频 + Claude Desktop MCP 配置教程 |
| D27 | 第一批反馈收集 + bug 修 + Cookbook 增量 |
| D28 | M1 复盘 + M2 计划（M2 上 24 个端点：filings 系列 + research 系列 prompt 调试 + watch 订阅 + screen + tech_roadmap）|

### M1 成功标准（v3）

- ✅ **W1 末**：extract/research 字段抽取 11 字段质量自评 ≥ 0.7（5 篇真实研报）
- ✅ **W2 末**：20 个 M1 端点全部可调用 + Credits 计费 + Idempotency-Key + Rate Limit + 错误处理（带 hint_for_agent）+ partial warnings 全部跑通
- ✅ **W3 末**：Python SDK + Node SDK + MCP Server 全部发布；从 `pip install` 到第一次成功调用 < 60 秒
- ✅ **W3 末**：rp.zgen.xin 上线（Landing + Playground + Dashboard）+ docs 上线（含 llms.txt / llms-full.txt / 5 篇 Cookbook）
- ✅ **W4 末**：≥ 5 个种子用户跑通真实工作流（其中 ≥ 2 个 Cursor 用户、≥ 1 个 Claude Desktop MCP 用户），收到 ≥ 10 条具体反馈
- ✅ scrape_qmp_reports.py 三端点稳定运行 ≥ 2 周；优先抓的 ~3K 份热门招股书入库完成
- ✅ 单次调用成本 < ¥0.50

**未达标的退出策略**：
- 若 W1 prompt 验证失败 → 调 prompt 1-2 天 → 仍失败说明产品定位有问题，由用户决定下一步（用户保留判断权）
- 若 W4 客户验证失败 → 不立即停，先扩 Free → Hobby 漏斗（即刻 / 微信群放大），本质是 PLG 增长慢于预期，但 ¥3 万预算允许多观察 1-2 个月

---

## 十三、关键文件路径速查

| 类别 | 路径 |
|---|---|
| 抓取脚本 | `/home/muye/qimingpian/scrape_qmp_reports.py` ✅ 已就绪 |
| qmp API 客户端 | `/home/muye/qimingpian/qimingpian_api.py` |
| qmp 现有 cron | `crontab -l` |
| qmp DB | Docker `qmp_postgres:5432` / DB `qmp_data` |
| 现有 FastAPI | `/home/muye/ventureos/QMPData/api/main.py` |
| Token 配置 | `/home/muye/qimingpian/config.json` |
| Storage state | `/home/muye/qimingpian/storage_state.json` |
| 抓取输出 | `/home/muye/qimingpian/output/*.csv` |
| 抓取日志 | `/home/muye/qimingpian/logs/` |
| mockrogo LLM | `/home/muye/mockrogo/backend/src/services/llm` |
| mockrogo RAG | `/home/muye/mockrogo/backend/src/services/rag` |

---

## 十四、关键风险技术应对清单

| 风险点 | 工程对策 |
|---|---|
| Tavily 限流 | 多 API key 轮询 + 客户端级 rate limit |
| 反爬升级 | Playwright + IP 代理池 + 频率退避 |
| GeeTest 验证码升级 | refresh_token.py 已有交互式重登流程 |
| Token 过期 | cookie_keepalive.py 持续保活 + 监控告警 |
| LLM 输出格式偏移 | response_format=json_object + JSON schema 校验 + 重试 1 次 |
| LLM 主备切换 | DeepSeek V4 → V3.2 → Qwen3-235B → 返回 raw_content |
| PostgreSQL 性能瓶颈 | 索引：source_url、broker_id、report_date、sector |
| MinIO 容量 | 自动归档 36 个月前 PDF 到冷存储 |
| 爬虫监控漏报 | 每日凌晨发送爬取报告（成功/失败/入库数）|
| 企名片接口变更 | scrape_qmp_reports.py 解耦端点配置 + 监控告警 |

---

**EDD 文档结束。**
