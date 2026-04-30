import Link from "next/link";

export const metadata = {
  title: "使用指南 — 投研派",
  description: "三步上手投研派：注册 → 提问 → 拿带引用的报告。",
};

const TOPICS = [
  {
    title: "快速开始",
    icon: "🚀",
    desc: "60 秒上手：注册、获取 API Key、问第一个问题。不会编程也能用。",
    href: "/docs/quickstart",
  },
  {
    title: "示例案例",
    icon: "📚",
    desc: "看看别人是怎么用的：行业研究、公司尽调、估值对标的真实使用场景。",
    href: "/docs/cookbook/cursor-sector-scanner",
  },
  {
    title: "完整 API 参考",
    icon: "📖",
    desc: "给开发者看的接口文档：50+ 端点 schema、参数、示例代码（可选）。",
    href: "/docs/endpoints",
  },
  {
    title: "技术接入",
    icon: "🔌",
    desc: "Python / Node SDK、MCP Server、Cursor 与 Claude Desktop 配置。",
    href: "/docs/sdks",
  },
];

export default function DocsHome() {
  return (
    <>
      <div className="mb-3">
        <span className="eyebrow">使用指南</span>
      </div>
      <h1 className="text-[40px] font-medium tracking-hero leading-tight text-ink-900 mb-4">
        如何使用投研派
      </h1>
      <p className="text-[16px] leading-relaxed text-ink/70 mb-12 max-w-prose">
        投研派是一个给投资人和分析师用的 AI 研究助手。
        最简单的方式：直接打开{" "}
        <Link href="/agent" className="text-accent-link hover:underline">
          研究界面
        </Link>{" "}
        问问题，不需要看任何文档。
      </p>

      {/* Topic cards */}
      <div className="grid sm:grid-cols-2 gap-4 mb-16">
        {TOPICS.map((t) => (
          <Link
            key={t.href}
            href={t.href}
            className="card-cream p-6 hover:shadow-card transition-shadow group"
          >
            <div className="flex items-center gap-3 mb-3">
              <span className="text-[24px]" aria-hidden>
                {t.icon}
              </span>
              <h3 className="text-[17px] font-semibold text-ink-900 group-hover:text-accent-blue transition-colors">
                {t.title}
                <span className="ml-1 inline-block transition-transform group-hover:translate-x-0.5">
                  →
                </span>
              </h3>
            </div>
            <p className="text-[13.5px] text-ink/70 leading-relaxed">
              {t.desc}
            </p>
          </Link>
        ))}
      </div>

      {/* Three-step "如何用" */}
      <section>
        <h2 className="text-[24px] font-medium tracking-hero mb-8">
          三步上手
        </h2>
        <ol className="space-y-6">
          {[
            {
              step: "1",
              title: "注册账户，拿到你的 API Key",
              body: "免费送 1,000 credits（够 200 次研究）。无需信用卡。",
            },
            {
              step: "2",
              title: "打开「研究」页面，问一个具体问题",
              body: '比如"半导体设备国产化最新进展"或"宁德时代固态电池量产时间表"。问得越具体，答案越聚焦。',
            },
            {
              step: "3",
              title: "拿到带引用的报告，点击下载或复制",
              body: "答案中所有数字都标注来源。不满意可以追问。可一键导出为 Markdown / PDF / 文本。",
            },
          ].map((s) => (
            <li key={s.step} className="flex items-start gap-5">
              <div className="shrink-0 w-9 h-9 rounded-full bg-soft flex items-center justify-center font-medium text-ink-900">
                {s.step}
              </div>
              <div>
                <h3 className="text-[16.5px] font-semibold text-ink-900">
                  {s.title}
                </h3>
                <p className="mt-1 text-[14px] text-ink/70 leading-relaxed">
                  {s.body}
                </p>
              </div>
            </li>
          ))}
        </ol>

        <div className="mt-10 flex gap-3">
          <Link href="/agent" className="btn-primary">
            直接开始研究
            <span aria-hidden>→</span>
          </Link>
          <Link href="/pricing" className="btn-ghost">
            查看定价
          </Link>
        </div>
      </section>

      {/* Status note */}
      <div className="mt-20 pt-8 border-t hairline">
        <p className="eyebrow mb-2">服务状态</p>
        <p className="text-[13.5px] text-ink/65 leading-relaxed">
          目前覆盖 14,000 多篇 2026 年券商研报与一级市场 deal 数据。研报库每周三更新。
          技术状态：M1 dev preview，研究端点已接 DeepSeek V4 Pro + Tavily Search。
        </p>
      </div>
    </>
  );
}
