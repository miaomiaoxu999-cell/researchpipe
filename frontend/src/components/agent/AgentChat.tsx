"use client";

import { useCallback, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { askAgent, AgentEvent, SourceItem } from "@/lib/sse-client";
import { ToolCallCard } from "./ToolCallCard";
import { SourceCard } from "./SourceCard";

interface ToolCallEntry {
  id: string;
  tool: string;
  args: Record<string, unknown>;
  status: "running" | "done";
  nResults?: number;
  elapsedMs?: number;
}

const SAMPLE_QUERIES = [
  "半导体设备国产化 2026 关键公司有哪些？",
  "中国 biotech 创新药出海 BD 首付款金额趋势",
  "美联储降息周期对中国 A 股影响",
  "宁德时代固态电池量产时间表",
  "比亚迪海外建厂进展（欧洲/泰国/巴西）",
];

const BACKEND = process.env.NEXT_PUBLIC_RP_BACKEND_URL || "http://localhost:3725";
const API_KEY = process.env.NEXT_PUBLIC_RP_API_KEY || "rp-demo-public";

export function AgentChat() {
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [tools, setTools] = useState<ToolCallEntry[]>([]);
  const [content, setContent] = useState("");
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [done, setDone] = useState<{ total_ms: number; iterations: number; tool_calls: number; credits_charged: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const runQuery = useCallback(
    async (q: string) => {
      if (!q.trim() || isStreaming) return;
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;

      setSubmitted(q);
      setTools([]);
      setContent("");
      setSources([]);
      setDone(null);
      setError(null);
      setIsStreaming(true);

      try {
        for await (const ev of askAgent({ query: q, apiKey: API_KEY, baseUrl: BACKEND, signal: ctrl.signal })) {
          dispatch(ev, { setTools, setContent, setSources, setDone, setError });
        }
      } catch (e) {
        if ((e as Error).name !== "AbortError") {
          setError((e as Error).message);
        }
      } finally {
        setIsStreaming(false);
      }
    },
    [isStreaming],
  );

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      runQuery(query);
      setQuery("");
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6 max-w-7xl mx-auto p-4 lg:p-8">
      {/* Left: chat */}
      <div className="space-y-4">
        {/* Hero / empty state */}
        {!submitted && (
          <div className="rounded-lg border border-slate-200 bg-white p-6">
            <h1 className="text-2xl font-bold tracking-tight">ResearchPipe Agent</h1>
            <p className="mt-1 text-sm text-slate-600">
              中文投研问答 · 14k+ 篇 2026 券商研报 + 一级市场 deal 数据 · LLM 自动综合并引用来源
            </p>
            <div className="mt-4">
              <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">试试这些问题</div>
              <div className="flex flex-wrap gap-2">
                {SAMPLE_QUERIES.map((q) => (
                  <button
                    key={q}
                    onClick={() => runQuery(q)}
                    className="rounded-md border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100 hover:border-slate-300"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Submitted query */}
        {submitted && (
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="text-xs font-medium text-slate-500 mb-1">提问</div>
            <div className="text-base font-medium text-slate-800">{submitted}</div>
          </div>
        )}

        {/* Tool calls trace */}
        {tools.length > 0 && (
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">
              Agent 工作流 ({tools.filter((t) => t.status === "done").length}/{tools.length})
            </div>
            {tools.map((t) => (
              <ToolCallCard
                key={t.id}
                tool={t.tool}
                args={t.args}
                status={t.status}
                nResults={t.nResults}
                elapsedMs={t.elapsedMs}
              />
            ))}
          </div>
        )}

        {/* Final answer */}
        {(content || isStreaming) && (
          <div className="rounded-lg border border-slate-200 bg-white p-6">
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-3">回答</div>
            {content ? (
              <div className="prose prose-slate max-w-none text-[15px] leading-relaxed">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    p: ({ children }) => <p className="my-2">{renderCitations(children)}</p>,
                    li: ({ children }) => <li>{renderCitations(children)}</li>,
                  }}
                >
                  {content}
                </ReactMarkdown>
              </div>
            ) : (
              <div className="text-sm text-slate-400 italic animate-pulse">综合中…</div>
            )}
          </div>
        )}

        {/* Done summary */}
        {done && (
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
            完成 · {(done.total_ms / 1000).toFixed(1)}s · {done.iterations} 轮 · {done.tool_calls} 次工具调用 · {done.credits_charged.toFixed(1)} credits
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
        )}

        {/* Input — non-sticky to avoid footer collision in integrated layout */}
        <form onSubmit={onSubmit} className="mt-4">
          <div className="flex gap-2 rounded-lg border border-slate-300 bg-white p-2 shadow-sm focus-within:border-slate-400">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="问一个投研问题…"
              disabled={isStreaming}
              className="flex-1 px-3 py-2 text-base outline-none disabled:bg-slate-50"
            />
            <button
              type="submit"
              disabled={isStreaming || !query.trim()}
              className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:bg-slate-300"
            >
              {isStreaming ? "运行中…" : "提问"}
            </button>
          </div>
        </form>
      </div>

      {/* Right: sources panel */}
      <aside className="space-y-3">
        <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">引用来源 ({sources.length})</div>
        {sources.length === 0 && !isStreaming && (
          <div className="rounded-lg border border-dashed border-slate-200 bg-white p-4 text-sm text-slate-400">
            提交问题后，引用研报会在这里出现。
          </div>
        )}
        <div className="space-y-2">
          {sources.map((s) => (
            <SourceCard key={s.n} source={s} />
          ))}
        </div>
      </aside>
    </div>
  );
}

function dispatch(
  ev: AgentEvent,
  setters: {
    setTools: React.Dispatch<React.SetStateAction<ToolCallEntry[]>>;
    setContent: React.Dispatch<React.SetStateAction<string>>;
    setSources: React.Dispatch<React.SetStateAction<SourceItem[]>>;
    setDone: React.Dispatch<React.SetStateAction<{ total_ms: number; iterations: number; tool_calls: number; credits_charged: number } | null>>;
    setError: React.Dispatch<React.SetStateAction<string | null>>;
  },
) {
  switch (ev.event) {
    case "tool_call": {
      // Use server-issued tool_call_id when present so parallel calls of same tool match correctly.
      const id = ev.tool_call_id || `${ev.tool}-${ev.iteration}-${Math.random().toString(36).slice(2, 6)}`;
      setters.setTools((prev) => [...prev, { id, tool: ev.tool, args: ev.args, status: "running" }]);
      break;
    }
    case "tool_result": {
      setters.setTools((prev) => {
        // Prefer matching by tool_call_id; fall back to most-recent-running-by-name.
        let realIdx = -1;
        if (ev.tool_call_id) {
          realIdx = prev.findIndex((t) => t.id === ev.tool_call_id);
        }
        if (realIdx === -1) {
          const reverseIdx = [...prev].reverse().findIndex((t) => t.tool === ev.tool && t.status === "running");
          if (reverseIdx === -1) return prev;
          realIdx = prev.length - 1 - reverseIdx;
        }
        const next = [...prev];
        next[realIdx] = { ...next[realIdx], status: "done", nResults: ev.n_results, elapsedMs: ev.elapsed_ms };
        return next;
      });
      break;
    }
    case "content":
      setters.setContent((prev) => prev + ev.delta);
      break;
    case "sources":
      setters.setSources(ev.sources);
      break;
    case "done":
      setters.setDone({ total_ms: ev.total_ms, iterations: ev.iterations, tool_calls: ev.tool_calls, credits_charged: ev.credits_charged });
      break;
    case "error":
      setters.setError(`${ev.code}: ${ev.message}`);
      break;
  }
}

/**
 * Replace inline `[N]` (and `[1][2][3]` clusters) with anchor links to source cards.
 * Operates on React node children (string or array).
 */
function renderCitations(children: React.ReactNode): React.ReactNode {
  if (typeof children === "string") return parseCites(children);
  if (Array.isArray(children)) return children.map((c, i) => (typeof c === "string" ? <span key={i}>{parseCites(c)}</span> : c));
  return children;
}

function parseCites(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const re = /\[(\d+)\]/g;
  let lastIdx = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  while ((m = re.exec(text))) {
    if (m.index > lastIdx) parts.push(text.slice(lastIdx, m.index));
    const n = m[1];
    parts.push(
      <a
        key={`c${key++}`}
        href={`#source-${n}`}
        className="cite-pill"
        title={`See source [${n}]`}
        onClick={(e) => {
          e.preventDefault();
          document.getElementById(`source-${n}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
        }}
      >
        {n}
      </a>,
    );
    lastIdx = re.lastIndex;
  }
  if (lastIdx < text.length) parts.push(text.slice(lastIdx));
  return parts;
}
