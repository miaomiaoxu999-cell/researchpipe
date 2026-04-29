"use client";

import { useEffect, useState } from "react";
import { rpFetch } from "@/lib/rp-client";
import { formatNumber } from "@/lib/utils";

interface UsageItem {
  date: string;
  endpoint: string;
  calls: number;
  credits: number;
}

interface UsageResp {
  items: UsageItem[];
}

export default function UsagePage() {
  const [items, setItems] = useState<UsageItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    rpFetch<UsageResp>("/v1/usage")
      .then((d) => setItems(d.items || []))
      .catch((e) => setError(String(e)));
  }, []);

  // Aggregate by endpoint
  const byEndpoint = items.reduce<Record<string, { calls: number; credits: number }>>((acc, it) => {
    if (!acc[it.endpoint]) acc[it.endpoint] = { calls: 0, credits: 0 };
    acc[it.endpoint].calls += it.calls;
    acc[it.endpoint].credits += it.credits;
    return acc;
  }, {});
  const topEndpoints = Object.entries(byEndpoint)
    .sort(([, a], [, b]) => b.credits - a.credits)
    .slice(0, 10);

  // Aggregate by day
  const byDay = items.reduce<Record<string, number>>((acc, it) => {
    acc[it.date] = (acc[it.date] || 0) + it.credits;
    return acc;
  }, {});
  const dayLabels = Object.keys(byDay).sort().slice(-30);
  const maxDayCredits = Math.max(0, ...Object.values(byDay));

  const totalCalls = items.reduce((a, b) => a + b.calls, 0);
  const totalCredits = items.reduce((a, b) => a + b.credits, 0);

  return (
    <>
      <h1 className="font-serif text-[40px] tracking-tight text-ink mb-2">Usage</h1>
      <p className="text-[14.5px] text-muted mb-10">最近 30 天 · 按端点 / 按日期。数据来自 SQLite。</p>

      {error && (
        <div className="border border-line bg-cream/60 p-4 mb-6 text-[13.5px] text-ink/80">
          ⚠️ Backend 不可达：{error}
        </div>
      )}

      <div className="grid grid-cols-3 gap-px bg-line border border-line mb-10">
        <Stat label="Total calls" value={formatNumber(totalCalls)} />
        <Stat label="Total credits" value={formatNumber(Math.round(totalCredits))} />
        <Stat label="Top endpoint" value={topEndpoints[0]?.[0] ?? "—"} mono />
      </div>

      <h2 className="font-serif text-[24px] mb-3">Top endpoints</h2>
      {topEndpoints.length === 0 ? (
        <p className="text-[14px] text-muted py-4">没有调用记录。试试 <a href="/playground" className="text-accent underline">Playground</a>。</p>
      ) : (
        <div className="border border-line mb-10 overflow-x-auto">
          <table className="w-full text-[13.5px]">
            <thead className="bg-cream">
              <tr>
                <th className="text-left py-2 px-4">Endpoint</th>
                <th className="text-right py-2 px-4">Calls</th>
                <th className="text-right py-2 px-4">Credits</th>
                <th className="text-left py-2 px-4">Share</th>
              </tr>
            </thead>
            <tbody>
              {topEndpoints.map(([ep, s]) => {
                const pct = totalCredits ? (s.credits / totalCredits) * 100 : 0;
                return (
                  <tr key={ep} className="border-t border-line">
                    <td className="px-4 py-2 font-mono text-[12.5px]">{ep}</td>
                    <td className="px-4 py-2 text-right font-mono">{s.calls}</td>
                    <td className="px-4 py-2 text-right font-mono">{s.credits.toFixed(1)}</td>
                    <td className="px-4 py-2 w-[200px]">
                      <div className="h-1 bg-line relative">
                        <div className="absolute inset-y-0 left-0 bg-accent" style={{ width: `${pct}%` }} />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <h2 className="font-serif text-[24px] mb-3">Daily credits (last 30 days)</h2>
      {dayLabels.length === 0 ? (
        <p className="text-[14px] text-muted py-4">没有日度数据</p>
      ) : (
        <div className="border border-line p-6">
          <div className="flex items-end gap-1 h-[120px]">
            {dayLabels.map((d) => {
              const v = byDay[d] || 0;
              const h = maxDayCredits ? (v / maxDayCredits) * 100 : 0;
              return (
                <div key={d} className="flex-1 flex flex-col items-center group">
                  <div
                    className="w-full bg-accent/80 group-hover:bg-accent transition-colors"
                    style={{ height: `${h}%`, minHeight: v > 0 ? "2px" : "0" }}
                    title={`${d}: ${v.toFixed(1)} credits`}
                  />
                </div>
              );
            })}
          </div>
          <div className="flex items-center justify-between mt-3 text-[10.5px] text-muted">
            <span>{dayLabels[0]}</span>
            <span>{dayLabels[dayLabels.length - 1]}</span>
          </div>
        </div>
      )}
    </>
  );
}

function Stat({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="bg-white p-6">
      <div className="eyebrow">{label}</div>
      <div className={`mt-2 font-serif text-[26px] tracking-tight text-ink ${mono ? "font-mono text-[15px]" : ""}`}>
        {value}
      </div>
    </div>
  );
}
