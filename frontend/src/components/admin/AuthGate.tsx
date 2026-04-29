"use client";

import { useEffect, useState } from "react";
import { getAdminKey, setAdminKey } from "@/lib/admin-client";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [keyInput, setKeyInput] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setAuthed(Boolean(getAdminKey()));
  }, []);

  if (authed === null) {
    return <div className="text-slate-400 text-sm py-12 text-center">Loading…</div>;
  }

  if (!authed) {
    return (
      <div className="max-w-md mx-auto mt-12">
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h1 className="text-lg font-semibold text-slate-900">Admin login</h1>
          <p className="mt-1 text-xs text-slate-500">Enter your `RP_ADMIN_KEY` to access internal console.</p>
          <form
            className="mt-4 flex flex-col gap-3"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              const trimmed = keyInput.trim();
              if (!trimmed) return;
              // Try a probe call
              const url = (process.env.NEXT_PUBLIC_RP_BACKEND_URL || "http://localhost:3725") + "/v1/admin/overview";
              try {
                const r = await fetch(url, { headers: { "X-Admin-Key": trimmed } });
                if (r.status === 200) {
                  setAdminKey(trimmed);
                  setAuthed(true);
                } else if (r.status === 401) {
                  setError("Invalid key.");
                } else {
                  setError(`Probe returned ${r.status}.`);
                }
              } catch (e) {
                setError(`Probe failed: ${(e as Error).message}`);
              }
            }}
          >
            <input
              type="password"
              autoFocus
              value={keyInput}
              onChange={(e) => setKeyInput(e.target.value)}
              placeholder="rp-admin-..."
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm font-mono outline-none focus:border-slate-500"
            />
            <button
              type="submit"
              className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
            >
              Login
            </button>
            {error && <div className="text-sm text-red-600">{error}</div>}
          </form>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
