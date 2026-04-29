"use client";

import { useEffect, useState } from "react";
import { AuthGate } from "@/components/admin/AuthGate";
import { adminFetch } from "@/lib/admin-client";

interface Overview {
  accounts: { total: number };
  usage: { total_calls: number; calls_24h: number; credits_24h: number };
  jobs: { total: number; by_status: Record<string, number> };
  watchlists: { total: number };
  corpus: { files: number; chunks: number; embed_status: Record<string, number> };
}

export default function AdminOverview() {
  return (
    <AuthGate>
      <Inner />
    </AuthGate>
  );
}

function Inner() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    const tick = async () => {
      try {
        const d = await adminFetch<Overview>("/v1/admin/overview");
        if (mounted) setData(d);
      } catch (e) {
        if (mounted) setError((e as Error).message);
      }
    };
    tick();
    const id = setInterval(tick, 30_000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  if (error) return <ErrorBanner err={error} />;
  if (!data) return <div className="text-slate-400 text-sm">Loading overview…</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-slate-900">Overview</h1>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card label="API Keys" value={data.accounts.total} hint="Total accounts" />
        <Card label="Calls (24h)" value={data.usage.calls_24h} hint={`${data.usage.total_calls} total`} />
        <Card label="Credits (24h)" value={data.usage.credits_24h.toFixed(1)} />
        <Card label="Watchlists" value={data.watchlists.total} />
      </div>

      {/* Corpus */}
      <Section title="2026 研报合集">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card label="Files" value={data.corpus.files.toLocaleString()} />
          <Card label="Chunks" value={data.corpus.chunks.toLocaleString()} />
          <Card
            label="Embedded"
            value={(data.corpus.embed_status?.embedded || 0).toLocaleString()}
            hint={`${pct(data.corpus.embed_status?.embedded, data.corpus.files)}%`}
          />
          <Card
            label="Skipped + Failed"
            value={
              (data.corpus.embed_status?.skipped || 0) + (data.corpus.embed_status?.failed || 0)
            }
            hint="Looks scanned / no_text / parse_failed"
          />
        </div>
      </Section>

      {/* Jobs */}
      <Section title="Async Jobs">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card label="Total" value={data.jobs.total} />
          {Object.entries(data.jobs.by_status).map(([k, v]) => (
            <Card key={k} label={k} value={v} />
          ))}
        </div>
      </Section>
    </div>
  );
}

function Card({ label, value, hint }: { label: string; value: number | string; hint?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs text-slate-500 uppercase tracking-wide">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-slate-400">{hint}</div>}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="mb-2 text-sm font-medium text-slate-700 uppercase tracking-wide">{title}</h2>
      {children}
    </div>
  );
}

function ErrorBanner({ err }: { err: string }) {
  return <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{err}</div>;
}

function pct(n: number | undefined, d: number) {
  if (!n || !d) return "0";
  return ((n / d) * 100).toFixed(1);
}
