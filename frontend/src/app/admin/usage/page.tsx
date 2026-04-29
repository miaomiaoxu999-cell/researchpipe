"use client";

import { useEffect, useState } from "react";
import { AuthGate } from "@/components/admin/AuthGate";
import { adminFetch } from "@/lib/admin-client";

interface ByEndpoint {
  rows: { endpoint: string; calls: number; credits: number }[];
}
interface ByDay {
  rows: { day: string; calls: number; credits: number }[];
}
interface Recent {
  rows: { api_key: string; endpoint: string; credits_charged: number; ts: number }[];
}

export default function AdminUsage() {
  return (
    <AuthGate>
      <Inner />
    </AuthGate>
  );
}

function Inner() {
  const [hours, setHours] = useState(24);
  const [byEndpoint, setByEndpoint] = useState<ByEndpoint | null>(null);
  const [byDay, setByDay] = useState<ByDay | null>(null);
  const [recent, setRecent] = useState<Recent | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async (h: number) => {
    try {
      const [a, b, c] = await Promise.all([
        adminFetch<ByEndpoint>(`/v1/admin/usage/by_endpoint?hours=${h}`),
        adminFetch<ByDay>(`/v1/admin/usage/by_day?days=14`),
        adminFetch<Recent>("/v1/admin/usage/recent?limit=50"),
      ]);
      setByEndpoint(a);
      setByDay(b);
      setRecent(c);
    } catch (e) {
      setError((e as Error).message);
    }
  };
  useEffect(() => {
    load(hours);
  }, [hours]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">Usage</h1>
        <div className="flex gap-2 text-sm">
          {[1, 24, 168, 720].map((h) => (
            <button
              key={h}
              onClick={() => setHours(h)}
              className={`rounded-md px-3 py-1.5 ${
                hours === h ? "bg-slate-900 text-white" : "border border-slate-200 hover:border-slate-300"
              }`}
            >
              {h === 1 ? "1h" : h === 24 ? "24h" : h === 168 ? "7d" : "30d"}
            </button>
          ))}
        </div>
      </div>

      {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <Section title={`By endpoint (last ${hours}h)`}>
        <Table
          rows={byEndpoint?.rows || []}
          cols={[
            { label: "Endpoint", key: "endpoint", className: "font-mono text-xs" },
            { label: "Calls", key: "calls", align: "right" },
            { label: "Credits", key: "credits", align: "right" },
          ]}
        />
      </Section>

      <Section title="By day (last 14d)">
        <Table
          rows={byDay?.rows || []}
          cols={[
            { label: "Day", key: "day" },
            { label: "Calls", key: "calls", align: "right" },
            { label: "Credits", key: "credits", align: "right" },
          ]}
        />
      </Section>

      <Section title="Recent calls (latest 50)">
        <Table
          rows={recent?.rows || []}
          cols={[
            { label: "Key", key: "api_key", className: "font-mono text-xs" },
            { label: "Endpoint", key: "endpoint", className: "font-mono text-xs" },
            { label: "Credits", key: "credits_charged", align: "right" },
            {
              label: "Time",
              key: "ts",
              render: (r) => <span className="text-slate-500">{new Date(r.ts * 1000).toLocaleString()}</span>,
            },
          ]}
        />
      </Section>
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

interface Col<R> {
  label: string;
  key: keyof R;
  align?: "left" | "right";
  className?: string;
  render?: (r: R) => React.ReactNode;
}

function Table<R extends Record<string, unknown>>({ rows, cols }: { rows: R[]; cols: Col<R>[] }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-xs text-slate-500 uppercase">
          <tr>
            {cols.map((c) => (
              <th key={String(c.key)} className={`p-2.5 ${c.align === "right" ? "text-right" : "text-left"}`}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-slate-100">
              {cols.map((c) => (
                <td
                  key={String(c.key)}
                  className={`p-2.5 ${c.align === "right" ? "text-right tabular-nums" : ""} ${c.className || ""}`}
                >
                  {c.render ? c.render(r) : String(r[c.key] ?? "")}
                </td>
              ))}
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={cols.length} className="p-4 text-center text-slate-400 text-sm">
                No data.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
