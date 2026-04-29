import Link from "next/link";

const CASES = [
  {
    tag: "Sector Snapshot",
    title: "具身智能赛道全景",
    desc: "一次拿全景：研报字段 + 主要 deals + 估值锚 + 头部公司 + 政策信号。30 分钟搞定一周的赛道扫描。",
    endpoint: "research/sector",
    prefill: { input: "具身智能", time_range: "24m" },
    cost: "≈ 50 credits",
  },
  {
    tag: "Company Due Diligence",
    title: "宁德时代深度尽调",
    desc: "business + 财务 5 年 + peers 估值带 + 招股书风险 + co-investors + red_flags。VC 真实尽调全要素。",
    endpoint: "research/company",
    prefill: { input: "宁德时代", focus: "business+financials+risks" },
    cost: "≈ 50 credits",
  },
  {
    tag: "Research Extraction",
    title: "半导体国产化研报抽取",
    desc: "8 篇券商研报字段化 + 海外英文一步翻译。core_thesis · target_price · key_data_points 直接喂下游 agent。",
    endpoint: "extract/research",
    prefill: { url: "https://...", source_types: "broker+overseas_ib" },
    cost: "5 credits / 篇",
  },
];

export function UseCases() {
  return (
    <section className="py-24 border-b border-line">
      <div className="container-page">
        <div className="flex items-end justify-between flex-wrap gap-6 mb-16">
          <div className="max-w-2xl">
            <p className="eyebrow">In production</p>
            <h2 className="mt-4 font-serif text-[44px] md:text-[52px] leading-[1.05] tracking-tightest text-ink text-balance">
              三个真实场景。<br />点开就跑。
            </h2>
          </div>
          <Link
            href="/playground"
            className="text-[14px] font-medium text-ink underline underline-offset-4 decoration-accent decoration-2 hover:text-accent transition-colors"
          >
            Browse all cookbook recipes →
          </Link>
        </div>

        <div className="grid md:grid-cols-3 gap-px bg-line border border-line">
          {CASES.map((c) => (
            <article key={c.title} className="bg-white p-8 flex flex-col">
              <p className="eyebrow">{c.tag}</p>
              <h3 className="mt-4 font-serif text-[24px] leading-[1.2] tracking-tight text-ink">
                {c.title}
              </h3>
              <p className="mt-4 text-[14.5px] leading-[1.6] text-ink/70 flex-1">
                {c.desc}
              </p>

              <div className="mt-6 pt-5 border-t border-line">
                <div className="font-mono text-[12.5px] text-ink/85 break-all">
                  POST /v1/{c.endpoint}
                </div>
                <div className="mt-2 flex items-center justify-between">
                  <span className="text-[12px] text-muted">{c.cost}</span>
                  <Link
                    href={`/playground?endpoint=${encodeURIComponent(
                      c.endpoint,
                    )}&prefill=${encodeURIComponent(JSON.stringify(c.prefill))}`}
                    className="text-[13px] font-medium text-accent hover:text-accent-hover transition-colors"
                  >
                    Run example →
                  </Link>
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
