"use client";

import { formatNumber } from "@/lib/utils";

interface Props {
  used: number;
  total: number;
}

export function CreditsBar({ used, total }: Props) {
  const pct = Math.min(100, (used / total) * 100);
  return (
    <div className="border-b border-line bg-cream">
      <div className="container-page flex items-center justify-between gap-6 py-3">
        <div className="flex items-center gap-3">
          <span className="eyebrow">Plan</span>
          <span className="text-[13.5px] font-medium text-ink">Pro · ¥5,000 / mo</span>
        </div>
        <div className="flex items-center gap-4 flex-1 max-w-[420px]">
          <div className="flex-1 h-1.5 bg-line relative overflow-hidden">
            <div
              className="absolute inset-y-0 left-0 bg-accent"
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="font-mono text-[12.5px] text-ink whitespace-nowrap">
            {formatNumber(used)} / {formatNumber(total)} credits
          </span>
        </div>
        <div className="text-[12px] text-muted">Resets May 1</div>
      </div>
    </div>
  );
}
