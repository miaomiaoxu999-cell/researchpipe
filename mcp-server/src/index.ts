#!/usr/bin/env node
/**
 * ResearchPipe MCP Server.
 *
 * Exposes 8 high-level tools (per PRD ch6.x) over stdio. Designed for Claude Desktop /
 * Cursor / Cline. Each tool's `description` is in English (LLM tool selection accuracy)
 * and includes Chinese examples in the schema.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  type Tool,
} from "@modelcontextprotocol/sdk/types.js";

import { ResearchPipeClient } from "./client.js";

const apiKey = process.env.RESEARCHPIPE_KEY || process.env.RP_API_KEY;
if (!apiKey) {
  console.error(
    "[researchpipe-mcp] missing RESEARCHPIPE_KEY env var. Set it in claude_desktop_config.json:\n" +
      JSON.stringify(
        {
          mcpServers: {
            researchpipe: {
              command: "npx",
              args: ["-y", "@researchpipe/mcp-server"],
              env: { RESEARCHPIPE_KEY: "rp-..." },
            },
          },
        },
        null,
        2,
      ),
  );
  process.exit(1);
}

const baseUrl = process.env.RESEARCHPIPE_BASE_URL || undefined;
const client = new ResearchPipeClient({ apiKey, baseUrl });

const TOOLS: Tool[] = [
  {
    name: "researchpipe_search",
    description:
      "Web/news/research/policy/filing search across China + global investment-research sources. Returns titles, URLs, snippets and an LLM-synthesized answer. Use for broad discovery before deep extraction. 例：query='具身智能 融资 2026', type='research'",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "搜索关键词" },
        type: {
          type: "string",
          enum: ["web", "news", "research", "policy", "filing"],
          default: "research",
        },
        max_results: { type: "number", default: 10 },
        time_range: { type: "string", default: "30d", description: "如 '30d' / '12m'" },
        regions: { type: "array", items: { type: "string" } },
      },
      required: ["query"],
    },
  },
  {
    name: "researchpipe_extract",
    description:
      "Extract clean text content from a single URL (PDF or HTML). Useful when you have a known research-report URL and want full text for further analysis. 例：url='https://...path/to/report.pdf'",
    inputSchema: {
      type: "object",
      properties: {
        url: { type: "string" },
        extract_depth: { type: "string", enum: ["basic", "advanced"], default: "advanced" },
      },
      required: ["url"],
    },
  },
  {
    name: "researchpipe_extract_research",
    description:
      "Extract 11 structured fields (broker, core_thesis, target_price, key_data_points, risks, etc.) from a research report URL. Handles English→Chinese translation in one step. Use for any sell-side, consultancy or association report. 例：url='https://www.goldmansachs.com/insights/...china-drug-development'",
    inputSchema: {
      type: "object",
      properties: {
        url: { type: "string" },
        language: { type: "string", enum: ["zh", "en"], default: "zh" },
      },
      required: ["url"],
    },
  },
  {
    name: "researchpipe_research_sector",
    description:
      "Run a deep, async sector research. Returns a structured 16-field report with executive_summary, deals, key_companies, valuation_anchors, risks, citations. Async — server polls until complete (~30-60s). 例：input='具身智能', time_range='24m'",
    inputSchema: {
      type: "object",
      properties: {
        input: { type: "string", description: "Sector or topic name (in Chinese for CN markets)" },
        time_range: { type: "string", default: "24m" },
        depth: { type: "string", enum: ["summary", "standard", "full"], default: "standard" },
        model: { type: "string", enum: ["mini", "pro", "auto"], default: "auto" },
      },
      required: ["input"],
    },
  },
  {
    name: "researchpipe_research_company",
    description:
      "Run a deep, async company DD. Returns 16 fields including business_profile, peers_dd, valuation_anchor, financials_summary, red_flags, recent_news, outlook. Async (~30-60s). 例：input='宁德时代', focus=['business','financials','risks']",
    inputSchema: {
      type: "object",
      properties: {
        input: { type: "string" },
        focus: {
          type: "array",
          items: { type: "string" },
          default: ["business", "financials", "risks"],
        },
        depth: { type: "string", enum: ["summary", "standard", "full"], default: "standard" },
      },
      required: ["input"],
    },
  },
  {
    name: "researchpipe_company_data",
    description:
      "Aggregated company data: profile / deals / peers / news / filings. Pass an `op` to choose which slice. Lower-credit than research_company; use for fast lookups. 例：op='get', id='comp_2x9bka'",
    inputSchema: {
      type: "object",
      properties: {
        op: {
          type: "string",
          enum: ["search", "get", "deals", "peers", "news", "founders"],
        },
        id: { type: "string", description: "Company id (for get/deals/peers/news/founders)" },
        query: { type: "string", description: "Used when op=search" },
        deep: { type: "boolean", description: "Used when op=founders" },
      },
      required: ["op"],
    },
  },
  {
    name: "researchpipe_industry_data",
    description:
      "Industry data: deals / companies / chain / policies / tech_roadmap. Pass `op` and `id`. 例：op='deals', id='ind_embodied'",
    inputSchema: {
      type: "object",
      properties: {
        op: {
          type: "string",
          enum: ["search", "deals", "companies", "chain", "policies", "tech_roadmap"],
        },
        id: { type: "string" },
        query: { type: "string" },
      },
      required: ["op"],
    },
  },
  {
    name: "researchpipe_watch",
    description:
      "Create a watchlist or fetch its digest (cron-friendly subscription on industries / companies / investors). 例：op='digest', id='watch_a8f2'",
    inputSchema: {
      type: "object",
      properties: {
        op: { type: "string", enum: ["create", "digest"] },
        id: { type: "string" },
        name: { type: "string" },
        industries: { type: "array", items: { type: "string" } },
        company_ids: { type: "array", items: { type: "string" } },
      },
      required: ["op"],
    },
  },
];

const server = new Server(
  { name: "researchpipe", version: "0.1.0" },
  { capabilities: { tools: {} } },
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOLS }));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  const safeArgs = (args || {}) as Record<string, unknown>;

  try {
    let result: unknown;
    switch (name) {
      case "researchpipe_search":
        result = await client.search(String(safeArgs.query), {
          type: safeArgs.type,
          max_results: safeArgs.max_results,
          time_range: safeArgs.time_range,
          regions: safeArgs.regions,
        });
        break;

      case "researchpipe_extract":
        result = await client.extract(String(safeArgs.url), {
          extract_depth: safeArgs.extract_depth,
        });
        break;

      case "researchpipe_extract_research":
        result = await client.extractResearch(String(safeArgs.url), {
          language: safeArgs.language,
        });
        break;

      case "researchpipe_research_sector":
        result = await client.researchSector({
          input: safeArgs.input,
          time_range: safeArgs.time_range,
          depth: safeArgs.depth,
          model: safeArgs.model,
        });
        break;

      case "researchpipe_research_company":
        result = await client.researchCompany({
          input: safeArgs.input,
          focus: safeArgs.focus,
          depth: safeArgs.depth,
        });
        break;

      case "researchpipe_company_data": {
        const op = String(safeArgs.op);
        const id = String(safeArgs.id || "");
        switch (op) {
          case "search":
            result = await client.companiesSearch({ query: safeArgs.query, limit: safeArgs.limit });
            break;
          case "get":
            result = await client.companiesGet(id);
            break;
          case "deals":
          case "news":
          case "peers":
          case "founders":
            // Generic fetch via subpath (peers/founders posts; deals/news GETs — let server handle)
            result = await client.companiesGet(`${id}/${op}${op === "founders" && safeArgs.deep ? "?deep=true" : ""}`);
            break;
          default:
            throw new Error(`unknown company_data op: ${op}`);
        }
        break;
      }

      case "researchpipe_industry_data": {
        const op = String(safeArgs.op);
        const id = String(safeArgs.id || "");
        switch (op) {
          case "search":
            result = await client.industriesDeals(id);  // best effort
            break;
          case "deals":
          case "companies":
          case "chain":
          case "policies":
          case "tech_roadmap":
          case "key_technologies":
            // All GET /v1/industries/{id}/{op} — go through generic fetch using the existing client method shape
            result = await (client as unknown as { request: (m: string, p: string) => Promise<unknown> }).request?.(
              "GET",
              `/v1/industries/${encodeURIComponent(id)}/${op}`,
            ) || await client.industriesDeals(`${id}/${op}`);
            break;
          default:
            throw new Error(`unknown industry_data op: ${op}`);
        }
        break;
      }

      case "researchpipe_watch": {
        const op = String(safeArgs.op);
        if (op === "create") {
          // Use a generic POST since client doesn't expose watchCreate yet
          result = await (client as unknown as { request?: (m: string, p: string, opts?: { body?: unknown }) => Promise<unknown> }).request?.(
            "POST",
            "/v1/watch/create",
            { body: { name: safeArgs.name, industries: safeArgs.industries, company_ids: safeArgs.company_ids, cron: safeArgs.cron } },
          ) || { note: "watch.create requires updated client", payload: safeArgs };
        } else {
          result = await client.watchDigest(String(safeArgs.id));
        }
        break;
      }

      default:
        throw new Error(`unknown tool: ${name}`);
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  } catch (err: unknown) {
    const e = err as Error & { code?: string; hint_for_agent?: string };
    return {
      isError: true,
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              error: e.message,
              code: e.code,
              hint_for_agent: e.hint_for_agent,
            },
            null,
            2,
          ),
        },
      ],
    };
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
process.stderr.write("[researchpipe-mcp] server ready (stdio)\n");
