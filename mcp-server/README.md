# @researchpipe/mcp-server

MCP server exposing **ResearchPipe** (China-focused investment research API) as 8 high-level tools to Claude Desktop / Cursor / Cline.

## Configure (Claude Desktop)

`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "researchpipe": {
      "command": "npx",
      "args": ["-y", "@researchpipe/mcp-server"],
      "env": {
        "RESEARCHPIPE_KEY": "rp-..."
      }
    }
  }
}
```

Restart Claude Desktop. You should see a hammer icon — click it and 8 `researchpipe_*` tools appear.

## Tools

| Tool | What it does |
|---|---|
| `researchpipe_search` | Web / news / research / policy / filing search |
| `researchpipe_extract` | Single URL → clean text |
| `researchpipe_extract_research` | URL → 11 structured research-report fields (translates EN→ZH inline) |
| `researchpipe_research_sector` | Deep async sector study (16 default fields) |
| `researchpipe_research_company` | Deep async company DD (16 fields including red_flags) |
| `researchpipe_company_data` | Fast company slices: profile / deals / peers / news / founders |
| `researchpipe_industry_data` | Industry data: deals / companies / chain / policies / tech_roadmap |
| `researchpipe_watch` | Create or digest a watchlist subscription |

## Example prompts

```
@researchpipe 用具身智能赛道做个全景研究
@researchpipe 帮我对宁德时代做一次尽调，重点看红旗
@researchpipe 把这篇研报抽成结构化字段：https://...
```

## Dev

```bash
git clone https://github.com/researchpipe/mcp-server
cd mcp-server
npm install
npm run build
RESEARCHPIPE_KEY=rp-... node dist/index.js  # exits with 1 + config hint if no key
```

## License

MIT
