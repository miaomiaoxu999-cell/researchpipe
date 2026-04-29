# ResearchPipe Agent UI

A clean, MIT-licensed chat interface for Chinese investment research, powered by [ResearchPipe](https://rp.zgen.xin) — 14k+ broker reports, qmp 一级市场 deal data, and LLM-driven multi-tool synthesis.

Inspired by Tavily's research playground; tuned for Chinese (二级 + 一级) investment research workflows.

![ResearchPipe Agent UI](docs/screenshot.png)

## What it does

- **Ask any Chinese investment-research question** in natural language
- The agent picks the right ResearchPipe tool(s) — corpus semantic search, qmp deals, company lookup, web fallback
- Streams back a structured answer with **inline `[1][2][3]` citations** to actual broker reports
- Click any citation to jump to the source card (broker, date, page, snippet)

## 60-second setup

```bash
# 1. Unzip / clone
unzip researchpipe-agent-ui-0.1.0.zip
cd researchpipe-agent-ui

# 2. Install
npm install

# 3. Set your key (free demo key works for trials)
cp .env.example .env.local
# Edit .env.local and set NEXT_PUBLIC_RP_API_KEY

# 4. Run
npm run dev
# → http://localhost:3001
```

## Configuration

| Env var | Default | Required | Notes |
|---|---|---|---|
| `NEXT_PUBLIC_RP_API_KEY` | `rp-demo-public` | yes | Get yours at https://rp.zgen.xin |
| `NEXT_PUBLIC_RP_BACKEND_URL` | `https://rp.zgen.xin` | no | Self-host: point to your local backend |

The demo key is rate-limited (~5 queries / hour / IP). For unlimited use, sign up for a personal key.

## Architecture

```
Browser (this app)
  │
  │  POST /v1/agent/ask  (SSE stream)
  ▼
ResearchPipe backend
  │
  ├─ deepseek-v4 (LLM tool-call orchestration)
  ├─ corpus_db   (14k 研报 metadata + 1M chunks pgvector)
  ├─ qmp_data    (26K 融资事件 / 5K 机构)
  ├─ Tavily      (web fallback)
  └─ multi_search (Tavily + Bocha + Serper)
```

The UI is a thin shell — all the work happens server-side via the SSE-streamed `/v1/agent/ask` endpoint. Update the agent on the server, no need to redistribute the UI.

## Customizing

Two files do most of the work:

- `src/components/AgentChat.tsx` — chat layout, citation rendering, SSE state machine
- `src/lib/sse-client.ts` — SSE parser for `/v1/agent/ask` events

Want different sample queries? Edit `SAMPLE_QUERIES` in `AgentChat.tsx`.
Want a different brand color? Edit `tailwind.config.ts` (`accent` color).
Want to render tool calls differently? Edit `src/components/ToolCallCard.tsx`.

## License

MIT — fork it, ship it, sell it. We just appreciate a backlink to https://rp.zgen.xin if you're feeling generous.
