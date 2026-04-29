export default function N8nWatchDigest() {
  return (
    <>
      <h1 className="font-serif text-[36px] tracking-tight text-ink">n8n + Watch digest 公众号 cron</h1>
      <p className="text-[15px] text-muted mt-2 mb-8">公众号 KOL 必看：cron 跑赛道 digest，自动生成日报草稿。</p>

      <h2>Step 1 - n8n 准备</h2>
      <ul>
        <li>n8n self-hosted 或 cloud</li>
        <li>Credentials → Add → "HTTP Header Auth" → Name <code>Authorization</code> Value <code>Bearer rp-...</code></li>
      </ul>

      <h2>Step 2 - Workflow 拓扑</h2>
      <pre className="bg-cream border border-line p-4 my-3 overflow-x-auto">
        <code className="font-mono text-[12.5px]">{`Schedule (cron 7:00) →
  HTTP Request (GET /v1/watch/{id}/digest) →
  Set (extract executive_summary + top deals) →
  HTTP Request (POST /v1/extract/research for top URL) →
  Function (format as 公众号 markdown) →
  Sticky Note: Manual review →
  HTTP Request (公众号草稿 API)`}</code>
      </pre>

      <h2>Step 3 - 创建 watchlist</h2>
      <pre className="bg-cream border border-line p-4 my-3 overflow-x-auto">
        <code className="font-mono text-[12.5px]">{`curl -X POST https://rp.zgen.xin/v1/watch/create \\
  -H "Authorization: Bearer rp-..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "AI 赛道日报",
    "industries": ["人工智能"],
    "company_ids": [],
    "investor_ids": [],
    "cron": "0 7 * * *"
  }'

# → { "id": "watch_xyz123", ... }`}</code>
      </pre>

      <h2>Step 4 - n8n HTTP node 取 digest</h2>
      <p>URL: <code>https://rp.zgen.xin/v1/watch/{`{{$node.Schedule.json.watch_id}}`}/digest</code></p>
      <p>Method: GET</p>
      <p>Auth: 用 Step 1 的 credential</p>

      <h2>Step 5 - 公众号草稿格式化</h2>
      <pre className="bg-cream border border-line p-4 my-3 overflow-x-auto">
        <code className="font-mono text-[12.5px]">{`// n8n Function node:
const digest = $input.first().json;
const md = \`
# AI 赛道日报 \${new Date().toISOString().slice(0,10)}

## 昨日动态
\${digest.summary}

## 重点 deal
\${(digest.items || []).slice(0,5).map(d => \`- \${d.company_name} \${d.round}\`).join('\\n')}

🔗 数据来源：投研派 ResearchPipe
\`;

return [{ json: { content: md } }];`}</code>
      </pre>

      <h2>成本估算</h2>
      <p>每次 digest = 10 credits ≈ ¥0.05。每天 1 次 × 30 天 = ¥1.5/月。</p>
    </>
  );
}
