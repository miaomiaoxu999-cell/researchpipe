export default function SDKs() {
  return (
    <>
      <h1 className="font-serif text-[40px] tracking-tight text-ink">SDKs</h1>
      <p className="text-[15px] text-muted mt-2 mb-10">三种形态平等交付：HTTP / Python / Node / MCP Server.</p>

      <h2>Python SDK</h2>
      <pre className="bg-cream border border-line p-4 my-3 overflow-x-auto">
        <code className="font-mono text-[12.5px]">{`pip install researchpipe

from researchpipe import ResearchPipe

rp = ResearchPipe(api_key="rp-...")
r = rp.search(query="...")
r = rp.extract_research(url="...")
r = rp.research_sector(input="具身智能")  # 自动 poll
r = rp.companies_get("comp_2x9bka")`}</code>
      </pre>
      <p>异步用法：<code>from researchpipe import AsyncResearchPipe</code></p>

      <h2>Node SDK</h2>
      <pre className="bg-cream border border-line p-4 my-3 overflow-x-auto">
        <code className="font-mono text-[12.5px]">{`npm install @researchpipe/sdk

import { ResearchPipe } from "@researchpipe/sdk";

const rp = new ResearchPipe({ apiKey: process.env.RESEARCHPIPE_KEY });
const r = await rp.search({ query: "..." });`}</code>
      </pre>

      <h2 id="mcp">MCP Server (Claude Desktop / Cursor / Cline)</h2>
      <p>把 ResearchPipe 装进 Claude Desktop / Cursor，自然语言调用 8 个智能 tool。</p>
      <pre className="bg-cream border border-line p-4 my-3 overflow-x-auto">
        <code className="font-mono text-[12.5px]">{`# ~/Library/Application Support/Claude/claude_desktop_config.json (macOS)
# %APPDATA%\\Claude\\claude_desktop_config.json (Windows)

{
  "mcpServers": {
    "researchpipe": {
      "command": "npx",
      "args": ["-y", "@researchpipe/mcp-server"],
      "env": { "RESEARCHPIPE_KEY": "rp-..." }
    }
  }
}`}</code>
      </pre>
      <p>重启 Claude Desktop，看到 hammer 图标 → 8 个 <code>researchpipe_*</code> tools。</p>

      <h3>8 个 MCP tools</h3>
      <ul className="list-disc ml-6">
        <li><code>researchpipe_search</code> — Web/news/research/policy/filing 搜索</li>
        <li><code>researchpipe_extract</code> — URL → 干净文本</li>
        <li><code>researchpipe_extract_research</code> — 研报 → 11 字段（自动英→中翻译）</li>
        <li><code>researchpipe_research_sector</code> — 异步赛道全景研究</li>
        <li><code>researchpipe_research_company</code> — 异步公司尽调（含 red_flags）</li>
        <li><code>researchpipe_company_data</code> — 公司画像 / deals / peers / news / founders</li>
        <li><code>researchpipe_industry_data</code> — 行业 deals / 公司 / 产业链 / 政策 / 技术路线</li>
        <li><code>researchpipe_watch</code> — 创建 / 拉取 watchlist digest</li>
      </ul>

      <h2>OpenAPI / Postman</h2>
      <ul>
        <li><a href="/openapi.json">OpenAPI 3.0 spec</a> — 喂给 Cursor / Claude Code 自动生成调用代码</li>
        <li>Postman Collection — 通过 OpenAPI 一键导入</li>
      </ul>
    </>
  );
}
