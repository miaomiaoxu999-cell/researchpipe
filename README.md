# ResearchPipe · 投研派

**Investment-research API · SDK · MCP — 50+ endpoints purpose-built for AI agents covering Chinese primary & secondary markets.**

[Try the agent →](https://rp.zgen.xin/agent) · [API Docs](https://rp.zgen.xin/docs) · [Get a key](https://rp.zgen.xin)

---

## What's inside

| Component | Path | Description |
|---|---|---|
| **Backend** | [`backend/`](./backend) | FastAPI · 50+ endpoints · pgvector · multi-source search |
| **Frontend** | [`frontend/`](./frontend) | Next.js Landing + Playground + Docs + Dashboard + `/agent` chat + `/admin` console |
| **Agent UI** | [`agents/researchpipe-agent-ui/`](./agents/researchpipe-agent-ui) | Open-source MIT-licensed chat shell — clone or download zip |
| **Python SDK** | [`sdk-python/`](./sdk-python) | `pip install researchpipe` |
| **MCP Server** | [`mcp-server/`](./mcp-server) | `npx @researchpipe/mcp-server` |

## Stack

- **Backend**: Python 3.12, FastAPI, asyncpg, uvicorn
- **Vector DB**: PostgreSQL 15 + pgvector (1024-dim bge-m3 embeddings, ivfflat ANN)
- **Embedding / Rerank**: SiliconFlow (BAAI/bge-m3 + bge-reranker-v2-m3, free tier)
- **LLM**: Aliyun Bailian DeepSeek-V4 (function calling)
- **Search**: Tavily + Bocha + Serper multi-source dedup
- **Frontend**: Next.js 14 (App Router), Tailwind, McKinsey-inspired editorial design
- **Auth**: Bearer API key + per-key token bucket rate limit

## Data assets

- **2026 研报合集**: 14,928 PDFs from 95+ Chinese brokers (中信建投 / 国金 / 广发 / Morgan Stanley / UBS / etc.) — chunked & embedded into ~917k chunks for semantic search
- **qmp_data**: 26K+ primary-market funding events / 5K+ institutions / 2.8K valuations — read-only, weekly cron updates upstream

## Highlights

- ✅ **Agent SSE endpoint** (`POST /v1/agent/ask`) — LLM tool-call orchestration with 8 tools, streams `tool_call` / `tool_result` / `content` / `sources` / `done` events
- ✅ **Semantic search over 14k 中文研报** (`POST /v1/corpus/semantic_search`) — bge-m3 embed → pgvector ANN top-50 → bge-reranker top-15, p50 ~1s wall
- ✅ **Citation-aware answers** — every fact tagged `[N]` with traceable source (broker, date, page no.)
- ✅ **Open-source agent UI** — MIT-licensed, downloadable zip, runs against your own API key

## Quick start

### Use the hosted version

```bash
curl -X POST https://rp.zgen.xin/v1/agent/ask \
  -H "Authorization: Bearer rp-demo-public" \
  -H "Content-Type: application/json" \
  -d '{"query": "半导体设备国产化 2026 关键公司有哪些"}'
```

Or just visit https://rp.zgen.xin/agent in your browser.

### Self-host

See [`agents/researchpipe-agent-ui/README.md`](./agents/researchpipe-agent-ui/README.md) for the agent UI alone, or:

```bash
# Backend
cd backend
cp .env.example .env  # fill in TAVILY_API_KEY, BAILIAN_API_KEY, SILICONFLOW_API_KEY
uv sync
uv run uvicorn researchpipe_api.main:app --port 3725

# Frontend
cd frontend
cp .env.example .env.local
npm install && npm run dev   # → localhost:3726
```

## Project status

🟢 **MVP shipped 2026-04-30** — full agent loop, 14k corpus embedded, admin console live.

## License

MIT — see [LICENSE](./LICENSE). Fork it, ship it, sell it.

## Acknowledgements

- [Tavily](https://tavily.com) — inspiration for the SSE research-agent UX pattern
- [SiliconFlow](https://siliconflow.cn) — free-tier bge-m3 + bge-reranker
- [pgvector](https://github.com/pgvector/pgvector) — PostgreSQL vector extension

---

*Built in WSL · Deployed via reverse proxy · No GitHub-CI dependency*
