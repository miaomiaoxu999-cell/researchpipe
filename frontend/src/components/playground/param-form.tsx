"use client";

import { useEffect, useState } from "react";
import type { Endpoint, ParamSpec } from "@/lib/endpoints";
import { estimateCredits } from "@/lib/endpoints";
import { cn } from "@/lib/utils";

interface Props {
  endpoint: Endpoint;
  values: Record<string, unknown>;
  onChange: (next: Record<string, unknown>) => void;
  onRun: () => void;
  running: boolean;
}

export function ParamForm({ endpoint, values, onChange, onRun, running }: Props) {
  // Cmd+Enter to run
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        onRun();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onRun]);

  const credits = estimateCredits(endpoint, values);
  const setField = (name: string, v: unknown) => onChange({ ...values, [name]: v });

  return (
    <div className="flex-1 min-w-0 overflow-y-auto">
      <div className="p-8 max-w-[640px]">
        <div className="flex items-baseline gap-3 flex-wrap">
          <span className="font-mono text-[12px] text-muted">{endpoint.code}</span>
          <h2 className="font-serif text-[28px] tracking-tight text-ink">
            {endpoint.name}
          </h2>
          {endpoint.star && (
            <span className="text-[11px] tracking-widest uppercase text-accent font-semibold">
              Flagship
            </span>
          )}
        </div>

        <div className="mt-3 font-mono text-[13px] text-ink/85 break-all">
          {endpoint.path}
        </div>
        <p className="mt-3 text-[14px] text-ink/70 leading-relaxed">
          {endpoint.desc}
        </p>

        <div className="mt-6 grid grid-cols-3 gap-px bg-line border border-line">
          <Stat label="Phase" value={endpoint.phase} />
          <Stat label="Cost" value={`${endpoint.creditsRange ?? endpoint.credits} credits`} />
          <Stat label="Method" value={endpoint.path.split(" ")[0]} mono />
        </div>

        {endpoint.params.length === 0 ? (
          <p className="mt-10 text-[14px] text-muted italic">
            This endpoint takes no parameters.
          </p>
        ) : (
          <div className="mt-10 space-y-6">
            <h3 className="eyebrow">Parameters</h3>
            {endpoint.params.map((p) => (
              <Field
                key={p.name}
                spec={p}
                value={values[p.name] ?? p.default}
                onChange={(v) => setField(p.name, v)}
              />
            ))}
          </div>
        )}

        <div className="mt-12 pt-6 border-t border-line flex items-center justify-between gap-4 sticky bottom-0 bg-white py-5 -mx-8 px-8 -mb-8">
          <div>
            <div className="text-[11px] tracking-widest uppercase text-muted">
              Estimated cost
            </div>
            <div className="mt-1 font-serif text-[26px] tracking-tight text-ink">
              {credits} <span className="text-[14px] font-sans text-muted">credits</span>
            </div>
          </div>
          <button
            onClick={onRun}
            disabled={running}
            className="inline-flex h-11 items-center px-6 bg-ink text-white text-[14px] font-medium tracking-wide hover:bg-navy-700 disabled:opacity-50 transition-colors"
          >
            {running ? "Running…" : "Run"}
            <kbd className="ml-3 px-1.5 py-0.5 text-[11px] bg-white/15 rounded-sm font-mono tracking-normal">
              ⌘ ⏎
            </kbd>
          </button>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="bg-white px-4 py-3">
      <div className="text-[10.5px] uppercase tracking-widest text-muted">{label}</div>
      <div className={cn("mt-1 text-[13.5px] text-ink", mono && "font-mono")}>{value}</div>
    </div>
  );
}

function Field({
  spec,
  value,
  onChange,
}: {
  spec: ParamSpec;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  const id = `f-${spec.name}`;
  return (
    <div>
      <label htmlFor={id} className="flex items-center gap-2 text-[13px] font-medium text-ink mb-2">
        <span>{spec.label}</span>
        {spec.required && <span className="text-accent">*</span>}
        <code className="font-mono text-[11.5px] text-muted">{spec.name}</code>
      </label>
      {renderInput(spec, value, onChange, id)}
      {spec.help && <p className="mt-1.5 text-[12px] text-muted">{spec.help}</p>}
    </div>
  );
}

function renderInput(
  spec: ParamSpec,
  value: unknown,
  onChange: (v: unknown) => void,
  id: string,
) {
  const baseCls =
    "w-full px-3 py-2.5 bg-white border border-line text-[13.5px] focus:outline-none focus:border-ink transition-colors";

  switch (spec.kind) {
    case "text":
      return (
        <input
          id={id}
          type="text"
          value={(value as string) ?? ""}
          placeholder={spec.placeholder}
          onChange={(e) => onChange(e.target.value)}
          className={baseCls}
        />
      );
    case "textarea":
      return (
        <textarea
          id={id}
          value={(value as string) ?? ""}
          placeholder={spec.placeholder}
          onChange={(e) => onChange(e.target.value)}
          rows={5}
          className={cn(baseCls, "font-mono text-[12.5px] resize-y")}
        />
      );
    case "number":
      return (
        <input
          id={id}
          type="number"
          value={(value as number) ?? ""}
          placeholder={spec.placeholder}
          onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))}
          className={baseCls}
        />
      );
    case "select":
      return (
        <select
          id={id}
          value={(value as string) ?? (spec.default as string)}
          onChange={(e) => onChange(e.target.value)}
          className={cn(baseCls, "appearance-none bg-white pr-8")}
        >
          {spec.options?.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      );
    case "toggle":
      return (
        <button
          id={id}
          type="button"
          onClick={() => onChange(!value)}
          className={cn(
            "inline-flex items-center gap-3 text-[13px] font-medium",
            value ? "text-ink" : "text-muted",
          )}
        >
          <span
            className={cn(
              "w-10 h-5 rounded-full relative transition-colors",
              value ? "bg-ink" : "bg-line",
            )}
          >
            <span
              className={cn(
                "absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all",
                value ? "left-[22px]" : "left-0.5",
              )}
            />
          </span>
          {value ? "true" : "false"}
        </button>
      );
    case "tags": {
      const arr = (value as string[] | undefined) ?? [];
      return (
        <div className={baseCls + " flex flex-wrap gap-2 min-h-[42px]"}>
          {arr.map((t, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1.5 bg-cream border border-line px-2 py-0.5 text-[12px] font-mono"
            >
              {t}
              <button
                type="button"
                onClick={() => onChange(arr.filter((_, j) => j !== i))}
                className="text-muted hover:text-ink"
                aria-label={`Remove ${t}`}
              >
                ×
              </button>
            </span>
          ))}
          <input
            type="text"
            placeholder={arr.length === 0 ? "type & press enter…" : ""}
            className="flex-1 min-w-[120px] outline-none bg-transparent text-[13px] font-mono"
            onKeyDown={(e) => {
              const target = e.target as HTMLInputElement;
              if (e.key === "Enter" && target.value.trim()) {
                e.preventDefault();
                onChange([...arr, target.value.trim()]);
                target.value = "";
              }
            }}
          />
        </div>
      );
    }
    default:
      return null;
  }
}
