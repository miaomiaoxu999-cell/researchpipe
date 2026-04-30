/**
 * Deep Research SSE client — POST /v1/deep-research/run, yields trace events.
 *
 * Mirrors the lib/sse-client.ts pattern (fetch + manual SSE frame parser) since
 * EventSource is GET-only. See backend/src/researchpipe_api/deep_research.py
 * for the event schema this consumes.
 */

export type StepName = "planning" | "searching" | "reporting" | "exporting";
export type StepStatus = "running" | "success" | "error";

export interface SourceItem {
  n: number;
  title: string | null;
  url: string | null;
  snippet?: string | null;
  providers?: string[];
  rerank_score?: number;
}

export interface SearchResultItem {
  batch_id: number;
  title: string | null;
  url: string | null;
  snippet?: string | null;
  providers?: string[];
}

export type DRStep = {
  event: "step";
  step_id: number;
  name: StepName;
  status: StepStatus;
  content: string;
  extra?: Record<string, unknown>;
};

export type DRQueries = { event: "queries"; queries: string[] };
export type DRBatchStart = { event: "search_batch_start"; batch_id: number; query: string };
export type DRBatchDone = { event: "search_batch_done"; batch_id: number; n_results: number; error?: string };
export type DRSearchResult = { event: "search_result" } & SearchResultItem;
export type DRThinking = { event: "thinking"; content: string };
export type DRReportDelta = { event: "report_delta"; delta: string };
export type DRSources = { event: "sources"; sources: SourceItem[] };
export type DRDone = {
  event: "done";
  request_id: string;
  report_id: string;
  report_url: string;
  total_ms: number;
  n_sources: number;
};
export type DRError = { event: "error"; code: string; message: string };

export type DREvent =
  | DRStep
  | DRQueries
  | DRBatchStart
  | DRBatchDone
  | DRSearchResult
  | DRThinking
  | DRReportDelta
  | DRSources
  | DRDone
  | DRError;

export interface RunOptions {
  question: string;
  apiKey: string;
  baseUrl: string;
  signal?: AbortSignal;
}

export async function* runDeepResearch(opts: RunOptions): AsyncGenerator<DREvent> {
  const resp = await fetch(`${opts.baseUrl}/v1/deep-research/run`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${opts.apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question: opts.question }),
    signal: opts.signal,
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`HTTP ${resp.status}: ${text.slice(0, 300)}`);
  }
  if (!resp.body) throw new Error("No response body");

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const FRAME_SEP = /\r?\n\r?\n/;
  const DATA_PREFIX = /^data:\s?/;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split(FRAME_SEP);
      buffer = frames.pop() ?? "";
      for (const frame of frames) {
        const dataLine = frame.split(/\r?\n/).find((l) => DATA_PREFIX.test(l));
        if (!dataLine) continue;
        try {
          yield JSON.parse(dataLine.replace(DATA_PREFIX, "")) as DREvent;
        } catch {
          /* skip malformed */
        }
      }
    }
  } catch (err) {
    if ((err as Error).name === "AbortError") {
      try { await reader.cancel(); } catch { /* ignore */ }
    }
    throw err;
  } finally {
    try { reader.releaseLock(); } catch { /* ignore */ }
  }
}
