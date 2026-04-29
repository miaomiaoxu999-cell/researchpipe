# researchpipe — Python SDK

```bash
pip install researchpipe
```

## Quickstart

```python
from researchpipe import ResearchPipe

rp = ResearchPipe(api_key="rp-...")  # get yours at https://rp.zgen.xin/dashboard

# 1) Search the web for investment research
r = rp.search(query="具身智能 融资 2026", max_results=5)
for hit in r["results"]:
    print(hit["title"], hit["url"])

# 2) Extract structured fields from a research PDF
fields = rp.extract_research(url="https://...path/to/report.pdf")
print(fields["extraction"]["core_thesis"])

# 3) Pull a company profile (mock during M1)
company = rp.companies_get("comp_2x9bka")
print(company["name"], company["sector"])

# 4) Run a deep sector study (async; SDK polls for you)
report = rp.research_sector(input="具身智能", time_range="24m")
print(report["result"]["executive_summary"])
```

## Async usage

```python
import asyncio
from researchpipe import AsyncResearchPipe

async def main():
    async with AsyncResearchPipe(api_key="rp-...") as rp:
        r = await rp.search(query="...")
        print(r["results"])

asyncio.run(main())
```

## Error handling

All SDK errors carry `hint_for_agent` so LLM-driven callers can decide next action:

```python
from researchpipe import ResearchPipe, RateLimitError, AuthError

rp = ResearchPipe(api_key="rp-...")

try:
    rp.search(query="...")
except RateLimitError as e:
    print(e.hint_for_agent)        # → "Wait retry_after_seconds, then retry…"
    print(e.retry_after_seconds)   # → 12
except AuthError as e:
    print(e.hint_for_agent)        # → "Set Authorization: Bearer rp-…"
```

The SDK auto-retries 429 (respecting `retry_after_seconds`) and 5xx upstream failures (exponential backoff, max 3 attempts).

## Endpoints

- **Search**: `search`, `extract`, `extract_research`
- **Research** (async, auto-polled): `research_sector`, `research_company`, `research_valuation`
- **Data — Companies**: `companies_search/get/deals/peers/news/founders`
- **Data — Investors**: `investors_search/get/portfolio/preferences/exits`
- **Data — Deals**: `deals_search/get/timeline/overseas/co_investors`
- **Account**: `me`, `usage`, `billing`
- **Watch**: `watch_create`, `watch_digest`

Full reference: https://rp.zgen.xin/docs

## Development

```bash
git clone https://github.com/researchpipe/sdk-python
cd sdk-python
uv sync
uv run pytest
```
