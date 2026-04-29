# 投资研报结构化提取 API — 产品需求文档（PRD）

| 项目 | 内容 |
|---|---|
| 项目代号 | ResearchPipe |
| 编写日期 | 2026-04-28 |
| 文档状态 | v3 - 中国版 Tavily / 4 产品线 / 50 端点 / 手搓 Agent 大军 + 一级市场聚焦 |
| 阶段 | MVP 启动前 |

---

## 一、执行摘要

ResearchPipe（**中文名：投研派**）—— **中国版 Tavily，但聚焦投资 / 行研领域**。

**一句话定位**：投研垂类 **API + SDK + MCP**，为**手搓 Agent 大军**而生。一个 API Key，让客户的 **Cursor / Claude Desktop / Cline** 瞬间获得 PE/VC 级投资情报。

**目标用户：手搓 Agent 大军 + 一级市场聚焦**

| 主战场 | 子群 | 典型工作流 |
|---|---|---|
| **A 群（核心）** | Cursor / Cline / Claude Code 用户 | IDE 里 vibe coding 写 Python 调 SDK |
| **D 群（核心）** | Claude Desktop / Cursor MCP 用户 | 自然语言提问 → Claude 调 MCP tool |

**业务聚焦**：一级市场（PE/VC 行研、家办、独立投资人、AI 投研创业者）。**完全不做**二级市场（实时行情、量化、技术分析）。

**产品架构：学 Tavily 双产品 + 投研垂类差异化（4 条产品线）**

| 产品线 | 形态 | 类比 Tavily | 端点 | Credits/次 |
|---|---|---|---|---|
| **Search** | 同步秒级 / 原料供应 / agent 自合成 | Tavily Search | 6 | 1-5 |
| **Research** | 异步多步 LLM / 成品交付 / `output_schema` 自定义 / `citations` | Tavily Research | 3 | 30-100 |
| **Data** | 同步毫秒级 / 投研结构化数据 | **Tavily 没有，护城河** | 38 | 0.5-3 |
| **Watch** | cron 友好 / 订阅摘要 | **Tavily 没有** | 2 | 10/digest |
| **总计** | | | **49 + 账户/admin** | |

**三种交付形态**（M1 全做）：
1. **HTTP API**（RESTful + OpenAPI 3.0 + 路径版本号 `/v1/...`）
2. **Python / Node SDK**（`pip install researchpipe` / `npm install @researchpipe/sdk`）
3. **MCP Server**（`npx @researchpipe/mcp-server`，Claude Desktop / Cursor 一行 config 即用，暴露 8 个智能 tool）

**关键 Agent 友好设计**：
- 错误返回带 `hint_for_agent`（自然语言告诉 LLM 下一步怎么办）
- partial success warnings（多源融合失败 1 个不影响整体）
- Idempotency-Key 防重复扣费（学 Stripe）
- 跨实体精简 inline + `expand` 参数（学 Stripe）
- 每个 entity 带 `_meta.freshness_status` + `last_updated_at`
- Research 异步默认 poll + 可选 SSE stream
- `output_schema` 完全自定义（agent 拿到严格 schema 直接 chain 下一步）

**8 类数据源汇总融合** → DeepSeek V4 字段抽取/翻译 → 归一化 JSON：

1. 卖方研报观点（Tavily/Bocha 搜索 + 自爬补位）
2. 一级市场融资事件（企名片 26K events）
3. 海外创投 deal（企名片国外创投子库）
4. 上市公司强制披露文件（科创板 22.6K + 创业板 45K = **67,668 份招股书/问询/审计/法律意见书**）
5. 政策与十五五规划匹配
6. 产业链上下游图谱
7. 专利布局
8. 实时新闻流（12.2 万条）

**双线并行（v3 战略调整 2026-04-29）**：

- **A 线（API 套壳 + 多源组合，主战场）** —— Tavily / Bocha / Serper 三渠道路由器（已注册 + 实测），加 multi-source 并发去重排序模式（M1 已实装）。Tavily Extract 单一抓取层（替代 Firecrawl，省一笔订阅）。Tavily Research API 直供深度报告。**所有研报 / 政策 / 产业链 / 专利 / 海外 deal / 新闻**走 A 线实时套壳，**不预爬不落库**。1 个月内全量上线
- **B 线（独家数据，唯一护城河）** —— 仅 `qmp_data` 一级市场数据：events 26K + institutions 5K + valuations 2.8K（weekly_pipeline cron 在跑增量）。这是任何套壳都拿不到的独家。其他 17 子库 / 67K 上市文件首爬 / 12.2 万新闻全量爬取**均推到 M3+ 可选**

> **战略口径（重要）**：前端文案保持 "8 类数据源 / 67K 上市文件 / 26K 一级 deal / 50+ 端点" 不变。"做"的方式（套壳为主）和"说"的方式（覆盖广）可以分开 — 客户拿到的端点输出和数据完整度一致，实现细节是工程内部的事

**冷启动目标**：M1 内验证 5 家付费意愿，M3 达 ¥3 万 MRR，M6 达 ¥15 万 MRR，M12 达 ¥50 万 MRR。

---

## 二、市场背景与竞争分析

### 2.1 PE/VC 投资研究真实工作流痛点

PE/VC 行研做行业判断时，需要拼凑的信息来源：

1. **行业 narrative** ← 看券商行业深度报告
2. **公司 ground truth** ← 看招股书 + 问询回复（**这才是真正的尽调一手材料**）
3. **估值参考** ← 看一级 deal 价格 + 行业 PS/PE 倍数
4. **政策判断** ← 看十五五规划、行业政策
5. **产业链判断** ← 看上下游公司布局
6. **机构动向** ← 看头部 VC/PE 在投什么
7. **海外对照** ← 看 GS/MS 报告 + 海外 deal

当前痛点：
- 信息分散在数十家券商网站、企名片、Wind、东财等多个平台
- 海外英文研报无中文化通道，时效性差
- 没有针对投资视角的字段抽取——通用搜索只给 PDF 链接，阅读 80 页招股书抓"商业逻辑/估值假设"耗时极高
- 跨券商、跨市场对比无工具

### 2.2 7 家搜索/抓取 API 实测结论

我们在产品设计前对 7 家相关 API 做了真实测试：

| 工具 | 类型 | 中文搜索 | 英文搜索 | PDF 全文 | 单次成本 | 在我们产品中的角色 |
|---|---|---|---|---|---|---|
| **Tavily** | 搜索+抓取一体 | 中 | 优 | ✅ 100% | ¥0.06/次 | 海外 + 跨市场核心引擎 |
| **Bocha** | 中文搜索 | **优** | 弱 | ❌ 摘要 | ¥0.03/次 | 中文发现层 |
| **Serper** | Google 搜索代理 | 中 | **优** | ❌ 摘要 | ¥0.04/次 | 海外发现层 |
| **Firecrawl** | 抓取器 | OK | OK | ✅ 按 URL | ¥0.01/页 | 抓取兜底 |
| Cloudsway | 中文搜索（Bing 系）| 好 | 中 | ❌ 摘要 | 同 Bocha 量级 | **砍掉**（与 Bocha 功能重叠）|
| Brave | 海外搜索（独立索引）| 一般 | 优 | ❌ 摘要 | 低 | **砍掉**（与 Serper 功能重叠）|
| Jina Reader | 抓取器 | OK | OK | ✅ 按 URL | 极低 | 备胎（账户欠费，未启用）|

**关键决策**：A 线最终留下 **Tavily / Bocha / Serper / Firecrawl** 四件套，覆盖中英文搜索 + 全文抓取，无功能冗余。

### 2.3 现有产品能力空缺评估

| 产品 | 卖方研报 | 一级 deal | 上市文件抽取 | 政策匹配 | 产业链 | 海外 | LLM 字段化 | API 化 |
|---|---|---|---|---|---|---|---|---|
| Tavily | ⭕ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |
| Bocha | ⭕ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Wind / iFinD | ✅ | ⭕ | ⭕ | ⭕ | ❌ | ⭕ | ❌ | 半 |
| 慧博 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 企名片 Pro | ❌ | ✅ | ✅（仅原文）| ⭕ | ✅ | ✅ | ❌ | 半 |
| **ResearchPipe** | **✅** | **✅** | **✅** | **✅** | **✅** | **✅** | **✅** | **✅** |

**结构性市场空白**：所有维度齐备 + LLM 字段抽取 + 标准 API 交付，是真正的市场空白。

### 2.4 我们卖的是 API，不是 Agent ⚠️

讨论中曾出现一个倾向性混淆：是否给客户做"跨券商对比矩阵 / 投决建议 / 总结报告"。

**结论：明确不做。**

| 形态 | 例子 | 是否做 |
|---|---|---|
| API 基础设施 | 输入查询 → 输出统一字段 JSON | ✅ 这是产品 |
| Demo 演示页 | 拿 API 自己渲染 3 个示例视图 | ✅ 仅作为售前转化用 |
| 对比矩阵 / 投决建议 | 替客户输出"买/不买"结论 | ❌ 这是 Agent，不是 API |

**理由**：
1. Agent 模式高度可复制（任何团队加几个 prompt 就能复刻），没有壁垒
2. API 模式的护城河在于**数据资产 + 字段 schema + 路由经验**，6-12 个月可形成
3. 客户应用层（怎么对比、怎么决策）是客户自己的业务逻辑，我们不替他做

**我们只做一件事：把分散的、PDF 形态的研报和披露材料，变成统一字段的 JSON 数据流。**

---

## 三、产品定位

### 3.1 一句话定位

**"中国版 Tavily，聚焦投资 / 行研——为手搓 Agent 大军而生。"**

一个 API Key，让 **Cursor / Claude Desktop / Cline 用户**瞬间获得 PE/VC 级投研情报。客户不打开 Wind 终端、不订阅多家 SaaS、不写爬虫——`pip install researchpipe` 或在 Claude Desktop 里加一行 MCP config，30 秒进入 agent 工作流。

### 3.2 核心价值主张

| 维度 | 价值 |
|---|---|
| **学 Tavily 双产品架构** | Search（原料）+ Research（成品）并存，客户按场景选 |
| **三形态交付** | HTTP API + Python/Node SDK + MCP Server（M1 全做）|
| **一级市场聚焦** | deal flow / 机构画像 / 估值带 / 创始团队深度 / co-investor 网络 |
| **行业 + 技术深度** | 8 类研报源（券商 / 咨询 / 协会 / 大厂研究院 / VC / 海外 IB / 媒体 + 自爬）+ 技术路线图 / 关键技术清单 / 技术成熟度 |
| **上市文件结构化** | 6.7 万份招股书/问询/审计/法律意见，5 套 schema 自动抽取（业内首创）|
| **政策影响评估** | LLM 评估每条政策对赛道的 direction / intensity / time_horizon |
| **跨市场覆盖** | A 股 + 港股 + 美股 + 海外私募，一次拉齐 |
| **海外英文中文化** | DeepSeek V4 一步翻译+字段抽取 |
| **数据资产护城河** | qmp_data 已就位 + 持续抓取累积，竞争对手 6 个月无法复制 |
| **Credits 计费** | 不同端点 0.5-100 credits，定价灵活 |

### 3.3 产品边界（不做什么）

**业务边界**：
- ❌ 不做二级市场（实时行情 / K 线 / 量化 / 技术分析 / 持仓监控 / 选股策略）—— 一级市场聚焦
- ❌ 不做"投决建议 / 总结报告 / 对比矩阵"等结论性产物（客户的应用层）
- ❌ 不做研报真伪验证、合规审查、KOL 个人观点 / 社交媒体爬取

**形态边界**：
- ❌ 不做前端可视化 SaaS 产品（前端只做 Landing + Playground + Docs + Dashboard 四件套，学 Tavily 范式）
- ❌ 不做 LangChain / LangGraph / AutoGen / CrewAI 官方 integration（客户用 SDK / MCP 自接更灵活）
- ❌ 不做 Coze / Dify / n8n / FastGPT 平台插件
- ❌ 不做"为运营/产品经理"的拖拽 UI（目标是工程师 + AI 重度用户）

**法律边界**：
- ❌ **永远不输出原始数据库副本**——只输出衍生分析与字段化数据（法律安全 + 不可复制）
- ❌ 不爬付费墙后内容、不爬 Wind/Choice/iFinD 终端导出

---

## 四、目标客户

### 4.1 客户分层（一级市场聚焦 + PLG 增长漏斗）

| 客群 | 月费档位 | 月度 Credits | 子群 | 核心痛点 | 卖点 |
|---|---|---|---|---|---|
| **Free**（注册即用）| ¥0 | 100 | A+D 群尝鲜 | 想试一下 | 注册送 100 credits，无需信用卡 |
| **Hobby**（个人 KOL / 公众号 / 投研副业）| ¥99 | 2,000 | A 群核心 | 公众号每天扫赛道 | cron 跑得起 watch/digest + news/recent |
| **Starter**（独立分析师 / 投研创业者 / 家办分析师）| ¥1,500 | 20,000 | A+D 群进阶 | 一级 deal + 招股书深度解读 | research/sector + filings/extract + 跨市场对标 |
| **Pro**（VC/PE 行研 / 投决支持）| ¥5,000 | 80,000 | A+D 群主力 | 多源情报手工拼凑 + 项目尽调 | research/company + dd 流水线 + co_investors 网络 |
| **Enterprise**（小型 PE / 大厂战投 / 券商策略）| ¥15,000 | 300,000 | E 群（投研创业者）| 内部数据中台 | 全端点 + 不限频 + 优先 SLA |
| **Flagship**（头部 PE / 保险资管 / 投行）| ¥30,000 | 不限 | E 群高阶 | 字段定制 + 私有部署 | 全端点 + custom schema + 专属 SLA |
| **超额** | ¥0.5/100 credits | — | — | — | — |

**客户分层的一级市场倾斜**：
- **Hobby 档**：核心是公众号 KOL / 个人投研账号 / 业余分析师。一级市场资讯爱好者多
- **Starter / Pro 档**：直接对应 VC/PE 行研、家办分析师、独立投资人 —— 一级市场主战场
- **Enterprise / Flagship 档**：小型 PE / 战投 / 券商策略部 —— 仍以一级市场视角为主
- **不再分层**："券商策略"被归到 Enterprise 而非独立档位（聚焦一级市场后客群整合）

**Credits 消耗参考**（按产品线分）：

| 产品线 | Credits/次 | 端点示例 |
|---|---|---|
| Data 列表查询 | 0.5 | companies/search, news/recent, deals/search |
| Data 单查询 | 1 | search, extract |
| Search 抽取 | 5 | extract/research, extract/filing |
| Data 衍生（peers/timeline）| 2-5 | companies/peers, events/timeline, screen |
| Watch 摘要 | 10 | watch/{id}/digest |
| Research mini | 20 | research/sector, research/company（mini）|
| Research pro | 50 | research/sector, research/company（pro）|

**关键设计**：Free 档可以频繁跑 search / Data，但 research/* 跑一次就用 1/5 quota → 天然引导升级。
**Hobby 档真实工作流**：daily watch/digest（10c × 30 天 = 300c）+ 1000 次 news/search + 100 次 extract/research ≈ 全月 2000 credits，正好够公众号 KOL。

### 4.2 典型场景（一级市场 / 手搓 Agent 视角）

1. **VC 行研每日 deal flow 扫描**（Pro 档）：
   ```python
   # Cursor 里写的脚本，每天 9:00 cron
   res = client.watch.digest("具身智能_监控")
   # → 拉昨日新增 deal + 公司动态 + 政策 + 新闻
   # 喂 Claude → 生成投决会议简报
   ```

2. **公众号 KOL 每日赛道日报**（Hobby 档）：
   ```python
   for industry in ["半导体国产化","具身智能","创新药出海"]:
       digest = client.watch.digest(industry)
       article = claude.generate(prompt=template, data=digest)
       publish(article)
   ```

3. **VC 项目尽调自动化**（Pro 档）：
   ```python
   # 收到 BP，5 秒生成尽调初步报告
   res = client.research.company(input="宁德时代", focus=["business","financials","risks","peers"])
   # → 同行 deal 价格 + 招股书风险 + 创始团队红旗 + co-investors 网络
   ```

4. **Claude Desktop 里自然语言尽调**（Pro 档，D 群）：
   ```
   用户："@researchpipe 分析下宁德时代，重点看一级估值参考和同行对标"
   Claude → researchpipe_research_company(...)
   → 直接拿到完整尽调报告
   ```

5. **AI 投研创业者做"IPO 风险扫描" SaaS**（Enterprise）：
   - 自家产品调 `filings/search + filings/extract/risks + screen` → 包装成 SaaS 卖给保险资管

6. **小型 PE 找 LP / 联合投资方**（Pro 档）：
   ```python
   investors = client.investors.search(industry="半导体", round_stage="B")
   for inv in investors:
       prefs = client.investors.preferences(inv.id)
       exits = client.investors.exits(inv.id)  # 退出案例
   ```

7. **个人投研者赛道全景**（Starter 档）：
   ```python
   # output_schema 自定义返回 agent 想要的字段
   res = client.research.sector(
       input="具身智能",
       output_schema={
           "properties": {
               "top_5_companies": {"type": "array"},
               "key_risks": {"type": "array"},
               "12m_outlook": {"type": "string"}
           }
       },
       model="pro"
   )
   ```

8. **技术路线对比研究**（Pro 档，新增场景）：
   ```python
   # 比较具身智能两条技术路线
   compare = client.technologies.compare(
       routes=["端到端神经网络VLA","分层架构 SLAM+控制"]
   )
   # → 优劣势 + 代表公司 + 投资活跃度 + 成熟度评估
   ```

---

## 五、信息源全景

> **v3 战略调整（2026-04-29）**：原 3 层架构（本地资产 + 套壳 + 自爬）改为 **2 层 + 1 个降级备选**。第二层（套壳 + 多源组合）从"补位"提升为"主战场"。第三层（30 家券商自爬）实测 100% 反爬，降级为 M5+ 可选。本地资产瘦身为只保 qmp 一级 deal 数据；其他 17 子库 + 67K 上市文件全量爬推到 M3+ 可选。

### 5.1 数据源 2 层架构（v3）

```
┌─────────────────────────────────────────────────┐
│ 第一层：B 线独家数据（唯一护城河）                │
│  └─ qmp_data PostgreSQL（已就位 + weekly 增量）  │
│      ├─ events 26,757（一级市场融资事件）★      │
│      ├─ institutions 5,000（机构画像）★         │
│      ├─ valuations 2,801（含海外可比）★         │
│      ├─ industry_ps_multiples 102               │
│      ├─ investment_cases 409                    │
│      └─ [pgvector 1024 维已就位]                │
│   ★ = 任何套壳都拿不到，独家数据                 │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│ 第二层：A 线套壳 + 多源组合（主战场）             │
│  ├─ Tavily Search（中英搜索 + 答案合成）         │
│  ├─ Tavily Extract（PDF + HTML 全文，替代 Firecrawl）│
│  ├─ Tavily Research（30-60s 异步深度报告）       │
│  ├─ Bocha（中文搜索补位）                        │
│  ├─ Serper（Google 海外发现）                    │
│  └─ DeepSeek V4（百炼）字段抽取 + 多源合成层     │
│                                                  │
│  组合模式：Tavily + Bocha + Serper 3 路并发      │
│           → URL 去重 → rank score 加权排序       │
│           → partial 容错（单源 fail 不阻塞）     │
│  实现：backend/src/researchpipe_api/multi_search │
└─────────────────────────────────────────────────┘

[降级备选 — M3+ 可选启动]
- qmp 上市文件首爬（kcb 22.6K + cyb 45K + news 12.2万）：脚本就绪未挂 cron，量不大保留为可选
- qmp 17 子库（国外 deal / 政策 / 产业链 / 专利 / 标签 等）：M3+ 探明 API 后再扩
- C 层 30 家券商自爬：实测 100% 反爬（30/30 hard），M5+ 也不做
```

### 5.2 数据源优先级矩阵（v3）

| 优先级 | 数据源 | 行动 | 周期 |
|---|---|---|---|
| **P0** | qmp 现有 events / institutions / valuations | 直接对接 API 层（**M1 已实装**）| M1 周 1-2 |
| **P0** | A 线套壳 + 多源组合（Tavily + Bocha + Serper + V4） | search / extract / research 全走套壳（**M1 已实装**）| M1 周 1-3 |
| **P1** | qmp 上市文件首爬（kcb + cyb 共 67K）| **可选**：挂 cron 启动首爬 | M3+（用户决定时点）|
| **P1** | qmp 12.2万 实时新闻 | **可选**：news endpoint 调用增量 | M3+ |
| **P2** | qmp 17 子库（政策 / 产业链 / 专利 / 国外 deal）| 暂不做，全走 A 线套壳 | M3-M6（按需）|
| **P3** | 30 家券商研究所自爬 | **不做**（实测 100% 反爬） | M5+ 可选 |
| **P3** | 高校 / 园区 / 集团 / 宏观 | 不做 | M6+ |

### 5.3 30 家券商自爬白名单（M5+ 可选 — 实测全部反爬）

> **2026-04-29 实测结论**：30 家券商主页 + robots audit，**0 家可走 naive HTTP 直接爬**（0 easy / 12 moderate / 26 hard / 100% 反爬）。100% 需要 Playwright 全家桶 + 反爬代理 + 验证码处理。单家从"能爬"到"稳定爬"工时 1-2 周，30 家全做 ~半年人年。
>
> **决策**：M1-M4 完全跳过，所有研报走 A 线 Tavily Search/Extract/Research 套壳。M5+ 客户付费要求专属源时再考虑启动 P3。

如 M5+ 启动，可参考的第一梯队 10 家：中信证券 / 申万宏源 / 中信建投 / 中金公司 / 华泰证券 / 国泰海通 / 招商证券 / 广发证券 / 国信证券 / 兴业证券。第二三梯队（光大 / 东方 / 长江 / 中泰 / 银河 等 20 家）保留为参考清单，不做立即规划。

---

## 六、产品形态

### 6.1 产品架构总览：学 Tavily 双产品 + 投研垂类差异化（4 条产品线）

**ResearchPipe = 中国版 Tavily 但聚焦投研**。借用 Tavily 双产品架构（Search / Research），加投研垂类的差异化（Data / Watch）。

```
┌──────────────────────────────────────────────────────────────────────┐
│  ResearchPipe 4 条产品线                                                │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐                          │
│  │  Search 产品线    │  │  Research 产品线  │   ← 学 Tavily               │
│  │  (同步 / 原料)    │  │  (异步 / 成品)    │                          │
│  │  6 端点 1-5c     │  │  3 端点 30-100c  │                          │
│  └──────────────────┘  └──────────────────┘                          │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐                          │
│  │  Data 产品线      │  │  Watch 产品线     │   ← Tavily 没有，差异化   │
│  │  (毫秒 / 结构化)  │  │  (cron 订阅)      │                          │
│  │  38 端点 0.5-3c  │  │  2 端点 10c/digest│                          │
│  └──────────────────┘  └──────────────────┘                          │
│                                                                      │
│  + 账户管理 3 + 内部运营 1 = 总计约 53 端点                              │
└──────────────────────────────────────────────────────────────────────┘
```

约定：`★` = 差异化旗舰端点。**Credits**（C 列）= 单次调用消耗的 credits。

---

### 6.2 产品线 1：ResearchPipe Search（学 Tavily Search）

> **同步秒级 / 原料供应 / 让 agent 自己合成**

#### 端点表（6 个）

| # | 端点 | 用途 | C | 阶段 |
|---|---|---|---|---|
| S1 | `POST /v1/search` | 通用搜索（type 参数分流：web/news/research/policy/filing）| 1 | M1 |
| S2 | `POST /v1/extract` | 单 URL → 全文（学 Tavily Extract）| 2 | M1 |
| S3 ★ | `POST /v1/extract/research` | **研报字段抽取**（含英→中翻译合并一步）| 5 | M1 |
| S4 ★ | `POST /v1/extract/filing` | 上市文件抽取（5 套 schema）| 3 | M2 |
| S5 | `POST /v1/extract/batch` | 批量 URL 异步抽取（≤100/批）| 内层叠加 | M2 |
| S6 | `GET /v1/jobs/{id}` | 查异步 job 状态（batch + research 共用）| 0 | M2 |

#### 核心参数（学 Tavily）

```json
POST /v1/search
{
  "query": "半导体设备 国产化",
  "type": "research",                        // web / news / research / policy / filing
  "search_depth": "basic",                    // basic (1c) / advanced (2c)
  "include_answer": false,                    // false / "basic" (LLM 短答) / "advanced" (详细)
  "include_raw_content": false,
  "max_results": 20,
  "regions": ["a-share","hk","us","global"],
  "languages": ["zh","en"],
  "time_range": "30d",
  "source_types": ["broker","consulting","vc","overseas_ib"]   // M2 加：限定研报来源类型
}
```

---

### 6.3 产品线 2：ResearchPipe Research（学 Tavily Research）

> **异步多步 LLM 编排 / 成品交付 / output_schema 自定义 / citations 默认带**

#### 端点表（3 个）

| # | 端点 | 用途 | C（mini/pro）| 阶段 |
|---|---|---|---|---|
| R1 ★ | `POST /v1/research/sector` | 赛道全景研究（替代原 sector-snapshot）| 20/50 | M3 |
| R2 ★ | `POST /v1/research/company` | 公司尽调研究（替代原 dd/company）| 20/50 | M3 |
| R3 | `POST /v1/research/valuation` | 估值锚研究（替代原 valuations/anchors）| 20/50 | M3 |

#### 核心参数（学 Tavily Research）

```json
POST /v1/research/sector
{
  "input": "具身智能",                         // 必填
  "time_range": "24m",
  "regions": ["a-share","hk","us"],
  "model": "auto",                             // mini (20c) / pro (50c) / auto
  "output_schema": null,                        // null = 走默认 16 字段 schema；自定义传 JSON Schema
  "citation_format": "numbered",                // numbered / apa / chicago
  "stream": false,                              // false = 异步 poll；true = SSE 流式
  "depth": "standard"                           // summary / standard (默认 12K) / full (25K)
}
```

#### 异步行为（学 Tavily）

```
默认（stream=false）：
  POST /v1/research/sector → HTTP 201 {request_id, status: "pending"}
  GET /v1/jobs/{request_id} → {status: "running"|"completed"|"failed", result: {...}}

stream=true：
  POST /v1/research/sector → HTTP 200 SSE stream
    event: started   → {request_id, model, estimated_seconds: 45}
    event: step      → {step: "searching news", progress: 0.2}
    event: step      → {step: "extracting filings", progress: 0.5}
    event: completed → {result: {...}}
```

#### output_schema 自定义示例

```json
POST /v1/research/company
{
  "input": "宁德时代",
  "output_schema": {
    "properties": {
      "core_thesis":   {"type": "string"},
      "risks":         {"type": "array", "items": {"type": "string"}},
      "peers_count":   {"type": "integer"},
      "next_action":   {"type": "string", "enum": ["buy","hold","sell","unknown"]}
    },
    "required": ["core_thesis", "risks"]
  }
}
```

Research 内部多次搜索 + LLM 合成 + **严格按 schema 输出 + citations 数组（source_url / filing_id / quote）**。

#### research/sector 默认 output_schema（16 字段，详见 6.10 示例）

industry / snapshot_date / executive_summary / research_views / deals / filings / policy_signals / industry_chain / valuation_anchors / news_pulse / key_companies / active_investors / risks / outlook / citations / metadata

#### research/company 默认 output_schema（16 字段）

company_basic / snapshot_date / executive_summary / business_profile / peers_dd / valuation_anchor / filing_risks / financials_summary / founders_background / patent_portfolio / major_investors / recent_news / **red_flags** / outlook / citations / metadata

---

### 6.4 产品线 3：ResearchPipe Data（投研垂类结构化数据，38 端点）

> **同步毫秒级 / qmp_data 直查 / Tavily 没有的护城河**

按 5 类核心实体分组：

#### B. Companies（6 端点）

| # | 端点 | 用途 | C | 阶段 |
|---|---|---|---|---|
| D1 | `POST /v1/companies/search` | 公司搜索（名称/行业/地区/阶段）| 0.5 | M1 |
| D2 | `GET /v1/companies/{id}` | 公司画像（10 字段 M1 必出） | 0.5 | M1 |
| D3 | `GET /v1/companies/{id}/deals` | 该公司所有融资事件 | 1 | M1 |
| D4 | `POST /v1/companies/{id}/peers` | 对标公司 | 2 | M2 |
| D5 | `GET /v1/companies/{id}/news` | 公司相关新闻 | 1 | M1 |
| D6 | `GET /v1/companies/{id}/founders` | 创始团队（默认精简；`deep=true` 出深度背景）★ | 1/3 | M2 |

#### C. Investors（5 端点）

| # | 端点 | 用途 | C | 阶段 |
|---|---|---|---|---|
| D7 | `POST /v1/investors/search` | 机构搜索 | 0.5 | M1 |
| D8 | `GET /v1/investors/{id}` | 机构画像 | 0.5 | M1 |
| D9 | `GET /v1/investors/{id}/portfolio` | 投过的项目 | 1 | M1 |
| D10 | `GET /v1/investors/{id}/preferences` | 投资偏好（行业/轮次画像）| 0.5 | M2 |
| D11 | `GET /v1/investors/{id}/exits` | 退出案例 ★（一级市场新增）| 1 | M2 |

#### Deals（5 端点）

| # | 端点 | 用途 | C | 阶段 |
|---|---|---|---|---|
| D12 | `POST /v1/deals/search` | 融资事件搜索（多维筛选）| 1 | M1 |
| D13 | `GET /v1/deals/{id}` | 单事件详情 | 0.5 | M1 |
| D14 | `POST /v1/deals/timeline` | 公司融资时间线 | 2 | M2 |
| D15 | `POST /v1/deals/overseas` | 海外创投 deal | 2 | M2 |
| D16 | `GET /v1/deals/{id}/co_investors` | co-investor 网络分析 ★（一级市场新增）| 2 | M2 |

#### D. Industries（9 端点）

| # | 端点 | 用途 | C | 阶段 |
|---|---|---|---|---|
| D17 | `POST /v1/industries/search` | 关键词 → 标准行业 tag | 0.5 | M1 |
| D18 | `GET /v1/industries/{id}/deals` | 赛道融资事件 | 1 | M1 |
| D19 | `GET /v1/industries/{id}/companies` | 赛道公司列表 | 1 | M1 |
| D20 | `GET /v1/industries/{id}/chain` | 上下游产业链图谱 | 2 | M2 |
| D21 | `GET /v1/industries/{id}/policies` | 相关政策 + impact_assessment | 1 | M2 |
| D22 | `GET /v1/industries/{id}/tech_roadmap` | 技术路线图 ★（新增）| 3 | M2 |
| D23 | `GET /v1/industries/{id}/key_technologies` | 核心技术清单 + 国产化率 ★（新增）| 2 | M2 |
| D24 | `POST /v1/industries/{id}/maturity` | 技术成熟度（Gartner 曲线）★（新增）| 5 | M3 |
| D25 | `POST /v1/technologies/compare` | 技术路线对比 ★（新增）| 5 | M3 |

#### E. Valuations（4 端点）

| # | 端点 | 用途 | C | 阶段 |
|---|---|---|---|---|
| D26 | `POST /v1/valuations/search` | 估值数据查询 | 1 | M1 |
| D27 | `POST /v1/valuations/multiples` | 行业 PS/PE 倍数 | 1 | M1 |
| D28 | `POST /v1/valuations/compare` | 跨市场对标（A/HK/US 同赛道）| 3 | M2 |
| D29 | `POST /v1/valuations/distribution` | 估值带分布 + 独角兽阈值 ★（一级市场新增）| 2 | M2 |

#### F. Filings（5 端点）

| # | 端点 | 用途 | C | 阶段 |
|---|---|---|---|---|
| D30 | `POST /v1/filings/search` | 文件搜索（公司/类型/时间）| 0.5 | M2 |
| D31 | `GET /v1/filings/{id}` | 文件元数据 + 直链 | 0.5 | M2 |
| D32 ★ | `POST /v1/filings/{id}/extract` | 5 套 schema 字段抽取 | 3 | M2 |
| D33 | `POST /v1/filings/{id}/risks` | 风险点抽取（高/中/低）| 2 | M2 |
| D34 | `POST /v1/filings/{id}/financials` | 5 年财务数据抽取 | 2 | M3 |

#### G. News & Events（3 端点）

| # | 端点 | 用途 | C | 阶段 |
|---|---|---|---|---|
| D35 | `POST /v1/news/search` | 新闻搜索 | 1 | M1 |
| D36 | `POST /v1/news/recent` | 最新新闻流（按行业/公司过滤）| 0.5 | M1 |
| D37 | `POST /v1/events/timeline` | 综合事件时间线（合 deals + filings + news + policy）| 2 | M2 |

#### Tasks（1 端点）

| # | 端点 | 用途 | C | 阶段 |
|---|---|---|---|---|
| D38 | `POST /v1/screen` | 赛道筛选器（多条件 → 公司列表）| 5 | M2 |

---

### 6.5 产品线 4：ResearchPipe Watch（订阅 / cron friendly）

> **Tavily 没有的差异化** —— 公众号 KOL / VC 监控赛道每天 cron 调

| # | 端点 | 用途 | C | 阶段 |
|---|---|---|---|---|
| W1 | `POST /v1/watch/create` | 创建 watchlist（行业/公司/机构组合 + filter）| 0 | M2 |
| W2 | `GET /v1/watch/{id}/digest` | Watchlist 摘要（昨日 deal+ news+ filings + LLM 摘要）| 10 | M2 |

### 6.6 账户管理 + 内部运营

| # | 端点 | 用途 | C |
|---|---|---|---|
| A1 | `GET /v1/me` | 当前 key 信息（档位 + quota） | 0 |
| A2 | `GET /v1/usage` | 用量历史（按端点/日期）| 0 |
| A3 | `GET /v1/billing` | 当月账单预估 | 0 |
| Adm1 | `POST /admin/takedown` | 法务下架（粒度：broker / source_url / filing_id）| — |

---

### 6.7 M1/M2/M3 分阶段上线

| 阶段 | 上线端点 | 客户能完成的事 |
|---|---|---|
| **M1**（4 周）| **Search 3** (S1, S2, S3) + **Data 12**（D1, D2, D3, D5, D7, D8, D9, D12, D13, D17, D18, D19, D26, D27, D35, D36）+ **账户 3** = **20 端点** | 一级 deal 查询 / 公司画像 / 机构画像 / 赛道扫描 / 研报抽取 / 估值倍数 / 实时新闻 |
| **M2** | + Search 3（S4-S6 加 filings）+ Data 18（peers / preferences / chain / policies / tech 维度 / valuations/compare 等）+ Watch 2 + screen + filings 系列 = **+24 端点** | 上市文件抽取 / co-investors / 估值分布 / 技术路线图 / Watch 订阅 / events/timeline |
| **M3** | + Research 3（sector / company / valuation）+ Data 4（filings/financials, industries/maturity, technologies/compare, etc）= **+7 端点** | 旗舰多步研究 / 单次 ¥10+ 感知价值 |

**M1 上线 20 端点 = "投研工具人能跑通完整工作流"的最小闭环**。

### 6.8 实现路径（信息从哪拿，v3 调整）

8 类数据源各自的获取路径（v3：B 线只保 qmp 一级 deal，其他全走 A 线套壳）：

| 数据 | 主路径（M1 实装） | 备选 / M3+ 可选 |
|---|---|---|
| 卖方研报 | **A 线**：Tavily Search 找 PDF → Tavily Extract 抓全文 → DeepSeek V4 抽 11 字段（W1 验证 9/9 schema OK，¥0.027/篇） | M3+ 高频客户专属源时考虑自爬 |
| 多源研报（咨询/协会/VC/海外IB / 大厂研究院 / 媒体）| 同上 + multi_source 模式（Tavily + Bocha + Serper 3 路并发去重）+ V4 一步翻译合并（海外英文 → 中文）| 同上 |
| **一级 deal（国内）** ⭐ | **B 线独家**：qmp `events` 26,757 + weekly_pipeline cron 在跑增量（每周日 11:00）| 不需要套壳 |
| **机构画像** ⭐ | **B 线独家**：qmp `institutions` 5,000 + portfolio | 不需要套壳 |
| **估值数据** ⭐ | **B 线独家**：qmp `valuations` 2,801 + industry_ps_multiples 102 | 不需要套壳 |
| 海外 deal | A 线：Tavily Search 海外 + Serper Google 海外 | M3+ 可选 qmp 国外创投子库 |
| 上市文件 | **A 线套壳**：Tavily Search 找文件 → Tavily Extract 抓全文 → V4 按 5 套 schema 抽（**M1 实时模式**）| **M3+ 可选**：`scrape_qmp_reports.py` 启动首爬（kcb 22.6K + cyb 45K）落库形成飞轮 |
| 政策库 | A 线：Tavily Search + Bocha（M1 实时）| M3+ 可选 qmp 政策子库 |
| 产业链 / 技术维度 | A 线：multi_source 搜索 + V4 综合 | M3+ 可选 qmp 产业链子库 |
| 专利 | A 线：Tavily / Serper 兜底（M1 实时）| M3+ 可选 qmp 专利子库 |
| 实时新闻 | A 线：Bocha + Serper 双发（M1 实时）| M3+ 可选 qmp 12.2 万新闻全量爬 |

**v3 主路径已全部就位**（events / institutions / valuations 已在 weekly_pipeline 跑；其他 9 类全走 M1 已实装的套壳层）→ **M1 完全不缺数据，且无 0% 进度的爬虫任务**。

### 6.9 字段优先级（M1/M2/M3）

#### `companies/get` 字段（Round 3 决策）

- **M1 必出（10 字段）**：基本信息 / 业务描述 / 产品列表 / 创始人+高管 / 融资轮次 / 当前估值 / 投资机构清单 / 员工规模 / 上市状态+招股书链接 / 关联企业
- **M2 加（4 字段）**：竞争对手 / 营收+利润 / 近期媒体提及 / 专利数量+Top5
- **M3 加（1 字段）**：上下游客户/供应商名单（依赖招股书抽取完成）
- **默认行为**：全字段返回 + `exclude_fields=[]` 让客户排除（不用 fields 白名单，agent 不用记字段名）

#### `extract/research` 字段（Round 3 决策）

- **M1 必出（11 字段）**：metadata 6 个（broker / source_type / report_title / report_date / source_url / language）+ 核心抽取 5 个（core_thesis ≤200字 / target_price+币种 / recommendation / key_data_points / risks）
- **M2 加（5 字段）**：business_logic ≤500字 / valuation_assumptions / companies_covered / sector / financial_forecasts
- **M3 加（7 字段）**：industry_outlook / catalyst / quarterly_metrics / supply_chain_view / policy_view / competitor_analysis / analyst_team
- **`include_raw_content` 默认 false**；**`confidence_score` 默认带**

#### 上市文件 5 套 schema（Round 3 决策）

- **M2 头**：prospectus_v1（招股说明书）+ inquiry_v1（问询回复）
- **M2 末**：sponsor_v1（发行保荐书）
- **M3**：audit_v1（审计报告）+ legal_v1（法律意见书）
- **prospectus_v1 M2 必出 9 字段**：company_basic / business_overview / core_products（含营收占比）/ financials_5y_summary / peers_comparison / fundraising_projects / controlling_shareholders / major_risks（5 类分）/ core_technology
- **prospectus_v1 M3 加 5 字段**：customers_suppliers / detailed_financials / related_party_transactions / litigation / management_compensation
- **抽取范围**：整本喂 DeepSeek V4（128K 长上下文一次抽全），单份成本 ¥0.04

#### `policy/match` 字段（Round 3 决策）

- **M2 必出 10 字段**：policy_id / title / issuing_body / policy_type / publish_date / source_url / summary（LLM ≤200字）/ related_industries / **impact_assessment** ★（direction / intensity / time_horizon / rationale）/ key_provisions
- **M3 加 5 字段**：effective_date / full_text / affected_companies / supersedes / confidence_score

### 6.10 关键设计原则（agent 友好）

ResearchPipe API 的 7 条不变量（贯穿所有端点，不可妥协）：

1. **跨实体引用 = 精简 inline + `expand` 参数**（学 Stripe 但更激进）
   - 默认每个嵌套 entity 返 `{id, name, ...top-3-fields}`
   - 客户传 `expand=["investors","filings"]` 拿完整对象

2. **每个 entity 带 `_meta.freshness_status`**
   - `{last_updated_at, data_age_days, freshness_status: fresh|stale|outdated, next_refresh_eta}`
   - 陈旧数据照常返回 + 标 stale，**不强制触发实时刷新**

3. **多源去重 + 字段冲突可见**
   - 实体去重：fuzzy match + 别名表 + LLM 兜底，落 `rp_entity_aliases`
   - 字段冲突：硬编码优先级（qmp 上市文件 > 研报 > Tavily > Bocha），主值用最高优先级
   - 其他版本放 `metadata.alternatives[]`
   - 顶层 `metadata.data_sources_used: [...]` 必带；硬数据字段（估值/营收/财务）单独带 `_source`

4. **错误返回带 `hint_for_agent`** + partial success warnings
   - 硬错误：HTTP 4xx/5xx + JSON `{error: {code, message, retry_after_seconds?, hint_for_agent, documentation_url}}`
   - partial：HTTP 200 + `metadata.partial: true` + `metadata.warnings: []`
   - 错误 code / warning code / hint_for_agent **英文**（给 LLM 看的工程字段最准）

5. **Idempotency-Key + Token Bucket Rate Limit + Cache-Control header**
   - Idempotency-Key：24h 内同 key 同请求只扣一次费
   - Rate limit：60 req/min sustained，允许 burst 10
   - 响应 header：`Cache-Control` / `X-RateLimit-Remaining` / `X-Credits-Cost`

6. **Schema 演进：加字段永远兼容 + 改/删走 v2**
   - `/v1/...` 路径版本号
   - 必填字段全输出（null 也输出 null，不省略 key）
   - 第一次 v2 至少在 M12 之后

7. **API 语言：默认中文 + 工程字段英文**
   - 响应主体默认中文（M2 加 `language=en` 参数）
   - 核心实体名带 `name_en` 英文 alias
   - MCP tool description **英文** + 内嵌中文 examples
   - hint_for_agent / error code / warning code **英文**

### 6.11 单端点示例：`POST /v1/extract/research`

```json
POST /v1/extract/research
Request:
{
  "query": "半导体设备 国产化",
  "time_range": "30d" | "24m" | {"from": "...", "to": "..."},
  "regions": ["a-share", "hk", "us-listed", "global"],
  "languages": ["zh", "en"],
  "max_results": 20,
  "include_raw_content": false
}

Response:
{
  "request_id": "...",
  "results": [
    {
      "broker": "中信证券",
      "broker_country": "CN",
      "report_title": "...",
      "report_date": "2026-04-15",
      "source_url": "...",
      "language": "zh",
      "extracted_fields": {
        "core_thesis": "...",
        "business_logic": "...",
        "valuation_assumptions": {...},
        "key_data_points": [...],
        "risks": [...],
        "target_price": "...",
        "recommendation": "..."
      },
      "raw_content_preview": "..."
    }
  ],
  "metadata": {
    "total_found": 23,
    "data_sources": ["self_db", "tavily", "bocha"],
    "processing_time_ms": 4231,
    "cost_credits": 5
  }
}
```

### 6.12 旗舰端点示例：`POST /v1/research/sector`

```json
{
  "industry": "具身智能",
  "snapshot_date": "2026-04-28",
  "research_views": [...],         // 8 篇券商研报字段抽取
  "deals": {
    "domestic": [...],              // 国内一级 deal
    "overseas": [...],              // 海外 deal
    "summary": {                    // 衍生分析（不暴露原始数据）
      "total_count_24m": 47,
      "total_amount_cny": "210亿",
      "top_5_active_investors": [...],
      "round_distribution": {...}
    }
  },
  "filings": [...],                 // 上市文件字段抽取
  "policy_signals": [...],          // 十五五规划相关
  "industry_chain": {
    "upstream": [...],
    "midstream": [...],
    "downstream": [...]
  },
  "patents": {...},
  "valuation_anchors": {
    "ps_multiples": {...},
    "recent_priced_rounds": [...]
  },
  "news_pulse": [...],
  "metadata": {...}
}
```

**旗舰端点单次调用客户感知价值 ≥ ¥10**，竞品做不到。

### 6.13 字段标准定义（投资垂类 schema）

| 字段名 | 类型 | 说明 | 必填 |
|---|---|---|---|
| broker | string | 出具机构名称 | ✅ |
| broker_country | enum(CN/US/HK/UK/JP/EU) | 出具机构国别 | ✅ |
| report_title | string | 报告标题 | ✅ |
| report_date | date | 发布日期 | ✅ |
| source_url | url | 原文链接 | ✅ |
| language | enum(zh/en) | 原文语言 | ✅ |
| core_thesis | string | 核心观点（≤200 字）| ✅ |
| business_logic | string | 商业逻辑（≤500 字）| ✅ |
| valuation_assumptions | object | 估值假设（PE/PB/DCF 输入）| 可选 |
| key_data_points | array | 关键数据点列表 | ✅ |
| risks | array | 风险提示列表 | ✅ |
| target_price | string | 目标价（含币种）| 可选 |
| recommendation | enum(买入/增持/中性/减持) | 评级 | 可选 |
| companies_covered | array | 涉及公司列表 | 可选 |
| sector | string | 所属行业（标准化）| ✅ |

### 6.14 前端形态：Tavily 范式四件套

前端**不是产品**，是 API 的售前 + 服务窗口。学 Tavily 范式：

```
researchpipe.com/                  → Landing 页（营销 + 简化 Playground）
researchpipe.com/playground        → 交互式 Playground（参数表单 + 多语言代码）
researchpipe.com/docs              → 文档站（OpenAPI 自动生成 + Cookbook）
researchpipe.com/dashboard         → Dashboard（API Keys + 用量 + 账单 + Logs）
```

**M1 起步合并在一个域名下；M3+ 视情况拆 docs / app 子域名。**

#### Landing 页核心模块

- Hero：定位 + 8 类数据源数字证据 + `Get free API key` + `Try in playground`
- Mini Playground（首屏即可玩，无需登录，限频）
- "Built for Cursor / Claude Desktop / Cline / 自家后端" Logo 墙
- 3 个 Use Cases 卡片（探索新赛道 / 跟踪一家公司 / IPO 尽调）→ 点击直跳 Playground 预填参数
- Pricing 摘要 + 完整 Pricing 链接

#### Playground 页核心交互

- 左侧：端点列表（按 9 组分组导航，30+ 端点）
- 中间：参数表单（按选中端点动态生成）+ Run 按钮（Cmd+Enter）+ **预估 Credits 实时显示**
- 右侧：Response 区，多 tab 切换：
  - JSON Raw
  - Code（默认 Python，含 cURL / Node / MCP 配置）
  - Visualization（仅旗舰端点，简单图表）
- 顶部固定：当月 Credits 进度条（`9,847 / 10,000`）

#### Docs 站

- Quickstart（60 秒上手）
- Endpoints 按使用场景分组：
  ```
  🔍 探索新赛道（search/research + sector-snapshot + policy）
  📊 跟踪一家公司（companies/peers + deals/timeline + filings/risks + news）
  💰 估值与对标（valuations/search + multiples + compare）
  🏢 机构与 portfolio（investors/portfolio + preferences）
  🔎 IPO/尽调辅助（filings/extract + dd/company）
  ```
- SDK 指南（Python / Node / MCP）
- Cookbook（差异化护城河）：
  - "30 分钟搭一个公众号选股助手"
  - "用 Cursor + ResearchPipe 写赛道扫描器"
  - "Claude Desktop 里 @researchpipe 做尽调"
  - "Notion 看板接 ResearchPipe webhook"

#### Dashboard 页

- API Keys 管理（多 key + 重新生成 + 删除）
- Usage 趋势图（按端点 / 按日期）
- Recent Logs（最近 100 次调用 + Replay 按钮：一键把参数 prefill 到 Playground）
- Billing（当前档位 + 升级按钮 + 账单历史）

### 6.15 交付物三形态：API + SDK + MCP

ResearchPipe 不只是 HTTP API，而是**三种形态平等交付**：

| 形态 | 用户场景 | M1 上线 |
|---|---|---|
| **HTTP API** | 任何能发请求的工具：Postman / cURL / 自家后端 / n8n / Dify（客户自接）| ✅ |
| **Python SDK** | `pip install researchpipe`；客户在 Cursor / Jupyter / 自家 Python 服务用 | ✅ |
| **Node SDK** | `npm install @researchpipe/sdk`；客户在 Next.js / Express 后端用 | ✅ |
| **MCP Server** | Claude Desktop / Cursor / Cline 直连，`@researchpipe` 即用 | ✅ |
| **OpenAPI 3.0 spec** | 客户喂给 Cursor / Claude Code 自动生成调用代码 | ✅ |
| **Postman Collection** | 客户从 Postman 导入即试 | ✅ |

**MCP Server 是关键差异化**：暴露 ~25 个端点（搜索类 + 数据查询类 + 旗舰任务型，写操作不暴露），让 Claude Desktop / Cursor 用户能直接 `@researchpipe 帮我扫描具身智能赛道`，进入 AI agent 工作流。Tavily 至今没做这件事。

**SDK / MCP 是 PLG 增长的关键**：客户从 `pip install` 到第一次成功调用应该 < 60 秒。Docs 第一屏就是 Quickstart 代码片段。

---

## 七、双线并行战略（v3 调整：A 线主战场 + B 线独家护城河）

> **v3 调整原因（2026-04-29）**：实证 Tavily Extract + V4 抽取 ¥0.027/篇 vs 自爬 PDF + 入库 + LLM 抽 ¥1-2/篇 + 长期维护成本。C 层 30 家券商 100% 反爬。结论：自建数据库飞轮的工程代价 >> 实时套壳的边际成本。M1-M2 完全砍掉自爬，A 线变主战场，B 线只保 qmp 一级 deal 这一条独家护城河。

### 7.1 A 线 vs B 线对比（v3）

| 维度 | A 线：API 套壳 + 多源组合（**主战场**）| B 线：qmp 一级 deal 数据（**唯一护城河**）|
|---|---|---|
| 解决问题 | 即时拿到全网最新研报 / 政策 / 新闻 / 海外 deal | **任何人套壳拿不到的独家**：26K 一级市场融资事件 + 5K 机构 + 2.8K 估值 |
| 上线状态 | M1 已实装（multi_source 模式 + V4 合成层）| M1 已实装（weekly_pipeline cron 在跑增量）|
| 单查询成本 | search ¥0.001-0.005 / extract ¥0.005 / extract+V4 抽 ¥0.027 / research ¥0.5 | ¥0（已落库 PostgreSQL，毫秒级查询）|
| 风险 | API 提供商失效（已加 multi_source fallback）| qmp 账号 ToS（用户处理；M2 切独立账号）|
| 差异化 | 多源组合 + V4 合成层 + 投研 schema | 一级 deal 数据本身就是独家 |

**两条线互补**：A 验证市场要不要 + 提供广覆盖；B 提供任何套壳拿不到的独家一级数据。

### 7.2 阶段时间表（v3）

| 月份 | A 线 | B 线 | 关键里程碑 |
|---|---|---|---|
| **M1**（已就位） | ✅ search / extract / extract-research / research-sector / research-company / research-valuation 全部真接 Tavily + V4 + multi_source | ✅ events 26K / institutions 5K / valuations 2.8K real-time 查询 | Backend + SDK + MCP 三件套 + Docs 已就位（4/29） |
| **M2** | filings/extract / news/recent 接入实时套壳路径；增加批处理端点 extract/batch | 不动（增量持续） | 2-5 家付费客户验证 |
| **M3** | watch/digest cron 友好实装；完整 SSE stream 支持 | **可选**：启动 qmp 上市文件首爬（kcb/cyb），落库 rp_filings | 10 家客户，¥3 万 MRR |
| **M6** | docs / cookbook / community 增长 | **可选**：政策库 / 产业链 / 专利 等 17 子库按需接入 | 30 家客户，¥15 万 MRR |
| **M12** | 多 LLM 投票 / SSE stream / 跨账号配额 | 看用量决定要不要建本地缓存层 | 100 家客户，¥50 万 MRR |

### 7.3 资源分配（v3）

| 阶段 | A 线（套壳 + 组合）| B 线（qmp 数据）| 主要 KPI |
|---|---|---|---|
| M1 | **80%** | 20%（已就位维护）| A 线产品成型 + 客户验证 |
| M2 | 70% | 30% | 付费客户突破 5 家 |
| M3+ | 60% | 40%（**可选启动上市文件首爬**）| 商业化稳定 |

### 7.4 统一路由器（A 线为主路径）

客户调用时不感知后端实现：

```
客户请求
  ↓
路由器分流（按 endpoint type）
  ↓
A. /v1/companies/* /v1/investors/* /v1/deals/* /v1/valuations/* /v1/industries/*
   → B 线 qmp_data 直接 SQL 查询（毫秒级）
   ↓
B. /v1/search /v1/extract /v1/extract/research /v1/research/*
   → A 线套壳：
     ├─ 单源模式（默认）→ Tavily（最快）
     ├─ 多源模式（multi_source=true）→ Tavily + Bocha + Serper 并发
     │                                  → URL 去重 → rank score → partial 容错
     └─ Research 类 → Tavily Search → 5 Tavily Extract 并发 → V4 抽 11 字段
                       → V4 合成 16 字段 schema → 注入 qmp deal 上下文
  ↓
返回客户（带 metadata.data_sources_used + credits_charged + warnings[]）
```

**飞轮效应**（M3+ 可选启用）：客户每调用一次 extract/research，可异步落 `rp_structured_reports`，下次同 URL 命中本地 cache 直接返回。但 M1-M2 不做，避免数据同步 / 一致性问题，全走实时。

### 7.5 关键设计决策：翻译合并到字段抽取一步 ⚠️

**问题**：海外英文研报需要翻译。是先翻译、再抽取（两步）？还是合并一步？

**答案**：合并一步。

**理由**：
1. **省一次 LLM 调用**：成本减半
2. **质量更高**：模型边读边判，能保留专业术语原意
3. **更适合 DeepSeek V4**：长上下文窗口让一步处理可行
4. **DeepSeek V4 价格**：¥0.5/1M-in + ¥1.5/1M-out，是该方案能跑的根本前提

**Prompt 模式**：
```
SYSTEM: 你是投资研究字段抽取专家。从给定研报中精确提取以下字段，
        严格按 JSON schema 输出。
        如原文为英文，所有抽取字段直接输出中文（合并翻译步骤）。

USER: <PDF 全文文本，5K-30K 字符>

ASSISTANT: <严格符合 schema 的 JSON>
```

---

## 八、商业模式

### 8.1 定价结构（Credits 计费 + PLG 漏斗）

| 档位 | 月费 | 月度 Credits | 历史回溯 | 端点权限 | 目标客户 |
|---|---|---|---|---|---|
| **Free** | ¥0 | 100 | 30 天 | A 组（搜索抽取）+ B/C 组基础（无 sector-snapshot/dd）| 注册即用 |
| **Hobby** | ¥99 | 2,000 | 30 天 | + 实时新闻 + watchlist + screen | 个人 KOL / 公众号作者 |
| **Starter** | ¥1,500 | 20,000 | 6 月 | + 上市文件 extract + 对标 | 独立分析师 / 小工作室 |
| **Pro** | ¥5,000 | 80,000 | 12 月 | + sector-snapshot（限频）+ 全字段 | PE/VC 行研 / 财经媒体 |
| **Enterprise** | ¥15,000 | 300,000 | 24 月 | + dd/company + 不限频 + 优先 SLA | 券商 / 大厂战投 |
| **Flagship** | ¥30,000 | 不限 | 不限 | 全端点 + 私有部署 + 字段定制 + 专属 SLA | 头部机构 / 投行 |
| 超额 | ¥0.5 / 100 credits | — | — | — | — |

**Credits 消耗参考**（不同端点不同消耗，让客户灵活选择）：

| 端点类别 | Credits/次 | 示例 |
|---|---|---|
| 列表查询 | 0.5 | companies/search, news/recent |
| 单查询 | 1 | search, deals |
| 抽取类 | 2-5 | extract/research, filings/extract |
| 任务型 | 5-10 | screen, watch/digest |
| 旗舰融合 | 30-50 | sector-snapshot, dd/company |

**关键设计**：Free 档可以频繁玩 search，但跑不动 sector-snapshot（50 credits）—— 天然引导升级。
**¥99 Hobby 档**：一个 ¥99 客户可以 cron 跑 watchlist daily digest（10 credits × 30 天 = 300）+ 1000 次新闻搜索 + 100 次抽取 ≈ 全月 2000 credits，**正好够公众号工作流**。

### 8.2 单位经济测算

**M1-M3（A 线主导）**：
- 单次查询平均成本：¥0.20
- 单次查询定价（按月费均摊）：¥0.30-1.00
- 毛利率：60%

**M3-M6（混合）**：
- sector-snapshot 单次成本：¥0.40（融合 8 类数据 + DeepSeek）
- 客户感知价值：¥10+
- 毛利率：60-75%

**M6+（B 线主导）**：
- 80% 查询走自建库（成本 ¥0.005）
- 20% 查询走 API（成本 ¥0.20）
- 加权平均成本 ¥0.044
- 毛利率 85-92%

### 8.3 财务指标目标

| 指标 | M3 | M6 | M12 |
|---|---|---|---|
| MRR | ¥3 万 | ¥15 万 | ¥50 万 |
| 客户数 | 10 | 30 | 100 |
| 毛利率 | 60% | 75% | 90% |
| 自建库覆盖率 | 30% | 70% | 95% |

---

## 九、风险与应对

### 9.1 法律风险三层防护

**第一层：数据来源合法性**
- ✅ qmp 现有数据：账号合法订阅（研发期使用合规）
- ✅ 上市文件：file_url 直链上交所/深交所官方 CDN（强制公开披露物，最强法律地位）
- ✅ 一级 deal：基于公开信息聚合 + 衍生分析
- ❌ 不爬 Wind 终端 / 慧博付费墙后内容

**第二层：商业化前账号分离**
- 当前账号绑定 `muye.m.li@shell.com`（壳牌资本-机构版），用于商业项目可能违反企名片 ToS（机构版限单组织内部使用）+ 壳牌 IT 政策
- **应对方案**：
  1. M1-M3 研发期：继续使用现账号迭代
  2. M3 末（首批付费客户出现前）：申请独立企名片企业账号（年费约 ¥5-10 万）
  3. M3-M4 切换：新账号同步流水线 → 旧数据保留为研发存档但停止增量

**第三层：输出形态合规**
- **永远不输出原始数据库副本** —— API 响应只含衍生分析（聚合统计、向量推荐、字段抽取后的归纳）
- 上市文件输出必带 source_url，标注"原文请访问交易所官网"
- 自爬券商研报：只爬官网公开页 + 引用式展示 + 标注源链接，绝不爬慧博/东方财富等聚合站点
- 用户协议明确："指引性聚合服务，不替代原始数据"
- 法务下架接口（POST /admin/takedown）：人工触发后立即从查询结果过滤

### 9.2 法律红线（绝不碰）

- ❌ 不爬付费墙后的内容
- ❌ 不爬 Wind/Choice/iFinD 终端导出物
- ❌ 不爬注册账户专享内容
- ❌ 不全文复制研报到自有页面
- ❌ 商业化前不切换独立账号（强制门槛）

### 9.3 核心风险清单

| 风险 | 概率 | 影响 | 应对措施 |
|---|---|---|---|
| 客户验证失败（无人付费）| 中 | 致命 | M1 强制 5 家用户访谈 + 试用，结果不行立即调整定位 |
| Tavily 涨价 / 封禁中国客户 | 低 | 高 | 多渠道架构 + 自建库逐步替代 |
| 法律警告（券商/企名片函）| 中 | 高 | 三层防护已就位 + 法务下架接口 |
| 反爬升级 | 高 | 中 | Playwright + IP 池 + 失败自动 fallback API |
| GeeTest 验证码升级 | 高 | 中 | refresh_token.py 已有交互式重登流程 |
| LLM 抽取质量不稳 | 中 | 中 | quality_score + 多模型 fallback + 人工 spot check |
| 大厂下场（Wind 加 LLM）| 低（短期）| 高（长期）| **窗口期 1-2 年**——速度 + 客户群差异化 |

### 9.4 客户验证不通过的转向方案

如果第 1 个月 5 家试用都不付费，候补客户群优先级：
1. 小型券商（用不起 Wind 但需要竞品研报覆盖）
2. 高校金融研究中心、商学院
3. 二级市场私募（自上而下选股需研报支持）
4. 海外华人投资者（中文 + 海外覆盖是真痛点）

如果四个候补群都验证失败，停止 B 线投入，A 线缩成低价工具型产品（¥299/月），转向 to C 长尾。

---

## 十、关键决策记录

| 日期 | 决策 | 理由 |
|---|---|---|
| 2026-04-28 | 砍掉 Cloudsway / Brave | 与 Bocha / Serper 完全功能重叠 |
| 2026-04-28 | A 线最终留 4 件套（Tavily/Bocha/Serper/Firecrawl）| 覆盖中英文搜索 + 全文抓取，无冗余 |
| 2026-04-28 | 翻译合并到字段抽取一步 | 省一次 LLM 调用 + 模型边读边判质量更高 |
| 2026-04-28 | 主 LLM 选 DeepSeek V4 | 中文质量好、价格便宜（¥0.5/1M-in）、长上下文 |
| 2026-04-28 | A+B 双线并行 | A 验证市场，B 建壁垒，互补 |
| 2026-04-28 | **不做对比矩阵 / 投决建议** | 那是 Agent 不是产品；卖 API 才是基建定位 |
| 2026-04-28 | 自爬只走券商官网公开页 | 法律安全 + 反爬弱 + 增量稳定 |
| 2026-04-28 | **上市文件升为 P0 数据源** | 6.7 万份 + 法律安全 + PE/VC 真实工作流匹配 |
| 2026-04-28 | **自爬 30 家券商降为 P2** | qmp 已有等效或更好数据 + 法律风险更低 |
| 2026-04-28 | sector-snapshot 设为旗舰端点 | 多源融合是真正的差异化 |
| 2026-04-28 | 商业化前必须分离账号 | 壳牌邮箱 + 机构版 ToS 不可商业化转售 |
| 2026-04-28 | 永久衍生分析路线 | 法律 + 不可复制双重保险 |
| 2026-04-28 | **目标客户重定位为"投研工具人"** | 个人创业者 / 投资白领 / 投资机构 都在自己手搓投研 APP；ResearchPipe 是他们的一站式 API 信息源 |
| 2026-04-28 | **三形态平等交付：API + SDK + MCP** | SDK / MCP 是 PLG 增长关键，让客户 60 秒上手；MCP 占领 AI agent 工作流生态位 |
| 2026-04-28 | **加 Free + Hobby 两档（¥0 / ¥99）** | 让"投研白领下班手搓 APP"场景跑起来，PLG 增长引擎；不为赚钱，为自来水 |
| 2026-04-28 | **计费单位改为 Credits（不是调用次数）** | 不同端点消耗不同 credits（0.5-50），定价灵活；端点成本调整不影响客户感知 |
| 2026-04-28 | **40 端点 / 9 组** | 围绕 5 类核心对象（Companies/Investors/Industries/Filings/Events）+ 4 类操作 + 5 旗舰任务型 |
| 2026-04-28 | **前端学 Tavily 范式四件套**（Landing/Playground/Docs/Dashboard）| 投研客户都会读 docs + 复制代码；前端不是产品，是 API 售前 + 服务窗口 |
| 2026-04-28 | **不做 Coze / Dify / n8n 第三方平台插件** | 客户用 SDK / MCP 自接，比平台插件灵活；聚焦核心 API + SDK + MCP 三形态 |
| 2026-04-28 | **加 watchlist 系列端点（#35-36）** | 个人创业者公众号场景必需；配 cron 后用户粘性最强 |
| 2026-04-28 | **加 events/timeline 端点（#31）** | 客户场景"事件追踪"高频；融合 deals + filings + news + policy 时间序列 |
| 2026-04-28 | **加 screen 端点（#34）独立** | 替代客户"打开 Wind 找筛选器"；多条件 + 排序 + 翻页是任务型，与 search 语义不同 |
| 2026-04-28 | **MCP Server 暴露 ~25 端点** | 搜索 + 数据查询 + 旗舰任务型；写操作（watchlist 创建）不暴露给 MCP |
| 2026-04-28 | **v3 产品架构：学 Tavily 双产品 + 投研垂类差异化** | 中国版 Tavily 但聚焦投研：4 条产品线（Search 同步 / Research 异步 / Data 结构化 / Watch 订阅）|
| 2026-04-28 | **目标用户聚焦 A+D 群** | 手搓 Agent 大军 = Cursor/Cline/Claude Code（A）+ Claude Desktop/Cursor MCP（D）；不抓 LangChain 框架党 / Coze 拖拽党 / 投研创业者 E 群（后置）|
| 2026-04-28 | **API 双模式：HTTP/SDK 细 + MCP 8 智能 tool** | A 群 HTTP/SDK 走 50 个细端点；D 群 MCP 暴露 8 个中粒度 tool（按"实体+任务"分组）|
| 2026-04-28 | **Research output_schema 完全自定义** | 学 Tavily Research 的 D 选项：客户传 JSON Schema → 严格按 schema 输出 + citations 默认带 + model 三档（mini 20c / pro 50c / auto）|
| 2026-04-28 | **Research 异步：默认 poll + 可选 SSE stream** | 学 Tavily 双模式（B）；MCP Server 内部封装 poll，对 D 群体感觉是同步 |
| 2026-04-28 | **错误处理：自定义 JSON + hint_for_agent + partial warnings** | hint_for_agent 用英文（LLM 最准）+ partial success 在 metadata.warnings 数组 |
| 2026-04-28 | **Schema 演进：加字段兼容 + 改/删走 v2** | 规则简单可预期 / v1 至少保 12 个月 / 必填字段全输出 null 也输出 |
| 2026-04-28 | **文档对 LLM 友好：B+C 部分** | llms.txt + llms-full.txt + 每页 .md + system prompt 模板（不做 RAG MCP tool / 不做 codegen 端点）|
| 2026-04-28 | **Cache + Idempotency + Token Bucket Rate Limit** | Idempotency-Key 防重复扣费；burst 10 友好 agent 突发；Cache-Control / X-RateLimit / X-Credits header |
| 2026-04-28 | **跨实体精简 inline + expand 参数** | 学 Stripe 但更激进（默认精简 inline，client expand 完整）—— 投研 agent "一次决策需多维信息" |
| 2026-04-28 | **每 entity 带 `_meta.freshness_status`** | fresh/stale/outdated 三档；陈旧数据照常返回不强制刷新（避免 API 成本爆炸）|
| 2026-04-28 | **多源去重：fuzzy + 别名 + LLM 兜底** | 落 `rp_entity_aliases` 表；字段冲突主值用硬编码优先级（qmp 上市 > 研报 > Tavily > Bocha），alternatives 在 metadata |
| 2026-04-28 | **API 语言：默认中文 + 工程字段英文** | 响应主体中文 / MCP tool description 英文 + 中文 examples / hint_for_agent / error code 英文 |
| 2026-04-28 | **一级市场聚焦** | 完全不做二级市场（实时行情/量化/技术分析）；新增端点：deals/co_investors / investors/exits / valuations/distribution / companies/founders deep mode |
| 2026-04-28 | **行业/技术维度强化** | broker_country 改 source_type（broker/consulting/association/corporate_research/vc/overseas_ib/media）+ 新增 industries/tech_roadmap / key_technologies / maturity / technologies/compare |
| 2026-04-28 | **政策匹配的 impact_assessment 是灵魂** | LLM 评估 direction / intensity / time_horizon / rationale —— 投研客户最想知道"这政策对我的赛道是利好还是利空"|
| 2026-04-28 | **research/sector 默认 16 字段 schema** | 含 executive_summary / key_companies（一级市场加近期融资+估值+投资方）/ active_investors / risks / outlook + citations |
| 2026-04-28 | **research/company 默认 16 字段 schema** | red_flags 字段是差异化（创始人争议 / 股权稀释 / 历史 deal 价格异常 / 关联交易），VC 真实尽调必看 |
| 2026-04-28 | **招股说明书 M2 9 字段 / M3 5 字段 + 整本喂 LLM** | 128K 长上下文优势，单份成本 ¥0.04，不分段聚合 |

---

**PRD 文档结束。配套 EDD 见同目录。**
