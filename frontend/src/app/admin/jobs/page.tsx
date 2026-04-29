"use client";

import { useEffect, useState } from "react";
import { AuthGate } from "@/components/admin/AuthGate";
import { adminFetch } from "@/lib/admin-client";

interface Job {
  request_id: string;
  kind: string;
  status: string;
  submitted_at: number;
  completed_at: number | null;
  error_preview: string;
}

const STATUS_COLOR: Record<string, string> = {
  completed: "text-emerald-700 bg-emerald-50",
  failed: "text-red-700 bg-red-50",
  running: "text-amber-700 bg-amber-50",
  queued: "text-slate-700 bg-slate-100",
};

export default function AdminJobs() {
  return (
    <AuthGate>
      <Inner />
    </AuthGate>
  );
}

function Inner() {
  const [rows, setRows] = useState<Job[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const d = await adminFetch<{ rows: Job[] }>("/v1/admin/jobs/recent?limit=100");
        if (mounted) setRows(d.rows);
      } catch (e) {
        if (mounted) setError(String(e));
      }
    };
    load();
    const id = setInterval(load, 15_000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-slate-900">Async jobs ({rows?.length ?? "…"})</h1>
      {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      <div className="rounded-lg border border-slate-200 bg-white overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-xs text-slate-500 uppercase">
            <tr>
              <th className="text-left p-3">Request ID</th>
              <th className="text-left p-3">Kind</th>
              <th className="text-left p-3">Status</th>
              <th className="text-left p-3">Submitted</th>
              <th className="text-right p-3">Duration</th>
              <th className="text-left p-3">Error preview</th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((r) => (
              <tr key={r.request_id} className="border-t border-slate-100">
                <td className="p-3 font-mono text-xs">{r.request_id.slice(0, 18)}</td>
                <td className="p-3">{r.kind}</td>
                <td className="p-3">
                  <span className={`inline-flex rounded px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[r.status] || "bg-slate-100"}`}>
                    {r.status}
                  </span>
                </td>
                <td className="p-3 text-slate-500">{new Date(r.submitted_at * 1000).toLocaleString()}</td>
                <td className="p-3 text-right tabular-nums">
                  {r.completed_at ? `${(r.completed_at - r.submitted_at).toFixed(1)}s` : "—"}
                </td>
                <td className="p-3 text-xs text-red-600 truncate max-w-md">{r.error_preview || "—"}</td>
              </tr>
            ))}
            {rows && rows.length === 0 && (
              <tr>
                <td colSpan={6} className="p-6 text-center text-slate-400">
                  No jobs yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
