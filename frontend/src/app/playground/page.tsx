import Link from "next/link";

export const metadata = {
  title: "试用 — 投研派",
  description: "看看投研派能做什么。从四种典型场景中选一个开始。",
};

const LINES = [
  {
    name: "搜索",
    pill: "pill-green",
    icon: "🔍",
    title: "全网搜原料",
    desc: "实时搜研报、新闻、公告、政策，自动去重排序。适合快速摸底某个题材。",
    examples: [
      "光伏行业 2026 出货量预测",
      "美联储 2025 年底以来表态",
      "比亚迪海外建厂最新进展",
    ],
  },
  {
    name: "研究",
    pill: "pill-purple",
    icon: "🧠",
    title: "深度合成报告",
    desc: "AI 多步骤拆解问题，调用研报库与一级数据，给你一份带引用的结构化报告。30 秒到 5 分钟。",
    examples: [
      "中信建投半导体研报核心观点",
      "宁德时代 vs 比亚迪 估值倍数对比",
      "2026 创新药出海 BD 首付款趋势",
    ],
  },
  {
    name: "数据",
    pill: "pill-yellow",
    icon: "📊",
    title: "查结构化数据",
    desc: "26K 一级 deal、5K 投资机构、2.8K 估值数据。秒级查询，自动关联实体。",
    examples: [
      "高瓴资本最近一年的医疗领域投资",
      "估值超过 100 亿的人形机器人公司",
      "宁德时代历轮融资与投资方",
    ],
  },
  {
    name: "订阅",
    pill: "pill-blue",
    icon: "🔔",
    title: "持续追踪",
    desc: "把一个研究主题订阅起来，每周收到更新摘要——新研报、新 deal、新政策。",
    examples: [
      "每周追踪：固态电池产业链",
      "每周追踪：AI 大模型出海",
      "每周追踪：美的集团动态",
    ],
  },
];

export default function PlaygroundPage() {
  return (
    <>
      <section className="hero-landscape">
        <div className="container-page pt-16 sm:pt-20 pb-10 text-center">
          <p className="text-[13px] tracking-wide text-muted mb-5">
            <span className="text-ink/50">/</span>
            <span className="text-ink/85">试用</span>
          </p>
          <h1 className="text-[36px] sm:text-[48px] font-medium tracking-hero leading-tight text-balance">
            投研派能做什么？
          </h1>
          <p className="mt-5 text-[16px] sm:text-[17px] text-ink/70 max-w-xl mx-auto">
            选一个场景，点示例直接试。或者直接{" "}
            <Link
              href="/agent"
              className="text-accent-link hover:underline"
            >
              去研究界面
            </Link>{" "}
            自由提问。
          </p>
        </div>
      </section>

      <section className="bg-cream pb-20">
        <div className="container-page grid md:grid-cols-2 gap-5">
          {LINES.map((l) => (
            <div key={l.name} className="card-cream p-7">
              <div className="flex items-center gap-3 mb-3">
                <span
                  className={`inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full text-[12px] font-medium ${l.pill}`}
                >
                  <span aria-hidden>{l.icon}</span> {l.name}
                </span>
              </div>
              <h2 className="text-[22px] font-semibold text-ink-900 leading-snug">
                {l.title}
              </h2>
              <p className="mt-3 text-[14px] text-ink/70 leading-relaxed">
                {l.desc}
              </p>

              <p className="eyebrow mt-6 mb-3">立即尝试</p>
              <div className="flex flex-wrap gap-2">
                {l.examples.map((q) => (
                  <Link
                    key={q}
                    href={`/agent?q=${encodeURIComponent(q)}`}
                    className="chip"
                    title={q}
                  >
                    {q}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Developer escape hatch */}
        <div className="container-narrow mt-16 text-center">
          <p className="eyebrow mb-3">开发者？</p>
          <p className="text-[14px] text-ink/60">
            你也可以直接调 API。{" "}
            <Link
              href="/docs/endpoints"
              className="text-accent-link hover:underline"
            >
              查看完整 API 文档 →
            </Link>
          </p>
        </div>
      </section>
    </>
  );
}
