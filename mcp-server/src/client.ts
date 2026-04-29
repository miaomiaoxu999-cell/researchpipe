/**
 * Minimal Node fetch wrapper around ResearchPipe API.
 * Used internally by the MCP tool handlers.
 */

const DEFAULT_BASE_URL = "https://rp.zgen.xin";
const USER_AGENT = "researchpipe-mcp/0.1.0";

export interface ClientOptions {
  apiKey: string;
  baseUrl?: string;
  timeoutMs?: number;
}

export class ResearchPipeClient {
  apiKey: string;
  baseUrl: string;
  timeoutMs: number;

  constructor(opts: ClientOptions) {
    if (!opts.apiKey) {
      throw new Error("apiKey is required");
    }
    this.apiKey = opts.apiKey;
    this.baseUrl = (opts.baseUrl || DEFAULT_BASE_URL).replace(/\/$/, "");
    this.timeoutMs = opts.timeoutMs ?? 60000;
  }

  // Public alias so MCP dispatchers can do generic GETs/POSTs to v3 endpoints
  async request<T = unknown>(
    method: "GET" | "POST",
    path: string,
    options: { body?: unknown; query?: Record<string, string | number | boolean | undefined> } = {},
  ): Promise<T> {
    return this._request<T>(method, path, options);
  }

  private async _request<T = unknown>(
    method: "GET" | "POST",
    path: string,
    options: { body?: unknown; query?: Record<string, string | number | boolean | undefined> } = {},
  ): Promise<T> {
    const url = new URL(`${this.baseUrl}${path}`);
    if (options.query) {
      for (const [k, v] of Object.entries(options.query)) {
        if (v != null) url.searchParams.set(k, String(v));
      }
    }
    const idempotency = crypto.randomUUID();
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), this.timeoutMs);
    try {
      const res = await fetch(url.toString(), {
        method,
        headers: {
          "Authorization": `Bearer ${this.apiKey}`,
          "Content-Type": "application/json",
          "User-Agent": USER_AGENT,
          "Idempotency-Key": idempotency,
        },
        body: options.body ? JSON.stringify(options.body) : undefined,
        signal: ctrl.signal,
      });
      const text = await res.text();
      let body: unknown;
      try {
        body = text ? JSON.parse(text) : {};
      } catch {
        body = { detail: text.slice(0, 300) };
      }
      if (!res.ok) {
        const err = (body as Record<string, unknown>)?.detail || (body as Record<string, unknown>)?.error || body;
        const errObj = typeof err === "object" && err ? (err as Record<string, unknown>) : { message: String(err) };
        throw Object.assign(new Error(String(errObj.message || `HTTP ${res.status}`)), {
          code: errObj.code,
          hint_for_agent: errObj.hint_for_agent,
          status: res.status,
        });
      }
      return body as T;
    } finally {
      clearTimeout(t);
    }
  }

  search(query: string, opts: Record<string, unknown> = {}) {
    return this.request("POST", "/v1/search", { body: { query, ...opts } });
  }

  extract(url: string, opts: Record<string, unknown> = {}) {
    return this.request("POST", "/v1/extract", { body: { url, ...opts } });
  }

  extractResearch(url: string, opts: Record<string, unknown> = {}) {
    return this.request("POST", "/v1/extract/research", { body: { url, ...opts } });
  }

  companiesGet(id: string) {
    return this.request("GET", `/v1/companies/${encodeURIComponent(id)}`);
  }

  companiesSearch(opts: Record<string, unknown>) {
    return this.request("POST", "/v1/companies/search", { body: opts });
  }

  dealsSearch(opts: Record<string, unknown>) {
    return this.request("POST", "/v1/deals/search", { body: opts });
  }

  industriesDeals(industryId: string) {
    return this.request("GET", `/v1/industries/${encodeURIComponent(industryId)}/deals`);
  }

  newsSearch(opts: Record<string, unknown>) {
    return this.request("POST", "/v1/news/search", { body: opts });
  }

  watchDigest(id: string) {
    return this.request("GET", `/v1/watch/${encodeURIComponent(id)}/digest`);
  }

  async researchSector(opts: Record<string, unknown>) {
    const job = (await this.request("POST", "/v1/research/sector", { body: opts })) as {
      request_id: string;
      status: string;
    };
    return this.pollJob(job.request_id);
  }

  async researchCompany(opts: Record<string, unknown>) {
    const job = (await this.request("POST", "/v1/research/company", { body: opts })) as {
      request_id: string;
      status: string;
    };
    return this.pollJob(job.request_id);
  }

  private async pollJob(id: string, intervalMs = 3000, maxPolls = 60): Promise<unknown> {
    for (let i = 0; i < maxPolls; i++) {
      const job = (await this.request("GET", `/v1/jobs/${id}`)) as { status: string };
      if (job.status === "completed" || job.status === "failed") {
        return job;
      }
      await new Promise((r) => setTimeout(r, intervalMs));
    }
    throw new Error(`Job ${id} timed out`);
  }
}
