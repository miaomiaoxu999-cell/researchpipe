"use client";

import { useEffect, useState } from "react";
import { AuthGate } from "@/components/admin/AuthGate";
import { adminFetch } from "@/lib/admin-client";

interface Account {
  api_key: string;
  api_key_masked?: string;
  plan: string;
  credits_limit: number;
  credits_used_this_month: number;
  plan_resets_on: string | null;
  created_at: number;
  calls_24h: number;
  calls_total: number;
}

export default function AdminAccounts() {
  return (
    <AuthGate>
      <Inner />
    </AuthGate>
  );
}

function Inner() {
  const [rows, setRows] = useState<Account[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [newPlan, setNewPlan] = useState("Free");
  const [newCredits, setNewCredits] = useState(100);
  const [newKey, setNewKey] = useState<string | null>(null);

  const load = async () => {
    try {
      const d = await adminFetch<{ accounts: Account[] }>("/v1/admin/accounts");
      setRows(d.accounts);
    } catch (e) {
      setError((e as Error).message);
    }
  };
  useEffect(() => {
    load();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">API Keys ({rows?.length ?? "…"})</h1>
        <button
          onClick={() => setCreating(true)}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800"
        >
          + New key
        </button>
      </div>

      {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      {creating && (
        <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
          <div className="flex gap-3 items-end flex-wrap">
            <label className="text-sm">
              <div className="text-xs text-slate-500 mb-1">Plan</div>
              <select
                value={newPlan}
                onChange={(e) => setNewPlan(e.target.value)}
                className="rounded border border-slate-300 px-2 py-1 text-sm"
              >
                <option>Free</option>
                <option>Starter</option>
                <option>Pro</option>
                <option>Enterprise</option>
              </select>
            </label>
            <label className="text-sm">
              <div className="text-xs text-slate-500 mb-1">Credits / month</div>
              <input
                type="number"
                value={newCredits}
                onChange={(e) => setNewCredits(Number(e.target.value))}
                className="w-32 rounded border border-slate-300 px-2 py-1 text-sm"
              />
            </label>
            <button
              onClick={async () => {
                try {
                  const d = await adminFetch<{ api_key: string }>("/v1/admin/accounts", {
                    method: "POST",
                    body: JSON.stringify({ plan: newPlan, credits_limit: newCredits }),
                  });
                  setNewKey(d.api_key);
                  await load();
                } catch (e) {
                  setError((e as Error).message);
                }
              }}
              className="rounded-md bg-slate-900 px-4 py-1.5 text-sm text-white hover:bg-slate-800"
            >
              Create
            </button>
            <button
              onClick={() => {
                setCreating(false);
                setNewKey(null);
              }}
              className="text-sm text-slate-500 hover:text-slate-900"
            >
              Cancel
            </button>
          </div>
          {newKey && (
            <div className="rounded border border-emerald-200 bg-emerald-50 p-3 text-sm">
              <div className="font-medium text-emerald-800">New key created — copy it now (won't be shown again):</div>
              <code className="mt-1 block font-mono text-xs text-emerald-900 break-all">{newKey}</code>
            </div>
          )}
        </div>
      )}

      <div className="rounded-lg border border-slate-200 bg-white overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-xs text-slate-500 uppercase">
            <tr>
              <th className="text-left p-3">Key</th>
              <th className="text-left p-3">Plan</th>
              <th className="text-right p-3">Credits</th>
              <th className="text-right p-3">Calls 24h</th>
              <th className="text-right p-3">Total calls</th>
              <th className="text-left p-3">Created</th>
              <th className="text-right p-3"></th>
            </tr>
          </thead>
          <tbody>
            {rows?.map((r) => (
              <tr key={r.api_key} className="border-t border-slate-100">
                <td className="p-3 font-mono text-xs">{r.api_key}</td>
                <td className="p-3">{r.plan}</td>
                <td className="p-3 text-right tabular-nums">
                  {r.credits_used_this_month} / {r.credits_limit}
                </td>
                <td className="p-3 text-right tabular-nums">{r.calls_24h}</td>
                <td className="p-3 text-right tabular-nums">{r.calls_total}</td>
                <td className="p-3 text-slate-500">{new Date(r.created_at * 1000).toLocaleDateString()}</td>
                <td className="p-3 text-right">
                  <button
                    onClick={async () => {
                      if (!confirm("Revoke this key?")) return;
                      try {
                        await adminFetch(`/v1/admin/accounts/${encodeURIComponent(r.api_key)}`, { method: "DELETE" });
                        await load();
                      } catch (e) {
                        setError((e as Error).message);
                      }
                    }}
                    className="text-xs text-red-600 hover:text-red-800"
                  >
                    Revoke
                  </button>
                </td>
              </tr>
            ))}
            {rows && rows.length === 0 && (
              <tr>
                <td colSpan={7} className="p-6 text-center text-slate-400">
                  No accounts yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-400">
        Note: existing key value isn't recoverable from the API for safety — only newly-created keys show their secret.
        Existing rows display the masked form.
      </p>
    </div>
  );
}
