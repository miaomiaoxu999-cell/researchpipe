export default function Errors() {
  return (
    <>
      <h1 className="font-serif text-[40px] tracking-tight text-ink">Errors & rate limits</h1>
      <p className="text-[15px] text-muted mt-2 mb-10">所有错误带 <code>hint_for_agent</code> —— LLM 调用方可基于此决策下一步。</p>

      <h2>错误格式</h2>
      <pre className="bg-cream border border-line p-4 my-3 overflow-x-auto">
        <code className="font-mono text-[12.5px]">{`{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Rate limit: 60 req/min + burst 10. Retry in 5s.",
    "retry_after_seconds": 5,
    "hint_for_agent": "Wait 5 seconds and retry. Pass Idempotency-Key header to safely retry without double-charge.",
    "documentation_url": "https://rp.zgen.xin/docs/errors/rate_limit_exceeded"
  }
}`}</code>
      </pre>

      <h2>错误 code 表</h2>
      <table className="w-full text-[13.5px] my-3 border border-line">
        <thead className="bg-cream">
          <tr>
            <th className="text-left py-2 px-3">HTTP</th>
            <th className="text-left py-2 px-3">Code</th>
            <th className="text-left py-2 px-3">Hint summary</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-t border-line"><td className="px-3 py-2">401</td><td className="px-3 py-2 font-mono">auth_invalid</td><td className="px-3 py-2">Set Authorization: Bearer rp-...</td></tr>
          <tr className="border-t border-line"><td className="px-3 py-2">404</td><td className="px-3 py-2 font-mono">quota_resource_not_found</td><td className="px-3 py-2">Use search endpoint to find IDs first.</td></tr>
          <tr className="border-t border-line"><td className="px-3 py-2">422</td><td className="px-3 py-2 font-mono">validation_failed</td><td className="px-3 py-2">Required field missing — check schema.</td></tr>
          <tr className="border-t border-line"><td className="px-3 py-2">422</td><td className="px-3 py-2 font-mono">extract_empty</td><td className="px-3 py-2">URL may be JS-rendered; try /v1/search first.</td></tr>
          <tr className="border-t border-line"><td className="px-3 py-2">429</td><td className="px-3 py-2 font-mono">rate_limit_exceeded</td><td className="px-3 py-2">Wait retry_after_seconds; pass Idempotency-Key.</td></tr>
          <tr className="border-t border-line"><td className="px-3 py-2">402</td><td className="px-3 py-2 font-mono">credits_exceeded</td><td className="px-3 py-2">Top up at /dashboard/billing.</td></tr>
          <tr className="border-t border-line"><td className="px-3 py-2">502</td><td className="px-3 py-2 font-mono">upstream_failure</td><td className="px-3 py-2">Retry exponentially; SDK auto-retries 3×.</td></tr>
          <tr className="border-t border-line"><td className="px-3 py-2">504</td><td className="px-3 py-2 font-mono">upstream_timeout</td><td className="px-3 py-2">Same as 502.</td></tr>
          <tr className="border-t border-line"><td className="px-3 py-2">500</td><td className="px-3 py-2 font-mono">internal_error</td><td className="px-3 py-2">Our side; please contact support.</td></tr>
        </tbody>
      </table>

      <h2>Partial success</h2>
      <p>多源融合 API <code>partial=true</code> 是常态。HTTP 200 + <code>metadata.warnings[]</code>。</p>
      <pre className="bg-cream border border-line p-4 my-3 overflow-x-auto">
        <code className="font-mono text-[12.5px]">{`{
  "results": [...],
  "metadata": {
    "partial": true,
    "warnings": [
      {
        "code": "data_source_unavailable",
        "source": "tavily",
        "message": "Web search upstream returned 503; falling back to secondary source",
        "hint_for_agent": "Result is still usable. If you need cross-source coverage, retry in 30s with same Idempotency-Key."
      }
    ]
  }
}`}</code>
      </pre>

      <h2>Rate limits</h2>
      <ul className="list-disc ml-6">
        <li><strong>60 req/min sustained + burst 10</strong>（token bucket per API key）</li>
        <li>响应头 <code>X-RateLimit-Limit / Remaining / Reset</code></li>
        <li>SDK 自动重试 429（按 <code>retry_after_seconds</code>）</li>
      </ul>

      <h2>Idempotency</h2>
      <p>传 <code>Idempotency-Key: &lt;uuid&gt;</code> header → 24h 内同 key + 同 body 只扣一次费，安全重放。SDK 自动注入 UUID。</p>

      <h2>Caching</h2>
      <ul className="list-disc ml-6">
        <li>响应头 <code>Cache-Control: max-age=N</code> 让 SDK 知道缓存多久</li>
        <li>Search 系列 5-15 分钟 / Research 系列 24 小时 / Data 系列 1 小时</li>
      </ul>
    </>
  );
}
