"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { rpFetch } from "@/lib/rp-client";

interface MeResp {
  api_key_prefix: string;
  plan: string;
}

export default function KeysPage() {
  const [me, setMe] = useState<MeResp | null>(null);
  const [reveal, setReveal] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    rpFetch<MeResp>("/v1/me").then(setMe).catch(() => null);
  }, []);

  const fullKey = process.env.NEXT_PUBLIC_RP_DEV_KEY || "rp-demo-public";

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(fullKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
  };

  return (
    <>
      <div className="mb-3">
        <span className="eyebrow">/ API Keys</span>
      </div>
      <h1 className="text-[34px] font-medium tracking-hero leading-tight text-ink-900 mb-2">
        你的 API Key
      </h1>
      <p className="text-[14.5px] text-muted mb-10 max-w-prose leading-relaxed">
        如果你只用网页版研究界面，不需要关心这个 Key——直接用就行。
        如果你的工程师想接入到自己的工具，把下面这个 Key 给他们。
      </p>

      <div className="card-cream p-7 mb-6">
        <div className="flex items-baseline justify-between mb-5">
          <div>
            <h3 className="text-[16.5px] font-semibold text-ink-900">默认 Key</h3>
            <p className="text-[12.5px] text-muted mt-0.5">绑定到你的账户</p>
          </div>
          <span className="inline-block px-3 py-0.5 rounded-full bg-accent-greenSoft text-accent-green text-[11.5px] font-medium">
            {me?.plan ?? "—"}
          </span>
        </div>
        <div className="flex items-center gap-3 bg-cream-50 border hairline py-3 px-4 rounded-md">
          <code className="flex-1 font-mono text-[13px] text-ink-900 break-all">
            {reveal ? fullKey : me?.api_key_prefix ?? "rp-..."}
          </code>
          <button
            onClick={() => setReveal((v) => !v)}
            className="text-[12.5px] font-medium text-ink/70 hover:text-ink"
          >
            {reveal ? "隐藏" : "显示"}
          </button>
          <button
            onClick={onCopy}
            className="text-[12.5px] font-medium text-accent-link hover:underline"
          >
            {copied ? "已复制" : "复制"}
          </button>
        </div>
        <p className="mt-4 text-[12.5px] text-muted">
          请勿把 Key 公开分享。如果泄露了，{" "}
          <Link
            href="/about#contact"
            className="text-accent-link hover:underline"
          >
            联系我们
          </Link>{" "}
          重新生成。
        </p>
      </div>

      <div className="card-cream p-7 mb-6">
        <h3 className="text-[16.5px] font-semibold text-ink-900 mb-3">
          生成新 Key
        </h3>
        <p className="text-[14px] text-ink/70 leading-relaxed mb-5">
          专业版 / 企业版可生成多个 Key（不同应用用不同 Key 方便追踪用量与限权）。
          目前默认 Key 已经够用。
        </p>
        <button
          disabled
          className="inline-flex items-center gap-2 px-4 py-2 rounded-btn bg-soft text-ink/40 text-[13px] font-medium cursor-not-allowed"
          title="即将上线"
        >
          + 生成 Key（即将上线）
        </button>
      </div>

      <details className="card-cream p-7 group">
        <summary className="cursor-pointer flex items-center justify-between text-[15px] font-medium text-ink-900 list-none">
          给开发者：怎么调 API
          <span className="text-muted group-open:rotate-90 transition-transform">
            ▸
          </span>
        </summary>
        <div className="mt-5">
          <p className="text-[13.5px] text-ink/70 leading-relaxed mb-3">
            所有 API 调用都需要在 header 里带 Bearer token。
          </p>
          <pre className="bg-cream-50 border hairline rounded-md p-4 overflow-x-auto font-mono text-[12.5px] text-ink/85">
            <code>{`curl -X POST https://rp.zgen.xin/v1/agent/ask \\
  -H "Authorization: Bearer rp-..." \\
  -H "Content-Type: application/json" \\
  -d '{"query":"半导体设备国产化进展"}'`}</code>
          </pre>
          <p className="mt-4 text-[13px] text-ink/65">
            完整 API 文档：{" "}
            <Link
              href="/docs/endpoints"
              className="text-accent-link hover:underline"
            >
              /docs/endpoints →
            </Link>
          </p>
        </div>
      </details>
    </>
  );
}
