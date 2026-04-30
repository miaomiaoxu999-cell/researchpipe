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

  const usedPct =
    me && me.credits_limit > 0
      ? Math.min(100, (me.credits_used_this_month / me.credits_limit) * 100)
      : 0;

  return (
    <>
      <div className="mb-3">
        <span className="eyebrow">/ 我的账户</span>
      </div>
      <h1 className="text-[36px] font-medium tracking-hero leading-tight text-ink-900 mb-2">
        你好 👋
      </h1>
      <p className="text-[14.5px] text-muted mb-10">
        这里是你的研究用量、账户和账单。
      </p>

      {error && (
        <div className="card-cream p-4 mb-6 text-[13.5px] text-amber-700">
          ⚠️ 暂时连不上服务：{error}
        </div>
      )}

      {/* Credits big card */}
      <div className="card-cream p-7 mb-8">
        <div className="flex items-baseline justify-between mb-4">
          <p className="eyebrow">本月用量</p>
          <Link
            href="/dashboard/usage"
            className="text-[13px] text-accent-link hover:underline"
          >
            详细图表 →
          </Link>
        </div>
        <div className="flex items-baseline gap-3 mb-4">
          <span className="text-[40px] font-medium tracking-hero text-ink-900">
            {me ? formatNumber(me.credits_used_this_month) : "—"}
          </span>
          <span className="text-[15px] text-muted">
            / {me ? formatNumber(me.credits_limit) : "—"} credits
          </span>
        </div>
        <div className="h-2 bg-soft rounded-full overflow-hidden">
          <div
            className="h-full bg-accent-green transition-all"
            style={{ width: `${usedPct}%` }}
          />
        </div>
        <p className="mt-3 text-[12.5px] text-muted">
          {me ? `下次重置：${me.plan_resets_on}` : ""} ·{" "}
          <Link
            href="/dashboard/billing"
            className="text-accent-link hover:underline"
          >
            充值
          </Link>{" "}
          ·{" "}
          <Link href="/pricing" className="text-accent-link hover:underline">
            升级套餐
          </Link>
        </p>
      </div>

      {/* Account row */}
      <div className="grid sm:grid-cols-2 gap-5 mb-10">
        <Stat
          label="当前套餐"
          value={me?.plan ?? "—"}
          accent="green"
        />
        <Stat
          label="API Key"
          value={me?.api_key_prefix ?? "—"}
          mono
        />
        <Stat
          label="本月应付"
          value={billing ? `¥${billing.total_due_cny.toLocaleString()}` : "—"}
        />
        <Stat
          label="账单月份"
          value={billing?.month ?? "—"}
        />
      </div>

      <h2 className="text-[20px] font-medium tracking-hero mb-4">
        快捷操作
      </h2>
      <div className="grid sm:grid-cols-2 gap-3">
        <ActionCard
          icon="🔑"
          href="/dashboard/keys"
          title="管理 API Keys"
          desc="生成 / 撤销 keys，可绑定到不同应用"
        />
        <ActionCard
          icon="📊"
          href="/dashboard/usage"
          title="用量趋势"
          desc="按日期、按端点查看消耗"
        />
        <ActionCard
          icon="💳"
          href="/dashboard/billing"
          title="账单与充值"
          desc="月度账单、充值、发票"
        />
        <ActionCard
          icon="📜"
          href="/dashboard/logs"
          title="最近调用"
          desc="最近 100 次调用日志"
        />
      </div>

      <div className="mt-12 card-tan p-5 flex items-start gap-4">
        <span className="text-[22px]" aria-hidden>
          🚀
        </span>
        <div className="flex-1">
          <p className="text-[14px] font-medium text-ink-900">
            还没问过问题？
          </p>
          <p className="mt-1 text-[13.5px] text-ink/70 leading-relaxed">
            打开{" "}
            <Link
              href="/agent"
              className="text-accent-link hover:underline"
            >
              研究界面
            </Link>{" "}
            ，问一句"半导体设备国产化最新进展"，30 秒后就有一份带引用的研究报告。
          </p>
        </div>
      </div>
    </>
  );
}

function Stat({
  label,
  value,
  mono,
  accent,
}: {
  label: string;
  value: string;
  mono?: boolean;
  accent?: "green";
}) {
  return (
    <div className="card-cream p-5">
      <div className="eyebrow mb-2">{label}</div>
      <div
        className={`text-[22px] font-medium tracking-hero ${
          mono ? "font-mono text-[15px]" : ""
        } ${accent === "green" ? "text-accent-green" : "text-ink-900"}`}
      >
        {value}
      </div>
    </div>
  );
}

function ActionCard({
  href,
  title,
  desc,
  icon,
}: {
  href: string;
  title: string;
  desc: string;
  icon: string;
}) {
  return (
    <Link
      href={href}
      className="card-cream p-5 hover:shadow-card transition-shadow flex items-start gap-3 group"
    >
      <span className="text-[22px] shrink-0" aria-hidden>
        {icon}
      </span>
      <div>
        <h3 className="text-[15px] font-semibold text-ink-900 group-hover:text-accent-blue transition-colors">
          {title}
          <span className="ml-1 inline-block transition-transform group-hover:translate-x-0.5">
            →
          </span>
        </h3>
        <p className="mt-1 text-[13px] text-ink/65 leading-relaxed">{desc}</p>
      </div>
    </Link>
  );
}
