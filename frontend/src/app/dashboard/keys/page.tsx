"use client";

import { useEffect, useState } from "react";
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
      <h1 className="font-serif text-[40px] tracking-tight text-ink mb-2">API Keys</h1>
      <p className="text-[14.5px] text-muted mb-10">
        所有调用必须带 <code>Authorization: Bearer rp-...</code>。**Pro / Enterprise** 档可生成多个 key。
      </p>

      <div className="border border-line p-8 mb-8">
        <div className="flex items-baseline justify-between mb-4">
          <div>
            <h3 className="font-serif text-[18px] font-semibold text-ink">Default dev key</h3>
            <p className="text-[12.5px] text-muted mt-0.5">本地 dev 环境内置</p>
          </div>
          <span className="text-[11.5px] tracking-wider uppercase text-accent">{me?.plan ?? "—"}</span>
        </div>
        <div className="flex items-center gap-3 bg-cream border border-line py-3 px-4">
          <code className="flex-1 font-mono text-[13px] text-ink break-all">
            {reveal ? fullKey : me?.api_key_prefix ?? "rp-dev-..."}
          </code>
          <button
            onClick={() => setReveal((v) => !v)}
            className="text-[12.5px] font-medium text-ink/70 hover:text-ink"
          >
            {reveal ? "Hide" : "Reveal"}
          </button>
          <button
            onClick={onCopy}
            className="text-[12.5px] font-medium text-accent hover:text-accent-hover"
          >
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </div>

      <div className="border border-line p-8 mb-8">
        <h3 className="font-serif text-[18px] font-semibold text-ink mb-3">Generate new key</h3>
        <p className="text-[14px] text-ink/70 leading-relaxed mb-4">
          M1 dev 模式下默认 key 已经够用。生产环境会启用多 key + scope + IP 白名单。
        </p>
        <button
          disabled
          className="inline-flex h-10 items-center px-5 bg-ink/10 text-ink/40 text-[13.5px] font-medium tracking-wide cursor-not-allowed"
          title="M2 启用"
        >
          + Generate (M2)
        </button>
      </div>

      <div className="border border-line p-8">
        <h3 className="font-serif text-[18px] font-semibold text-ink mb-3">用法</h3>
        <pre className="bg-cream border border-line p-4 overflow-x-auto font-mono text-[12.5px]">
          <code>{`curl -X POST https://rp.zgen.xin/v1/search \\
  -H "Authorization: Bearer rp-..." \\
  -H "Content-Type: application/json" \\
  -d '{"query":"具身智能 2026"}'`}</code>
        </pre>
      </div>
    </>
  );
}
