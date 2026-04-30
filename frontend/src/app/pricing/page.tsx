import Link from "next/link";

export const metadata = {
  title: "定价 — 投研派",
  description: "从免费开始，按需付费。注册即获 1,000 credits，无需信用卡。",
};

const PLANS = [
  {
    name: "免费",
    pill: "pill-green",
    price: "¥0",
    unit: "/ 月",
    tagline: "适合刚开始尝试",
    features: [
      "1,000 credits / 月（约 200 次研究）",
      "完整 14k+ 研报库 + 一级市场数据",
      "邮件支持",
      "无需信用卡",
    ],
    cta: "免费开始",
    href: "/agent",
    primary: false,
  },
  {
    name: "按量付费",
    pill: "pill-purple",
    price: "¥0.05",
    unit: "/ credit",
    tagline: "灵活，用多少付多少",
    features: [
      "无月费，余额永不过期",
      "起充 ¥99",
      "完整数据库 + 标准模型",
      "邮件支持 · 24h 响应",
    ],
    cta: "充值",
    href: "/dashboard/billing",
    primary: false,
  },
  {
    name: "专业版",
    pill: "pill-yellow",
    price: "¥1,500",
    unit: "/ 月",
    tagline: "投资人 / 分析师主推",
    features: [
      "80,000 credits / 月（约 16,000 次研究）",
      "Pro 模型（更深、更准、更长报告）",
      "更高速率 · 优先排队",
      "微信群直接支持",
      "前 3 个月免费试用",
    ],
    cta: "联系开通",
    href: "/about#contact",
    primary: true,
  },
  {
    name: "企业版",
    pill: "pill-blue",
    price: "定制",
    unit: "",
    tagline: "团队 / 基金 / 企业",
    features: [
      "无限 credits · SLA 99.9%",
      "私有部署 · 数据不出内网",
      "团队账户 · SSO",
      "专属客户成功",
    ],
    cta: "联系销售",
    href: "/about#contact",
    primary: false,
  },
];

export default function PricingPage() {
  return (
    <>
      {/* Hero */}
      <section className="hero-landscape">
        <div className="container-page pt-16 sm:pt-24 pb-12 text-center">
          <p className="text-[13px] tracking-wide text-muted mb-5">
            <span className="text-ink/50">/</span>
            <span className="text-ink/85">定价方案</span>
          </p>
          <h1 className="text-[40px] sm:text-[56px] font-medium tracking-hero leading-tight text-balance">
            从免费开始，按需付费。
          </h1>
          <p className="mt-5 text-[16px] sm:text-[17px] text-ink/70 max-w-xl mx-auto">
            注册即获 1,000 credits（约 200 次研究）。不满意随时停。
          </p>
        </div>
      </section>

      {/* Plans */}
      <section className="bg-cream">
        <div className="container-page pb-20">
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5">
            {PLANS.map((p) => (
              <div
                key={p.name}
                className={`p-6 rounded-card flex flex-col ${
                  p.primary
                    ? "bg-ink-900 text-cream-50"
                    : "card-cream"
                }`}
              >
                <div>
                  <span
                    className={`inline-block px-3 py-0.5 rounded-full text-[12px] font-medium ${
                      p.primary
                        ? "bg-cream-50 text-ink-900"
                        : p.pill
                    }`}
                  >
                    {p.name}
                  </span>
                </div>
                <div className="mt-5">
                  <span
                    className={`text-[36px] font-medium tracking-hero ${
                      p.primary ? "text-cream-50" : "text-ink-900"
                    }`}
                  >
                    {p.price}
                  </span>
                  <span
                    className={`text-[14px] ml-1 ${
                      p.primary ? "text-cream-50/70" : "text-muted"
                    }`}
                  >
                    {p.unit}
                  </span>
                </div>
                <p
                  className={`mt-2 text-[13.5px] ${
                    p.primary ? "text-cream-50/75" : "text-ink/60"
                  }`}
                >
                  {p.tagline}
                </p>
                <ul className="mt-6 space-y-2.5 flex-1">
                  {p.features.map((f) => (
                    <li
                      key={f}
                      className={`flex items-start gap-2 text-[13.5px] leading-relaxed ${
                        p.primary ? "text-cream-50/85" : "text-ink/75"
                      }`}
                    >
                      <span
                        className={`shrink-0 mt-1 ${
                          p.primary ? "text-cream-50/60" : "text-accent-green"
                        }`}
                      >
                        ●
                      </span>
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  href={p.href}
                  className={`mt-6 inline-flex items-center justify-between px-4 py-2.5 rounded-btn text-[13.5px] font-medium transition-colors ${
                    p.primary
                      ? "bg-cream-50 text-ink-900 hover:bg-cream-200"
                      : "bg-ink-900 text-cream-50 hover:bg-ink-800"
                  }`}
                >
                  {p.cta}
                  <span aria-hidden>→</span>
                </Link>
              </div>
            ))}
          </div>

          {/* Free for students card */}
          <div className="mt-10 max-w-2xl mx-auto card-tan p-6 flex items-center gap-5">
            <div className="shrink-0 w-14 h-14 rounded-card bg-cream-50/60 flex items-center justify-center text-[26px]">
              🎓
            </div>
            <div className="flex-1">
              <h3 className="text-[18px] font-semibold text-ink-900">
                学生免费
              </h3>
              <p className="mt-1 text-[14px] text-ink/70 leading-relaxed">
                我们支持学习与研究。在校生发送学生证至{" "}
                <a
                  href="mailto:hi@rp.zgen.xin"
                  className="text-accent-link hover:underline"
                >
                  hi@rp.zgen.xin
                </a>
                ，免费使用专业版。
              </p>
            </div>
          </div>

          {/* FAQ */}
          <div className="mt-20 max-w-2xl mx-auto">
            <h2 className="text-[28px] font-medium tracking-hero text-center mb-10">
              常见问题
            </h2>
            <div className="space-y-1">
              {FAQS.map((f, i) => (
                <details
                  key={i}
                  className="group border-b hairline py-4"
                >
                  <summary className="cursor-pointer flex items-center justify-between text-[15.5px] font-medium text-ink-900 list-none">
                    {f.q}
                    <span className="text-muted group-open:rotate-90 transition-transform">
                      ▸
                    </span>
                  </summary>
                  <div className="mt-3 text-[14px] text-ink/70 leading-relaxed">
                    {f.a}
                  </div>
                </details>
              ))}
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

const FAQS = [
  {
    q: "什么是 credits？",
    a: "Credits 是研究次数的内部单位。一次普通研究消耗 5 credits，一次深度研究 20 credits。1,000 credits 大约够 200 次普通研究。",
  },
  {
    q: "免费额度用完会怎样？",
    a: "会暂停服务，直到下个月重置或你升级套餐。我们不会自动扣费。",
  },
  {
    q: "能开发票吗？",
    a: "可以。支付后联系微信客服，提供开票信息即可。增值税普票和专票都支持。",
  },
  {
    q: "可以随时取消吗？",
    a: "可以。专业版按月订阅，随时停止下月不再续。已扣的当月费用按比例不退。",
  },
  {
    q: "数据是实时的吗？",
    a: "研报库每周三更新，覆盖 2026 年所有公开券商研报。一级市场 deal 数据每周自动同步。",
  },
  {
    q: "我的问题和答案会被存吗？",
    a: "默认会存在你的账户里以便回看。可以在设置里关闭历史记录。我们绝不用客户问题训练模型。",
  },
];
