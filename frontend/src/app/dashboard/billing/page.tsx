"use client";

import { useEffect, useState } from "react";
import { rpFetch } from "@/lib/rp-client";

interface BillingResp {
  month: string;
  plan: string;
  plan_fee_cny: number;
  overage_credits: number;
  overage_fee_cny: number;
  total_due_cny: number;
}

const PLAN_TIERS = [
  { name: "Free", price: 0, credits: "100" },
  { name: "Hobby", price: 99, credits: "2,000" },
  { name: "Starter", price: 1500, credits: "20,000" },
  { name: "Pro", price: 5000, credits: "80,000", current: true },
  { name: "Enterprise", price: 15000, credits: "300,000" },
  { name: "Flagship", price: 30000, credits: "不限" },
];

export default function BillingPage() {
  const [billing, setBilling] = useState<BillingResp | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    rpFetch<BillingResp>("/v1/billing")
      .then(setBilling)
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <>
      <h1 className="font-serif text-[40px] tracking-tight text-ink mb-2">Billing</h1>
      <p className="text-[14.5px] text-muted mb-10">月度账单实时算自 SQLite usage_log。</p>

      {error && (
        <div className="border border-line bg-cream/60 p-4 mb-6 text-[13.5px] text-ink/80">
          ⚠️ Backend 不可达：{error}
        </div>
      )}

      <div className="border border-line p-8 mb-10">
        <div className="eyebrow">Current bill · {billing?.month ?? "—"}</div>
        <div className="mt-2 flex items-baseline gap-3">
          <span className="font-serif text-[48px] tracking-tightest text-ink">
            ¥{billing?.total_due_cny?.toLocaleString() ?? "—"}
          </span>
          <span className="text-[14px] text-muted">due end of month</span>
        </div>

        <div className="mt-8 grid grid-cols-3 gap-px bg-line border border-line">
          <Row label="Plan" value={billing?.plan ?? "—"} />
          <Row label="Plan fee" value={billing ? `¥${billing.plan_fee_cny.toLocaleString()}` : "—"} />
          <Row label="Overage" value={billing ? `¥${billing.overage_fee_cny.toLocaleString()}（${billing.overage_credits} credits）` : "—"} />
        </div>
      </div>

      <h2 className="font-serif text-[24px] mb-4">Pricing tiers</h2>
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-px bg-line border border-line mb-12">
        {PLAN_TIERS.map((t) => (
          <div
            key={t.name}
            className={`p-6 ${
              billing?.plan === t.name ? "bg-ink text-white" : "bg-white"
            }`}
          >
            <div
              className={`eyebrow ${
                billing?.plan === t.name ? "text-white/70" : "text-muted"
              }`}
            >
              {t.name}
            </div>
            <div
              className={`mt-2 font-serif text-[26px] tracking-tight ${
                billing?.plan === t.name ? "text-white" : "text-ink"
              }`}
            >
              ¥{t.price.toLocaleString()}
            </div>
            <div
              className={`text-[12.5px] ${
                billing?.plan === t.name ? "text-white/75" : "text-ink/70"
              }`}
            >
              {t.credits} credits / 月
            </div>
            {billing?.plan === t.name && (
              <div className="mt-3 text-[11.5px] tracking-wider uppercase text-white/85">
                Current
              </div>
            )}
          </div>
        ))}
      </div>

      <h2 className="font-serif text-[24px] mb-3">Bill history</h2>
      <div className="border border-line p-6 text-[14px] text-muted">
        历史账单（M2 加）
      </div>
    </>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white p-5">
      <div className="eyebrow">{label}</div>
      <div className="mt-1.5 text-[15px] text-ink">{value}</div>
    </div>
  );
}
