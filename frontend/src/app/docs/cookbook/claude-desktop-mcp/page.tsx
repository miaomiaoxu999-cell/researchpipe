export default function ClaudeDesktopMCP() {
  return (
    <>
      <h1 className="font-serif text-[36px] tracking-tight text-ink">Claude Desktop + MCP 30 秒接入</h1>
      <p className="text-[15px] text-muted mt-2 mb-8">让 Claude Desktop 直接 @researchpipe 做投研。</p>

      <h2>Step 1 - 拿 API key</h2>
      <p>rp.zgen.xin/dashboard → Generate new API key</p>

      <h2>Step 2 - 编辑 Claude Desktop config</h2>
      <ul>
        <li>macOS：<code>~/Library/Application Support/Claude/claude_desktop_config.json</code></li>
        <li>Windows：<code>%APPDATA%\Claude\claude_desktop_config.json</code></li>
      </ul>

      <pre className="bg-cream border border-line p-4 my-3 overflow-x-auto">
        <code className="font-mono text-[12.5px]">{`{
  "mcpServers": {
    "researchpipe": {
      "command": "npx",
      "args": ["-y", "@researchpipe/mcp-server"],
      "env": {
        "RESEARCHPIPE_KEY": "rp-..."
      }
    }
  }
}`}</code>
      </pre>

      <h2>Step 3 - 重启 Claude Desktop</h2>
      <p>看到 hammer 图标，点开 → 8 个 <code>researchpipe_*</code> tools 就绪。</p>

      <h2>Step 4 - 自然语言调用</h2>
      <p>试这些 prompt：</p>
      <ul>
        <li>"用 @researchpipe 帮我把具身智能赛道做一次全景研究，重点看头部公司估值"</li>
        <li>"@researchpipe 看下宁德时代的 red flags 有什么"</li>
        <li>"@researchpipe 把这篇研报抽成结构化字段：[URL]"</li>
        <li>"@researchpipe 高瓴最近 6 个月在哪些赛道布的局？"</li>
      </ul>

      <h2>常见问题</h2>
      <h3>看不到 hammer 图标？</h3>
      <p>检查 (a) JSON 格式是否合法 (b) RESEARCHPIPE_KEY 是否填了 (c) 重启 Claude Desktop（不只是关窗口）。</p>
      <h3>tool 调用很慢？</h3>
      <p>research_* 是异步的，30-90 秒正常。MCP server 内部自动 poll。</p>
      <h3>怎么看用了多少 credits？</h3>
      <p>tool 返回 JSON 里 metadata.credits_charged 就是。月度看 rp.zgen.xin/dashboard/usage。</p>
    </>
  );
}
