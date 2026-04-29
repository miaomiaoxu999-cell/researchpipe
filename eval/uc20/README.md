# UC20 — 20-case Quality Benchmark

End-to-end quality test of the ResearchPipe agent across 20 query types.
Used as a regression suite when changing the agent loop, prompts, or tools.

## Files

- `cases.py` — 20 case definitions (id, category, query, expected behavior)
- `run.py` — SSE client that POSTs each case to `/v1/agent/ask` and records events
- `analyze.py` — heuristic scorer; produces `report.md`
- `results_uc20.json` — last full run's raw event log per case
- `report.md` — per-case grade table + answer previews

## Categories covered

sector, single_stock, hybrid, niche, english, metadata, timeseries, comparative,
hot_topic, policy, macro, ticker, ambiguous, deep_chain, claim_check, commodity,
off_topic.

## Running

```bash
cd eval/uc20
# All 20 against production
python3 run.py --base https://rp.zgen.xin --key rp-dev-XXXX

# Single case
python3 run.py --only uc01_semiconductor

# Score
python3 analyze.py results_uc20.json report.md
```

## Last run

A=18 / B=1 / C=1 / F=0. See `report.md` for per-case detail.

Bugs surfaced and fixed by this benchmark:
- `deals_search()` rejected `company_name` kwarg → added param
- agent loop hit MAX_ITERATIONS=5 with empty content → bumped to 8 + force final synthesis
- `corpus_search` broker filter exact-only → switched to ILIKE partial match
- agent followed off-topic queries (weather) into `web_search` → scope guardrail in system prompt
