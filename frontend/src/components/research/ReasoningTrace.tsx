"use client";

import { useState } from "react";
import type { StepName, StepStatus, SearchResultItem } from "@/lib/deep-research-client";

export interface SearchBatch {
  id: number;
  query: string;
  status: "running" | "done" | "error";
  results: SearchResultItem[];
}

export interface TraceStep {
  id: number;
  name: StepName;
  status: StepStatus;
  message: string;
  queries?: string[];
  research_steps?: string[];
}

interface Props {
  elapsedSec: number;
  steps: TraceStep[];
  batches: SearchBatch[];
  finished: boolean;
}

const STEP_LABEL: Record<StepName, string> = {
  planning: "Planning",
  searching: "Searching",
  reporting: "Reporting",
  exporting: "Exporting",
};

export function ReasoningTrace({ elapsedSec, steps, batches, finished }: Props) {
  return (
    <div className="rounded-2xl border hairline bg-white/60 backdrop-blur-sm p-5 sm:p-6">
      <header className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-medium text-ink/80">Reasoning Trace</span>
          {!finished && (
            <span className="inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
          )}
        </div>
        <span className="text-[12px] text-muted tabular-nums">
          {formatElapsed(elapsedSec)}
        </span>
      </header>

      <ol className="relative">
        {/* vertical guide line */}
        <div className="absolute left-[7px] top-2 bottom-2 w-px bg-ink/10" aria-hidden />

        {steps.map((step) => (
          <StepRow
            key={`${step.id}-${step.name}-${step.status}`}
            step={step}
            batches={step.name === "searching" ? batches : []}
          />
        ))}
      </ol>
    </div>
  );
}

function StepRow({ step, batches }: { step: TraceStep; batches: SearchBatch[] }) {
  const [open, setOpen] = useState(true);
  const hasNested = step.queries?.length || batches.length > 0 || step.research_steps?.length;

  return (
    <li className="relative pl-6 pb-4 last:pb-0">
      <span
        className="absolute left-0 top-0.5 flex h-3.5 w-3.5 items-center justify-center"
        aria-hidden
      >
        <StatusDot status={step.status} />
      </span>

      <button
        type="button"
        onClick={() => hasNested && setOpen((o) => !o)}
        className={`flex items-center gap-2 text-left ${hasNested ? "cursor-pointer hover:text-ink" : "cursor-default"}`}
      >
        <span className="text-[14px] font-medium text-ink">{STEP_LABEL[step.name]}</span>
        {hasNested && (
          <ChevronIcon className={`h-3 w-3 text-ink/40 transition-transform ${open ? "rotate-90" : ""}`} />
        )}
      </button>

      <p className="mt-0.5 text-[13px] text-ink/65 leading-relaxed">{step.message}</p>

      {open && hasNested && (
        <div className="mt-3 space-y-2.5">
          {step.queries && step.queries.length > 0 && (
            <ul className="space-y-1 text-[12.5px]">
              {step.queries.map((q, i) => (
                <li key={i} className="flex items-start gap-2 text-ink/70">
                  <span className="text-ink/30 tabular-nums">{String(i + 1).padStart(2, "0")}</span>
                  <span className="font-mono text-[12px] leading-relaxed">{q}</span>
                </li>
              ))}
            </ul>
          )}

          {batches.length > 0 && (
            <div className="space-y-2">
              {batches.map((b) => (
                <BatchBlock key={b.id} batch={b} />
              ))}
            </div>
          )}
        </div>
      )}
    </li>
  );
}

function BatchBlock({ batch }: { batch: SearchBatch }) {
  const [open, setOpen] = useState(false);
  const isDone = batch.status === "done";
  return (
    <div className="rounded-lg border hairline bg-cream/60">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left text-[12.5px]"
      >
        <span className="flex h-3 w-3 items-center justify-center" aria-hidden>
          <StatusDot status={isDone ? "success" : batch.status === "error" ? "error" : "running"} />
        </span>
        <span className="text-ink/55 font-medium">
          {isDone ? "Search Complete" : batch.status === "error" ? "Search Failed" : "Searching..."}
        </span>
        <span className="text-ink/40 tabular-nums">·</span>
        <span className="text-ink/40 tabular-nums">{batch.results.length}</span>
        <span className="text-ink/55 font-mono truncate flex-1">{batch.query}</span>
        <ChevronIcon className={`h-3 w-3 text-ink/40 transition-transform shrink-0 ${open ? "rotate-90" : ""}`} />
      </button>
      {open && batch.results.length > 0 && (
        <ul className="px-3 pb-2.5 pt-0.5 space-y-1.5 border-t hairline">
          {batch.results.map((r, i) => (
            <li key={i} className="text-[12px] leading-relaxed">
              <a
                href={r.url || "#"}
                target="_blank"
                rel="noopener noreferrer"
                className="text-ink/70 hover:text-ink underline-offset-2 hover:underline line-clamp-1"
              >
                {r.title || r.url}
              </a>
              {r.snippet && (
                <p className="text-ink/45 line-clamp-1 mt-0.5">{r.snippet}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function StatusDot({ status }: { status: StepStatus | "running" | "success" | "error" }) {
  if (status === "running") {
    return <span className="h-2.5 w-2.5 rounded-full border border-emerald-500 border-t-transparent animate-spin" />;
  }
  if (status === "error") {
    return <span className="h-2.5 w-2.5 rounded-full bg-red-500" />;
  }
  return (
    <svg viewBox="0 0 12 12" className="h-3 w-3 text-emerald-500" fill="currentColor">
      <circle cx="6" cy="6" r="5.5" fill="none" stroke="currentColor" strokeWidth="1.2" />
      <path d="M3.5 6.2 5.2 7.8 8.5 4.5" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={className}>
      <path d="M9 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function formatElapsed(s: number) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return m > 0 ? `${m}m ${sec.toString().padStart(2, "0")}s` : `${sec}s`;
}
