import Link from "next/link";

const QUICK_LINKS = [
  { href: "/docs/quickstart", title: "Quickstart", desc: "60 秒拿到 API key + 第一次调用" },
  { href: "/docs/endpoints", title: "Endpoints reference", desc: "50+ 端点完整参考，含 schema + curl + Python + Node" },
  { href: "/docs/cookbook/cursor-sector-scanner", title: "Cookbook", desc: "4 篇真实场景教程：Cursor / Claude Desktop / n8n / Notion" },
  { href: "/docs/sdks", title: "SDKs", desc: "Python pip install · Node npm install · MCP npx" },
  { href: "/docs/errors", title: "Errors & rate limits", desc: "hint_for_agent 错误格式 + 429 / 401 / 502 处理" },
  { href: "/playground", title: "Playground", desc: "交互式 API 调试，支持 mock / real backend 切换" },
];

export default function DocsHome() {
  return (
    <>
      <h1 className="font-serif text-[44px] tracking-tight text-ink mb-4">投研派 Docs</h1>
      <p className="text-[16px] leading-relaxed text-ink/75 mb-10 max-w-prose">
        投研垂类的 API · SDK · MCP，为手搓 Agent 大军而生。下面是常用入口；侧边栏有完整目录。
      </p>

      <div className="grid sm:grid-cols-2 gap-px bg-line border border-line">
        {QUICK_LINKS.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className="bg-white p-6 hover:bg-cream transition-colors group"
          >
            <h3 className="font-serif text-[19px] font-semibold text-ink group-hover:text-accent transition-colors">
              {l.title} →
            </h3>
            <p className="mt-2 text-[14px] text-ink/70 leading-relaxed">{l.desc}</p>
          </Link>
        ))}
      </div>

      <div className="mt-12 border-t border-line pt-8">
        <p className="eyebrow">Status</p>
        <p className="mt-2 text-[14px] text-ink/75">
          M1 dev preview 当前版本：50 端点全开（其中 5 个真接 Tavily / DeepSeek V4 / qmp_data 一级
          deal 数据，其余 47 stub）。
        </p>
      </div>
    </>
  );
}
