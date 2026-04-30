"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { askAgent, AgentEvent, SourceItem } from "@/lib/sse-client";

interface ToolCallEntry {
  id: string;
  tool: string;
  args: Record<string, unknown>;
  status: "running" | "done";
  nResults?: number;
  elapsedMs?: number;
}

interface DoneSummary {
  total_ms: number;
  iterations: number;
  tool_calls: number;
  credits_charged: number;
}

const EXAMPLES = [
  {
    label: "行业研究",
    icon: "📊",
    query: "半导体设备国产化 2026 关键公司有哪些？",
  },
  {
    label: "公司尽调",
    icon: "🏢",
    query: "宁德时代固态电池量产时间表",
  },
  {
    label: "估值对标",
    icon: "💰",
    query: "比亚迪 vs 特斯拉 当前估值倍数对比",
  },
  {
    label: "政策匹配",
    icon: "📜",
    query: "十五五规划对人工智能产业的重点扶持方向",
  },
  {
    label: "赛道扫描",
    icon: "🔭",
    query: "中国 biotech 创新药出海 BD 首付款金额趋势",
  },
];

const FALLBACK_BACKEND = "http://localhost:3725";
const PUBLIC_DEMO_KEY = "rp-demo-public";

function getBackendUrl() {
  return process.env.NEXT_PUBLIC_RP_BACKEND_URL || FALLBACK_BACKEND;
}

function getDefaultKey() {
  if (typeof window === "undefined") return PUBLIC_DEMO_KEY;
  return localStorage.getItem("rp_api_key") || process.env.NEXT_PUBLIC_RP_API_KEY || PUBLIC_DEMO_KEY;
}

export function ResearchApp({
  initialQuery = "",
}: {
  initialQuery?: string;
}) {
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [apiKey, setApiKey] = useState<string>("");
  const [keyEditing, setKeyEditing] = useState(false);

  const [query, setQuery] = useState(initialQuery);
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [tools, setTools] = useState<ToolCallEntry[]>([]);
  const [content, setContent] = useState("");
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [done, setDone] = useState<DoneSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [model, setModel] = useState<"mini" | "pro">("mini");
  const [history, setHistory] = useState<{ q: string; t: number }[]>([]);
  const [exportOpen, setExportOpen] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  // Load key + history from localStorage on mount
  useEffect(() => {
    setApiKey(getDefaultKey());
    try {
      const h = JSON.parse(localStorage.getItem("rp_history") || "[]");
      if (Array.isArray(h)) setHistory(h.slice(0, 30));
    } catch {}
  }, []);

  // Auto-run if a query was passed in via URL (?q=...)
  // Strip the param from the URL after consuming so a refresh doesn't replay.
  const autoRanRef = useRef(false);
  useEffect(() => {
    if (!autoRanRef.current && initialQuery && apiKey) {
      autoRanRef.current = true;
      runQuery(initialQuery);
      setQuery("");
      try {
        router.replace("/agent", { scroll: false });
      } catch {}
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiKey, initialQuery]);

  const persistKey = (k: string) => {
    setApiKey(k);
    try {
      localStorage.setItem("rp_api_key", k);
    } catch {}
  };

  const pushHistory = useCallback((q: string) => {
    const stored = q.length > 500 ? q.slice(0, 500) : q;
    setHistory((prev) => {
      const next = [{ q: stored, t: Date.now() }, ...prev.filter((h) => h.q !== stored)].slice(0, 30);
      try {
        localStorage.setItem("rp_history", JSON.stringify(next));
      } catch {}
      return next;
    });
  }, []);

  const runQuery = useCallback(
    async (q: string) => {
      const trimmed = q.trim();
      if (!trimmed) return;
      // Abort any in-flight stream so back-to-back clicks always start fresh.
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;

      setSubmitted(trimmed);
      setTools([]);
      setContent("");
      setSources([]);
      setDone(null);
      setError(null);
      setIsStreaming(true);
      pushHistory(trimmed);

      try {
        for await (const ev of askAgent({
          query: trimmed,
          apiKey: apiKey || PUBLIC_DEMO_KEY,
          baseUrl: getBackendUrl(),
          signal: ctrl.signal,
        })) {
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
    [apiKey, pushHistory],
  );

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      runQuery(query);
      setQuery("");
    }
  };

  const newResearch = () => {
    abortRef.current?.abort();
    setSubmitted(null);
    setTools([]);
    setContent("");
    setSources([]);
    setDone(null);
    setError(null);
    setIsStreaming(false);
  };

  // Build a markdown report for export
  const buildReport = () => {
    const head = `# ${submitted || "投研派研究"}\n\n`;
    const meta = done
      ? `> ${(done.total_ms / 1000).toFixed(1)}s · ${done.iterations} 轮 · ${done.tool_calls} 次工具调用 · ${done.credits_charged.toFixed(1)} credits\n\n`
      : "";
    const body = content + "\n\n";
    const refs = sources.length
      ? "## 引用来源\n\n" +
        sources
          .map(
            (s) =>
              `[${s.n}] ${s.broker || s.source_type || "源"} · ${s.title || ""}${
                s.date ? " · " + s.date : ""
              }${s.url ? `\n    ${s.url}` : ""}`,
          )
          .join("\n\n")
      : "";
    return head + meta + body + refs;
  };

  const downloadAs = (ext: "md" | "txt") => {
    const md = buildReport();
    const mime = ext === "md" ? "text/markdown" : "text/plain";
    const blob = new Blob([md], { type: `${mime};charset=utf-8` });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(submitted || "report").slice(0, 40).replace(/[^\w一-龥]+/g, "_")}.${ext}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    setExportOpen(false);
  };

  const copyMarkdown = async () => {
    try {
      await navigator.clipboard.writeText(buildReport());
      setExportOpen(false);
    } catch {}
  };

  const printPdf = () => {
    window.print();
    setExportOpen(false);
  };

  return (
    <div className="-mt-[64px] pt-[64px] min-h-screen bg-cream relative">
      <div className="flex h-[calc(100vh-0px)]">
        {/* Sidebar */}
        <aside
          className={`sidebar shrink-0 border-r hairline bg-cream-200 flex flex-col ${
            sidebarOpen ? "w-[260px]" : "w-[58px]"
          }`}
        >
          <div className="flex items-center justify-between px-3 pt-[76px] pb-3">
            {sidebarOpen ? (
              <Link href="/" className="flex items-baseline gap-1.5">
                <span className="text-[15px] font-semibold tracking-tight">
                  投研派
                </span>
                <span className="text-[10.5px] text-muted">ResearchPipe</span>
              </Link>
            ) : (
              <span />
            )}
            <button
              onClick={() => setSidebarOpen((v) => !v)}
              className="p-1.5 rounded-md hover:bg-soft text-ink/60 hover:text-ink"
              aria-label={sidebarOpen ? "收起" : "展开"}
            >
              {sidebarOpen ? "←" : "→"}
            </button>
          </div>

          <div className="px-3">
            <button
              onClick={newResearch}
              className="w-full inline-flex items-center gap-2 px-3 py-2 rounded-btn bg-ink-900 text-cream-50 text-[13.5px] font-medium hover:bg-ink-800 transition-colors"
            >
              <span aria-hidden>＋</span>
              {sidebarOpen && <span>新研究</span>}
            </button>
          </div>

          {sidebarOpen && (
            <div className="px-3 mt-6 flex-1 overflow-y-auto">
              <p className="eyebrow mb-3">最近研究</p>
              {history.length === 0 ? (
                <div className="text-[13px] text-muted leading-relaxed">
                  还没有研究记录。
                  <br />
                  开始你的第一个问题。
                </div>
              ) : (
                <ul className="space-y-1.5">
                  {history.slice(0, 12).map((h, i) => (
                    <li key={`${h.t}-${i}`}>
                      <button
                        onClick={() => runQuery(h.q)}
                        className="w-full text-left text-[13px] text-ink/75 hover:text-ink hover:bg-soft px-2 py-1.5 rounded-md truncate transition-colors"
                        title={h.q}
                      >
                        {h.q}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {sidebarOpen && (
            <div className="px-3 py-3 border-t hairline space-y-1">
              <Link
                href="/dashboard/usage"
                className="flex items-center gap-2 px-2 py-1.5 rounded-md text-[13px] text-ink/70 hover:text-ink hover:bg-soft"
              >
                <span aria-hidden>📊</span> 用量
              </Link>
              <Link
                href="/docs"
                className="flex items-center gap-2 px-2 py-1.5 rounded-md text-[13px] text-ink/70 hover:text-ink hover:bg-soft"
              >
                <span aria-hidden>📖</span> 使用指南
              </Link>
              <Link
                href="/dashboard/keys"
                className="flex items-center gap-2 px-2 py-1.5 rounded-md text-[13px] text-ink/70 hover:text-ink hover:bg-soft"
              >
                <span aria-hidden>🔑</span> API Key
              </Link>
            </div>
          )}
        </aside>

        {/* Workspace */}
        <section className="flex-1 overflow-y-auto relative">
          {!submitted ? (
            <EmptyHero
              query={query}
              setQuery={setQuery}
              onSubmit={onSubmit}
              isStreaming={isStreaming}
              examples={EXAMPLES}
              runExample={(q) => {
                abortRef.current?.abort();
                runQuery(q);
              }}
              model={model}
              setModel={setModel}
              apiKey={apiKey}
              setApiKey={persistKey}
              keyEditing={keyEditing}
              setKeyEditing={setKeyEditing}
            />
          ) : (
            <ResearchView
              submitted={submitted}
              tools={tools}
              content={content}
              sources={sources}
              done={done}
              error={error}
              isStreaming={isStreaming}
              query={query}
              setQuery={setQuery}
              onSubmit={onSubmit}
              onStop={() => abortRef.current?.abort()}
              onNew={newResearch}
              exportOpen={exportOpen}
              setExportOpen={setExportOpen}
              onCopy={copyMarkdown}
              onDownload={downloadAs}
              onPrint={printPdf}
            />
          )}
        </section>
      </div>
    </div>
  );
}

/* ─────────── Empty hero (initial state) ─────────── */

function EmptyHero({
  query,
  setQuery,
  onSubmit,
  isStreaming,
  examples,
  runExample,
  model,
  setModel,
  apiKey,
  setApiKey,
  keyEditing,
  setKeyEditing,
}: {
  query: string;
  setQuery: (s: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  isStreaming: boolean;
  examples: { label: string; icon: string; query: string }[];
  runExample: (q: string) => void;
  model: "mini" | "pro";
  setModel: (m: "mini" | "pro") => void;
  apiKey: string;
  setApiKey: (k: string) => void;
  keyEditing: boolean;
  setKeyEditing: (v: boolean) => void;
}) {
  const isPublicDemo = !apiKey || apiKey === PUBLIC_DEMO_KEY;
  return (
    <div className="hero-landscape min-h-full">
      <div className="container-narrow pt-16 sm:pt-24 pb-20">
        <div className="text-center mb-10">
          <p className="text-[13px] tracking-wide">
            <span className="text-ink/50">/</span>
            <span className="text-ink/85 font-medium">投研派</span>
            <span className="text-ink/40 mx-2">·</span>
            <span className="text-muted">研究</span>
          </p>
          <h1 className="mt-5 text-[30px] sm:text-[36px] font-medium tracking-hero leading-tight text-ink-900">
            问一个投研问题
          </h1>
          <p className="mt-3 text-[15px] text-ink/65">
            AI 自动综合 14,000 多篇研报，每个观点带出处，可导出。
          </p>
        </div>

        {/* API key step */}
        <div className="card-cream p-4 mb-3 shadow-card">
          <div className="flex items-start gap-3">
            <div className="shrink-0 w-6 h-6 rounded-full bg-soft text-[12px] flex items-center justify-center text-ink/70 font-medium">
              1
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <p className="text-[13.5px] font-medium text-ink-900">
                  你的 API Key
                </p>
                {!keyEditing && (
                  <button
                    onClick={() => setKeyEditing(true)}
                    className="text-[12px] text-ink/55 hover:text-ink"
                  >
                    {isPublicDemo ? "添加 Key" : "更换"}
                  </button>
                )}
              </div>
              {keyEditing ? (
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="rp-..."
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    className="flex-1 px-3 py-2 text-[13px] bg-cream-50 rounded-md border hairline focus:outline-none focus:border-ink/30"
                  />
                  <button
                    onClick={() => setKeyEditing(false)}
                    className="px-3 py-2 text-[12.5px] text-ink/70 hover:text-ink"
                  >
                    完成
                  </button>
                </div>
              ) : (
                <p className="text-[12.5px] text-muted">
                  {isPublicDemo ? (
                    <>
                      使用公共 demo key（额度有限）。{" "}
                      <Link
                        href="/pricing"
                        className="text-accent-link hover:underline"
                      >
                        获取私人 Key →
                      </Link>
                    </>
                  ) : (
                    <span className="font-mono">
                      ••••••••••{apiKey.slice(-6)}
                    </span>
                  )}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Main input */}
        <form
          onSubmit={onSubmit}
          className="card-cream shadow-float p-4 mb-5"
        >
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="例如：半导体设备国产化最新进展…"
            disabled={isStreaming}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                onSubmit(e as unknown as React.FormEvent);
              }
            }}
            className="w-full min-h-[100px] text-[16px] bg-transparent outline-none resize-none placeholder:text-muted"
          />
          <div className="flex items-center justify-between pt-3 border-t hairline">
            <div className="flex items-center gap-2">
              <ModelToggle model={model} setModel={setModel} />
            </div>
            <button
              type="submit"
              disabled={isStreaming || !query.trim()}
              className="btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {isStreaming ? "运行中…" : "开始研究"}
              <span aria-hidden>↑</span>
            </button>
          </div>
        </form>

        <p className="text-center text-[12px] text-muted mb-10">
          投研派可能会出错。请核对来源。
        </p>

        {/* Try an example */}
        <div className="text-center">
          <p className="eyebrow mb-4">✨ 试试这些例子</p>
          <div className="flex flex-wrap justify-center gap-2">
            {examples.map((e) => (
              <button
                key={e.label}
                onClick={() => runExample(e.query)}
                className="chip"
                title={e.query}
              >
                <span aria-hidden>{e.icon}</span>
                {e.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function ModelToggle({
  model,
  setModel,
}: {
  model: "mini" | "pro";
  setModel: (m: "mini" | "pro") => void;
}) {
  return (
    <div className="inline-flex items-center bg-soft rounded-full p-0.5 text-[12.5px]">
      {(["mini", "pro"] as const).map((m) => (
        <button
          key={m}
          type="button"
          onClick={() => setModel(m)}
          className={`px-3 py-1 rounded-full transition-colors ${
            model === m
              ? "bg-ink-900 text-cream-50 font-medium"
              : "text-ink/60 hover:text-ink"
          }`}
        >
          {m}
        </button>
      ))}
    </div>
  );
}

/* ─────────── Active research view ─────────── */

function ResearchView({
  submitted,
  tools,
  content,
  sources,
  done,
  error,
  isStreaming,
  query,
  setQuery,
  onSubmit,
  onStop,
  onNew,
  exportOpen,
  setExportOpen,
  onCopy,
  onDownload,
  onPrint,
}: {
  submitted: string;
  tools: ToolCallEntry[];
  content: string;
  sources: SourceItem[];
  done: DoneSummary | null;
  error: string | null;
  isStreaming: boolean;
  query: string;
  setQuery: (s: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  onStop: () => void;
  onNew: () => void;
  exportOpen: boolean;
  setExportOpen: (v: boolean) => void;
  onCopy: () => void;
  onDownload: (ext: "md" | "txt") => void;
  onPrint: () => void;
}) {
  return (
    <div className="hero-landscape min-h-full">
      <div className="container-page max-w-[920px] pt-12 pb-32">
        {/* Title row */}
        <div className="flex items-start justify-between gap-4 mb-8">
          <div className="flex-1 min-w-0">
            <p className="eyebrow mb-2">研究问题</p>
            <h1 className="text-[26px] sm:text-[30px] font-medium leading-snug text-ink-900 tracking-hero">
              {submitted}
            </h1>
            {done && (
              <p className="mt-3 text-[12.5px] text-muted">
                {(done.total_ms / 1000).toFixed(1)}s · {done.iterations} 轮 ·{" "}
                {done.tool_calls} 次工具调用 · {done.credits_charged.toFixed(1)}{" "}
                credits
              </p>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0 no-print">
            <button
              onClick={onNew}
              className="btn-ghost !py-2 !px-3 text-[12.5px]"
            >
              新研究
            </button>
            <ExportMenu
              open={exportOpen}
              setOpen={setExportOpen}
              onCopy={onCopy}
              onDownload={onDownload}
              onPrint={onPrint}
              disabled={!content}
            />
          </div>
        </div>

        {/* Tool trace (collapsed) */}
        {tools.length > 0 && (
          <details className="mb-6 group">
            <summary className="cursor-pointer text-[12.5px] text-ink/55 hover:text-ink list-none flex items-center gap-1.5 select-none">
              <span className="group-open:rotate-90 transition-transform">▸</span>
              查看研究过程 ({tools.filter((t) => t.status === "done").length}/
              {tools.length})
            </summary>
            <div className="mt-3 space-y-1.5 pl-4 border-l hairline">
              {tools.map((t) => (
                <div
                  key={t.id}
                  className="text-[12.5px] text-ink/65 flex items-center gap-2"
                >
                  <span
                    className={
                      t.status === "running"
                        ? "streaming-dot text-accent-blue"
                        : "text-accent-green"
                    }
                  >
                    ●
                  </span>
                  <span className="font-mono text-[11.5px] text-ink/50">
                    {t.tool}
                  </span>
                  {t.nResults !== undefined && (
                    <span className="text-muted">· {t.nResults} 条</span>
                  )}
                  {t.elapsedMs !== undefined && (
                    <span className="text-muted">
                      · {(t.elapsedMs / 1000).toFixed(1)}s
                    </span>
                  )}
                </div>
              ))}
            </div>
          </details>
        )}

        {/* Answer */}
        <div className="card-cream p-7 sm:p-9 shadow-card">
          {content ? (
            <div className="prose prose-stone max-w-none text-[15.5px] leading-[1.75] text-ink/85">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  p: ({ children }) => <p className="my-3">{renderCitations(children)}</p>,
                  li: ({ children }) => <li>{renderCitations(children)}</li>,
                  h2: ({ children }) => (
                    <h2 className="text-[20px] font-semibold mt-6 mb-3 text-ink-900">
                      {children}
                    </h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-[16.5px] font-semibold mt-5 mb-2 text-ink-900">
                      {children}
                    </h3>
                  ),
                  a: ({ children, ...rest }) => (
                    <a {...rest} className="text-accent-link hover:underline" />
                  ),
                }}
              >
                {content}
              </ReactMarkdown>
            </div>
          ) : (
            <div className="text-[14px] text-ink/50 italic">
              <span className="streaming-dot">综合中…</span>
            </div>
          )}
        </div>

        {/* Sources */}
        {sources.length > 0 && (
          <div className="mt-8">
            <p className="eyebrow mb-4">引用来源 · {sources.length} 条</p>
            <div className="space-y-2.5">
              {sources.map((s) => (
                <SourceLine key={s.n} source={s} />
              ))}
            </div>
          </div>
        )}

        {error && (
          <div className="mt-8 card-cream p-4 text-[13.5px] text-rose-700 border-rose-200">
            {error}
          </div>
        )}

        {/* Follow-up input (sticky bottom) */}
        <form
          onSubmit={onSubmit}
          className="fixed bottom-6 left-1/2 -translate-x-1/2 w-[min(720px,calc(100%-2rem))] z-30"
        >
          <div className="card-cream shadow-float p-2 pl-4 flex items-center gap-2">
            <input
              type="text"
              placeholder={
                isStreaming ? "运行中…" : "继续追问，或问一个新问题…"
              }
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={isStreaming}
              className="flex-1 bg-transparent outline-none text-[14.5px] py-2 placeholder:text-muted"
            />
            {isStreaming ? (
              <button
                type="button"
                onClick={onStop}
                className="btn-ghost !py-2 !px-3 text-[12.5px]"
              >
                停止
              </button>
            ) : (
              <button
                type="submit"
                disabled={!query.trim()}
                className="btn-primary !py-2 !px-3 text-[13px] disabled:opacity-40"
              >
                提问 ↑
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}

function SourceLine({ source: s }: { source: SourceItem }) {
  return (
    <div
      id={`source-${s.n}`}
      className="card-cream p-4 flex items-start gap-3 hover:shadow-card transition-shadow"
    >
      <span className="cite-pill shrink-0 mt-0.5 !min-w-[26px] !h-[26px] !text-[12px]">
        {s.n}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-[14px] font-medium text-ink-900 truncate">
          {s.title || "未命名"}
        </p>
        <p className="mt-0.5 text-[12.5px] text-muted">
          {[s.broker, s.date, s.source_type, s.page_no ? `第 ${s.page_no} 页` : null]
            .filter(Boolean)
            .join(" · ")}
        </p>
        {s.snippet && (
          <p className="mt-2 text-[13px] text-ink/65 line-clamp-2 leading-relaxed">
            {s.snippet}
          </p>
        )}
      </div>
      {s.url && (
        <a
          href={s.url}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 text-[12.5px] text-accent-link hover:underline"
        >
          原文 ↗
        </a>
      )}
    </div>
  );
}

function ExportMenu({
  open,
  setOpen,
  onCopy,
  onDownload,
  onPrint,
  disabled,
}: {
  open: boolean;
  setOpen: (v: boolean) => void;
  onCopy: () => void;
  onDownload: (ext: "md" | "txt") => void;
  onPrint: () => void;
  disabled: boolean;
}) {
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  // Close on Escape and restore focus to trigger
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, setOpen]);
  return (
    <div className="relative">
      <button
        ref={triggerRef}
        onClick={() => setOpen(!open)}
        disabled={disabled}
        aria-haspopup="menu"
        aria-expanded={open}
        className="btn-primary !py-2 !px-3 text-[12.5px] disabled:opacity-40"
      >
        <span aria-hidden>⬇</span> 下载
      </button>
      {open && !disabled && (
        <>
          <div
            className="fixed inset-0 z-40"
            aria-hidden
            onClick={() => setOpen(false)}
          />
          <div
            role="menu"
            aria-label="下载选项"
            className="absolute right-0 mt-2 w-52 card-cream shadow-float py-1.5 z-50"
          >
            <button
              role="menuitem"
              onClick={onCopy}
              className="w-full text-left px-3 py-2 text-[13px] text-ink/80 hover:bg-soft hover:text-ink focus:bg-soft focus:outline-none"
            >
              <span aria-hidden>📋</span> 复制为 Markdown
            </button>
            <button
              role="menuitem"
              onClick={() => onDownload("md")}
              className="w-full text-left px-3 py-2 text-[13px] text-ink/80 hover:bg-soft hover:text-ink focus:bg-soft focus:outline-none"
            >
              <span aria-hidden>📄</span> 下载 .md 文件
            </button>
            <button
              role="menuitem"
              onClick={() => onDownload("txt")}
              className="w-full text-left px-3 py-2 text-[13px] text-ink/80 hover:bg-soft hover:text-ink focus:bg-soft focus:outline-none"
            >
              <span aria-hidden>📄</span> 下载 .txt 文件
            </button>
            <button
              role="menuitem"
              onClick={onPrint}
              className="w-full text-left px-3 py-2 text-[13px] text-ink/80 hover:bg-soft hover:text-ink focus:bg-soft focus:outline-none border-t hairline mt-1 pt-2"
            >
              <span aria-hidden>🖨</span> 打印为 PDF
            </button>
          </div>
        </>
      )}
    </div>
  );
}

/* ─────────── Citation parsing helpers ─────────── */

function dispatch(
  ev: AgentEvent,
  setters: {
    setTools: React.Dispatch<React.SetStateAction<ToolCallEntry[]>>;
    setContent: React.Dispatch<React.SetStateAction<string>>;
    setSources: React.Dispatch<React.SetStateAction<SourceItem[]>>;
    setDone: React.Dispatch<React.SetStateAction<DoneSummary | null>>;
    setError: React.Dispatch<React.SetStateAction<string | null>>;
  },
) {
  switch (ev.event) {
    case "tool_call": {
      const id =
        ev.tool_call_id ||
        `${ev.tool}-${ev.iteration}-${Math.random().toString(36).slice(2, 6)}`;
      setters.setTools((prev) => [
        ...prev,
        { id, tool: ev.tool, args: ev.args, status: "running" },
      ]);
      break;
    }
    case "tool_result": {
      setters.setTools((prev) => {
        let realIdx = -1;
        if (ev.tool_call_id) {
          realIdx = prev.findIndex((t) => t.id === ev.tool_call_id);
        }
        if (realIdx === -1) {
          const reverseIdx = [...prev].reverse().findIndex(
            (t) => t.tool === ev.tool && t.status === "running",
          );
          if (reverseIdx === -1) return prev;
          realIdx = prev.length - 1 - reverseIdx;
        }
        const next = [...prev];
        next[realIdx] = {
          ...next[realIdx],
          status: "done",
          nResults: ev.n_results,
          elapsedMs: ev.elapsed_ms,
        };
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
      setters.setDone({
        total_ms: ev.total_ms,
        iterations: ev.iterations,
        tool_calls: ev.tool_calls,
        credits_charged: ev.credits_charged,
      });
      break;
    case "error":
      setters.setError(`${ev.code}: ${ev.message}`);
      break;
  }
}

function renderCitations(children: React.ReactNode): React.ReactNode {
  if (typeof children === "string") return parseCites(children);
  if (Array.isArray(children))
    return children.map((c, i) =>
      typeof c === "string" ? <span key={i}>{parseCites(c)}</span> : c,
    );
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
        title={`查看引用 [${n}]`}
        onClick={(e) => {
          e.preventDefault();
          document
            .getElementById(`source-${n}`)
            ?.scrollIntoView({ behavior: "smooth", block: "center" });
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
