"use client";

import { useEffect, useState } from "react";
import { AuthGate } from "@/components/admin/AuthGate";
import { adminFetch } from "@/lib/admin-client";

interface Health {
  files_total: number;
  chunks_total: number;
  embed_status: Record<string, number>;
  broker_top10: { broker: string; n: number }[];
  recent_failed: { id: number; title: string; embed_error: string | null }[];
  filename_patterns: Record<string, number>;
}

export default function AdminCorpus() {
  return (
    <AuthGate>
      <Inner />
    </AuthGate>
  );
}

function Inner() {
  const [data, setData] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    adminFetch<Health>("/v1/admin/corpus/health").then(setData).catch((e) => setError(String(e)));
  }, []);

  if (error) return <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>;
  if (!data) return <div className="text-slate-400 text-sm">Loading…</div>;

  const totalEmbedded = data.embed_status.embedded || 0;
  const totalSkipped = data.embed_status.skipped || 0;
  const totalFailed = data.embed_status.failed || 0;
  const totalPending = data.embed_status.pending || 0;
  const pctEmbedded = data.files_total ? ((totalEmbedded / data.files_total) * 100).toFixed(1) : "0";

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-slate-900">Corpus health</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card label="Files" value={data.files_total.toLocaleString()} />
        <Card label="Chunks" value={data.chunks_total.toLocaleString()} />
        <Card label="Embedded" value={totalEmbedded.toLocaleString()} hint={`${pctEmbedded}%`} />
        <Card label="Skipped + Failed + Pending" value={totalSkipped + totalFailed + totalPending} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Section title="Embed status">
          <KVTable rows={Object.entries(data.embed_status)} valueClass="tabular-nums text-right" />
        </Section>
        <Section title="Filename pattern distribution">
          <KVTable rows={Object.entries(data.filename_patterns)} valueClass="tabular-nums text-right" />
        </Section>
        <Section title="Top 10 brokers">
          <KVTable rows={data.broker_top10.map((r) => [r.broker, r.n])} valueClass="tabular-nums text-right" />
        </Section>
        <Section title={`Recent failed files (${data.recent_failed.length})`}>
          <div className="rounded-lg border border-slate-200 bg-white">
            {data.recent_failed.length === 0 ? (
              <div className="p-4 text-center text-sm text-slate-400">None — clean. ✨</div>
            ) : (
              <ul className="divide-y divide-slate-100 text-sm">
                {data.recent_failed.map((r) => (
                  <li key={r.id} className="p-3">
                    <div className="font-medium text-slate-800 truncate">{r.title}</div>
                    <div className="text-xs text-red-600 font-mono mt-0.5">{r.embed_error || "—"}</div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Section>
      </div>
    </div>
  );
}

function Card({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs text-slate-500 uppercase tracking-wide">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
      {hint && <div className="text-xs text-slate-400">{hint}</div>}
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

function KVTable({ rows, valueClass }: { rows: [string, number | string][]; valueClass?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
      <table className="w-full text-sm">
        <tbody>
          {rows.map(([k, v]) => (
            <tr key={k} className="border-b border-slate-100 last:border-b-0">
              <td className="p-2.5">{k}</td>
              <td className={`p-2.5 ${valueClass || ""}`}>{v}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
