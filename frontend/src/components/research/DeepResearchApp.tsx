"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  runDeepResearch,
  type DREvent,
  type SourceItem,
} from "@/lib/deep-research-client";
import { ReasoningTrace, type SearchBatch, type TraceStep } from "./ReasoningTrace";

const FALLBACK_BACKEND = "http://localhost:3725";
const PUBLIC_DEMO_KEY = "rp-demo-public";

const EXAMPLES = [
  "美国 2026 原油库存与油价中枢预测",
  "固态电池 2026 量产时间表与产业链关键供应商",
  "比亚迪 vs 特斯拉 2026 估值倍数对比",
  "中国机器人灵巧手赛道 2026 融资动态",
];

function getBackendUrl() {
  return process.env.NEXT_PUBLIC_RP_BACKEND_URL || FALLBACK_BACKEND;
}

function getDefaultKey() {
  if (typeof window === "undefined") return PUBLIC_DEMO_KEY;
  return localStorage.getItem("rp_api_key") || process.env.NEXT_PUBLIC_RP_API_KEY || PUBLIC_DEMO_KEY;
}

export function DeepResearchApp({ initialQuery = "" }: { initialQuery?: string }) {
  const [apiKey, setApiKey] = useState<string>("");
  const [question, setQuestion] = useState(initialQuery);
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [steps, setSteps] = useState<TraceStep[]>([]);
  const [batches, setBatches] = useState<SearchBatch[]>([]);
  const [report, setReport] = useState("");
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [reportUrl, setReportUrl] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [finished, setFinished] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsedSec, setElapsedSec] = useState(0);

  const abortRef = useRef<AbortController | null>(null);
  const startedAtRef = useRef<number>(0);

  useEffect(() => {
    setApiKey(getDefaultKey());
  }, []);

  // Tick elapsed counter while running.
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => {
      setElapsedSec((Date.now() - startedAtRef.current) / 1000);
    }, 250);
    return () => clearInterval(id);
  }, [running]);

  function reset() {
    setSteps([]);
    setBatches([]);
    setReport("");
    setSources([]);
    setReportUrl(null);
    setError(null);
    setFinished(false);
    setElapsedSec(0);
  }

  function start(q: string) {
    if (!q.trim() || running) return;
    reset();
    setSubmitted(q);
    setRunning(true);
    startedAtRef.current = Date.now();

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    (async () => {
      try {
        const stream = runDeepResearch({
          question: q,
          apiKey,
          baseUrl: getBackendUrl(),
          signal: ctrl.signal,
        });
        for await (const ev of stream) {
          handleEvent(ev);
        }
      } catch (err) {
        const e = err as Error;
        if (e.name === "AbortError") return;
        setError(e.message);
      } finally {
        setRunning(false);
      }
    })();
  }

  function handleEvent(ev: DREvent) {
    switch (ev.event) {
      case "step":
        setSteps((prev) => upsertStep(prev, {
          id: ev.step_id,
          name: ev.name,
          status: ev.status,
          message: ev.content,
          queries: (ev.extra?.queries as string[] | undefined) || undefined,
          research_steps: (ev.extra?.research_steps as string[] | undefined) || undefined,
        }));
        break;
      case "queries":
        setSteps((prev) => prev.map((s) => s.name === "planning" ? { ...s, queries: ev.queries } : s));
        break;
      case "search_batch_start":
        setBatches((prev) => [...prev, { id: ev.batch_id, query: ev.query, status: "running", results: [] }]);
        break;
      case "search_result":
        setBatches((prev) => prev.map((b) =>
          b.id === ev.batch_id
            ? { ...b, results: [...b.results, { batch_id: ev.batch_id, title: ev.title, url: ev.url, snippet: ev.snippet, providers: ev.providers }] }
            : b
        ));
        break;
      case "search_batch_done":
        setBatches((prev) => prev.map((b) =>
          b.id === ev.batch_id ? { ...b, status: ev.error ? "error" : "done" } : b
        ));
        break;
      case "thinking":
        // surface as an inline message under the most recent in_progress step
        setSteps((prev) => prev.map((s, i, arr) => i === arr.length - 1 && s.status === "running" ? { ...s, message: ev.content } : s));
        break;
      case "report_delta":
        setReport((prev) => prev + ev.delta);
        break;
      case "sources":
        setSources(ev.sources);
        break;
      case "done":
        setReportUrl(ev.report_url);
        setFinished(true);
        break;
      case "error":
        setError(`${ev.code}: ${ev.message}`);
        break;
    }
  }

  function stop() {
    abortRef.current?.abort();
    setRunning(false);
  }

  // Initial form state — no question submitted yet.
  if (!submitted) {
    return (
      <div className="container-narrow pt-12 pb-24">
        <h1 className="text-[36px] sm:text-[44px] font-medium tracking-tight text-ink-900 leading-[1.1] text-balance">
          深度研究
        </h1>
        <p className="mt-4 text-[16px] text-ink/65 leading-relaxed">
          提一个投研问题，AI 会自动拟订研究计划、并行搜索多个数据源、综合成一份带引用的报告。
        </p>

        <form
          className="mt-8"
          onSubmit={(e) => {
            e.preventDefault();
            start(question);
          }}
        >
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="例如：美国 2026 原油库存与油价中枢预测"
            rows={3}
            className="w-full resize-none rounded-2xl border hairline bg-white/70 px-5 py-4 text-[15px] text-ink placeholder:text-ink/35 focus:outline-none focus:ring-2 focus:ring-ink/15"
          />
          <div className="mt-4 flex items-center justify-between gap-3 flex-wrap">
            <p className="text-[12px] text-muted">
              通常 2-4 分钟出一份 4000+ 字的报告 · 已注入 Tavily / Bocha / Serper 三路检索
            </p>
            <button
              type="submit"
              disabled={!question.trim()}
              className="btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
            >
              开始深度研究
              <span aria-hidden>→</span>
            </button>
          </div>
        </form>

        <div className="mt-10">
          <p className="eyebrow mb-3">试试这些</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => setQuestion(ex)}
                className="text-[13px] px-3 py-1.5 rounded-full border hairline bg-white/60 text-ink/75 hover:text-ink hover:border-ink/30 transition-colors"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // Running / finished view.
  return (
    <div className="container-page pt-8 pb-24">
      <div className="max-w-[820px] mx-auto">
        <button
          type="button"
          onClick={() => {
            stop();
            setSubmitted(null);
            reset();
          }}
          className="text-[13px] text-ink/60 hover:text-ink mb-3 inline-flex items-center gap-1.5"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
          新研究
        </button>
        <h1 className="text-[24px] sm:text-[28px] font-medium leading-tight text-ink-900">
          {submitted}
        </h1>

        <div className="mt-6 space-y-6">
          <ReasoningTrace
            elapsedSec={elapsedSec}
            steps={steps}
            batches={batches}
            finished={finished}
          />

          {report && (
            <article className="rounded-2xl border hairline bg-white/80 px-6 sm:px-10 py-8 sm:py-10">
              <div className="prose prose-neutral max-w-none prose-headings:font-medium prose-h2:text-[22px] prose-h2:mt-8 prose-h2:mb-3 prose-h3:text-[18px] prose-h3:mt-6 prose-h3:mb-2 prose-p:text-[14.5px] prose-p:leading-[1.75] prose-li:text-[14.5px] prose-table:text-[13px]">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{report}</ReactMarkdown>
              </div>
              {finished && reportUrl && (
                <div className="mt-8 pt-6 border-t hairline flex items-center justify-between">
                  <p className="text-[12px] text-muted">
                    {sources.length} 条来源 · {Math.round(elapsedSec)}s
                  </p>
                  <a
                    href={`${getBackendUrl()}${reportUrl}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-primary !py-2 !px-3.5 !text-[13px]"
                  >
                    下载 .md
                  </a>
                </div>
              )}
            </article>
          )}

          {sources.length > 0 && (
            <section className="rounded-2xl border hairline bg-white/60 p-5 sm:p-6">
              <h2 className="text-[14px] font-medium text-ink mb-3">参考来源</h2>
              <ol className="space-y-1.5 text-[13px]">
                {sources.map((s) => (
                  <li key={s.n} className="flex gap-2">
                    <span className="text-ink/35 tabular-nums shrink-0">[{s.n}]</span>
                    <a
                      href={s.url || "#"}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-ink/75 hover:text-ink line-clamp-1"
                    >
                      {s.title || s.url}
                    </a>
                  </li>
                ))}
              </ol>
            </section>
          )}

          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50/70 px-4 py-3 text-[13px] text-red-700">
              {error}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function upsertStep(prev: TraceStep[], next: TraceStep): TraceStep[] {
  // One step per step_id — replace if existing.
  const i = prev.findIndex((s) => s.id === next.id);
  if (i === -1) return [...prev, next];
  const merged = { ...prev[i], ...next, queries: next.queries ?? prev[i].queries, research_steps: next.research_steps ?? prev[i].research_steps };
  const out = [...prev];
  out[i] = merged;
  return out;
}
