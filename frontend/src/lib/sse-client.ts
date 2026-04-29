/**
 * Streaming POST → SSE client.
 *
 * Browser EventSource only supports GET, so we use fetch with a streaming reader
 * and parse the `event: <name>\ndata: {...}\n\n` SSE frames manually.
 */

export type AgentEvent =
  | { event: "tool_call"; tool_call_id?: string; tool: string; args: Record<string, unknown>; iteration: number }
  | { event: "tool_result"; tool_call_id?: string; tool: string; n_results: number; n_new_sources: number; elapsed_ms: number }
  | { event: "content"; delta: string }
  | { event: "sources"; sources: SourceItem[] }
  | { event: "done"; request_id: string; total_ms: number; iterations: number; tool_calls: number; credits_charged: number }
  | { event: "error"; code: string; message: string };

export interface SourceItem {
  n: number;
  title: string | null;
  broker: string | null;
  date: string | null;
  url: string;
  snippet: string | null;
  source_type: string;
  page_no?: number;
  rerank_score?: number;
  industry_tags?: string[];
}

export interface AskOptions {
  query: string;
  apiKey: string;
  baseUrl: string;
  signal?: AbortSignal;
}

export async function* askAgent(opts: AskOptions): AsyncGenerator<AgentEvent> {
  const resp = await fetch(`${opts.baseUrl}/v1/agent/ask`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${opts.apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query: opts.query }),
    signal: opts.signal,
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`HTTP ${resp.status}: ${text.slice(0, 300)}`);
  }
  if (!resp.body) {
    throw new Error("No response body");
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  // SSE allows CRLF line endings (some proxies rewrite); accept both.
  const FRAME_SEP_RE = /\r?\n\r?\n/;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split(FRAME_SEP_RE);
      buffer = frames.pop() ?? "";
      for (const frame of frames) {
        const ev = parseFrame(frame);
        if (ev) yield ev;
      }
    }
  } catch (err) {
    // Abort: cancel reader to free underlying connection immediately.
    if ((err as Error).name === "AbortError") {
      try { await reader.cancel(); } catch {}
    }
    throw err;
  } finally {
    try { reader.releaseLock(); } catch {}
  }
}

const DATA_PREFIX_RE = /^data:\s?/;

function parseFrame(frame: string): AgentEvent | null {
  const dataLine = frame
    .split(/\r?\n/)
    .find((l) => DATA_PREFIX_RE.test(l));
  if (!dataLine) return null;
  try {
    return JSON.parse(dataLine.replace(DATA_PREFIX_RE, "")) as AgentEvent;
  } catch {
    return null;
  }
}
