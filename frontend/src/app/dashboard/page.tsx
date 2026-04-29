"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { rpFetch } from "@/lib/rp-client";
import { formatNumber } from "@/lib/utils";

interface MeResp {
  api_key_prefix: string;
  plan: string;
  credits_used_this_month: number;
  credits_limit: number;
  plan_resets_on: string;
}

interface BillingResp {
  month: string;
  plan: string;
  plan_fee_cny: number;
  overage_credits: number;
  overage_fee_cny: number;
  total_due_cny: number;
}

export default function DashboardOverview() {
  const [me, setMe] = useState<MeResp | null>(null);
  const [billing, setBilling] = useState<BillingResp | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([rpFetch<MeResp>("/v1/me"), rpFetch<BillingResp>("/v1/billing")])
      .then(([m, b]) => {
        setMe(m);
        setBilling(b);
      })
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <>
      <h1 className="font-serif text-[44px] tracking-tight text-ink mb-2">Overview</h1>
      <p className="text-[15px] text-muted mb-10">
        实时数据来自 backend · `localhost:3725` · SQLite 持久化
      </p>

      {error && (
        <div className="border border-line bg-cream/60 p-4 mb-6 text-[13.5px] text-ink/80">
          ⚠️ Backend 不可达：{error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-px bg-line border border-line mb-12">
        <Stat label="Plan" value={me?.plan ?? "—"} />
        <Stat label="API key" value={me?.api_key_prefix ?? "—"} mono />
        <Stat
          label="Credits used this month"
          value={me ? formatNumber(me.credits_used_this_month) : "—"}
        />
        <Stat
          label="Credits limit"
          value={me ? formatNumber(me.credits_limit) : "—"}
        />
        <Stat
          label="Bill due"
          value={billing ? `¥${billing.total_due_cny.toLocaleString()}` : "—"}
        />
        <Stat label="Resets on" value={me?.plan_resets_on ?? "—"} />
      </div>

      <h2 className="font-serif text-[24px] mb-4">Quick actions</h2>
      <div className="grid grid-cols-2 gap-px bg-line border border-line">
        <ActionCard
          href="/dashboard/keys"
          title="Manage API keys"
          desc="生成 / 撤销 keys、设置使用范围"
        />
        <ActionCard
          href="/dashboard/usage"
          title="Usage trends"
          desc="按端点 / 日期看调用量与 credits 消耗"
        />
        <ActionCard
          href="/dashboard/billing"
          title="Billing"
          desc="月度账单 + 历史"
        />
        <ActionCard
          href="/dashboard/logs"
          title="Recent logs"
          desc="最近 100 次调用 + Replay"
        />
      </div>
    </>
  );
}

function Stat({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="bg-white p-6">
      <div className="eyebrow">{label}</div>
      <div className={`mt-2 font-serif text-[26px] tracking-tight text-ink ${mono ? "font-mono text-[16px]" : ""}`}>
        {value}
      </div>
    </div>
  );
}

function ActionCard({ href, title, desc }: { href: string; title: string; desc: string }) {
  return (
    <Link href={href} className="bg-white p-6 hover:bg-cream transition-colors group">
      <h3 className="font-serif text-[18px] font-semibold text-ink group-hover:text-accent transition-colors">
        {title} →
      </h3>
      <p className="mt-2 text-[13.5px] text-ink/70 leading-relaxed">{desc}</p>
    </Link>
  );
}
