export default function Quickstart() {
  return (
    <>
      <h1 className="font-serif text-[40px] tracking-tight text-ink">Quickstart</h1>
      <p className="text-[15px] text-muted mt-2 mb-10">60 秒从 0 到第一次成功调用</p>

      <h2>1. 拿 API key</h2>
      <p>注册账号 → Dashboard → "Generate new API key"。Free 档每月 100 credits，无信用卡。</p>

      <h2>2. 第一次调用</h2>

      <h3>Python（推荐）</h3>
      <pre className="bg-cream border border-line p-4 my-3 overflow-x-auto">
        <code className="font-mono text-[12.5px]">{`pip install researchpipe

# search.py
from researchpipe import ResearchPipe

rp = ResearchPipe(api_key="rp-...")
r = rp.search(query="具身智能 融资 2026", max_results=5)
for hit in r["results"]:
    print(hit["title"], hit["url"])`}</code>
      </pre>

      <h3>cURL</h3>
      <pre className="bg-cream border border-line p-4 my-3 overflow-x-auto">
        <code className="font-mono text-[12.5px]">{`curl -X POST https://rp.zgen.xin/v1/search \\
  -H "Authorization: Bearer rp-..." \\
  -H "Content-Type: application/json" \\
  -d '{"query":"具身智能 2026","max_results":5}'`}</code>
      </pre>

      <h3>Node</h3>
      <pre className="bg-cream border border-line p-4 my-3 overflow-x-auto">
        <code className="font-mono text-[12.5px]">{`npm install @researchpipe/sdk

import { ResearchPipe } from "@researchpipe/sdk";
const rp = new ResearchPipe({ apiKey: process.env.RESEARCHPIPE_KEY });
const r = await rp.search({ query: "具身智能 2026" });`}</code>
      </pre>

      <h2>3. 试一个旗舰端点</h2>
      <p>抽研报字段（11 个结构化字段一键抽出）：</p>
      <pre className="bg-cream border border-line p-4 my-3 overflow-x-auto">
        <code className="font-mono text-[12.5px]">{`r = rp.extract_research(url="https://...path/to/report.pdf")
print(r["extraction"]["core_thesis"])
print(r["extraction"]["target_price"])
print(r["extraction"]["key_data_points"])`}</code>
      </pre>

      <h2>4. 下一步</h2>
      <ul>
        <li>试 <a href="/playground">Playground</a> 看 50+ 端点</li>
        <li>看 <a href="/docs/cookbook/cursor-sector-scanner">Cookbook</a> 30 分钟搭出第一个完整工具</li>
        <li>装 <a href="/docs/sdks#mcp">MCP Server</a> 让 Claude Desktop 自然语言调用</li>
      </ul>
    </>
  );
}
