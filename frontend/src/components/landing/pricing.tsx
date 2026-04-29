import Link from "next/link";

const TIERS = [
  {
    name: "Free",
    price: "¥0",
    credits: "100 credits / 月",
    audience: "试水",
    highlight: false,
  },
  {
    name: "Hobby",
    price: "¥99",
    credits: "2,000 credits / 月",
    audience: "个人 KOL",
    highlight: false,
  },
  {
    name: "Starter",
    price: "¥1,500",
    credits: "20,000 credits / 月",
    audience: "独立分析师",
    highlight: true,
  },
  {
    name: "Pro",
    price: "¥5,000",
    credits: "80,000 credits / 月",
    audience: "VC / 小团队",
    highlight: false,
  },
  {
    name: "Enterprise",
    price: "¥15,000",
    credits: "300,000 credits / 月",
    audience: "中型机构",
    highlight: false,
  },
  {
    name: "Flagship",
    price: "¥30,000",
    credits: "不限 credits",
    audience: "头部机构",
    highlight: false,
  },
];

export function Pricing() {
  return (
    <section id="pricing" className="py-24 border-b border-line">
      <div className="container-page">
        <div className="flex items-end justify-between flex-wrap gap-6 mb-16">
          <div className="max-w-2xl">
            <p className="eyebrow">Pricing</p>
            <h2 className="mt-4 font-serif text-[44px] md:text-[52px] leading-[1.05] tracking-tightest text-ink text-balance">
              按 credits 计费。<br />一个端点 0.5 到 100 credits，写得很清楚。
            </h2>
          </div>
          <Link
            href="/#full-pricing"
            className="text-[14px] font-medium text-ink underline underline-offset-4 decoration-accent decoration-2 hover:text-accent transition-colors"
          >
            See full pricing →
          </Link>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-px bg-line border border-line">
          {TIERS.map((t) => (
            <div
              key={t.name}
              className={`p-6 flex flex-col ${
                t.highlight ? "bg-ink text-white" : "bg-white"
              }`}
            >
              <div
                className={`text-[12px] tracking-widest uppercase ${
                  t.highlight ? "text-white/60" : "text-muted"
                }`}
              >
                {t.name}
              </div>
              <div
                className={`mt-3 font-serif text-[28px] tracking-tightest ${
                  t.highlight ? "text-white" : "text-ink"
                }`}
              >
                {t.price}
              </div>
              <div
                className={`mt-1 text-[12.5px] ${
                  t.highlight ? "text-white/75" : "text-ink/70"
                }`}
              >
                {t.credits}
              </div>
              <div
                className={`mt-4 pt-4 border-t text-[12px] ${
                  t.highlight
                    ? "border-white/15 text-white/65"
                    : "border-line text-muted"
                }`}
              >
                {t.audience}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-12 grid md:grid-cols-3 gap-8 border-t border-line pt-10">
          <div>
            <p className="eyebrow">Search</p>
            <p className="mt-2 text-[14px] text-ink/75 leading-relaxed">
              1–5 credits / call。同步秒级返回。
            </p>
          </div>
          <div>
            <p className="eyebrow">Research</p>
            <p className="mt-2 text-[14px] text-ink/75 leading-relaxed">
              30–100 credits / call。异步多步 LLM 编排。
            </p>
          </div>
          <div>
            <p className="eyebrow">Data</p>
            <p className="mt-2 text-[14px] text-ink/75 leading-relaxed">
              0.5–3 credits / call。结构化查询，成本最低。
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
