import Link from "next/link";

const COLUMNS: { title: string; links: { label: string; href: string }[] }[] = [
  {
    title: "产品",
    links: [
      { label: "AI 研究助手", href: "/agent" },
      { label: "在线试用", href: "/playground" },
      { label: "定价", href: "/pricing" },
      { label: "我的账户", href: "/dashboard" },
    ],
  },
  {
    title: "资源",
    links: [
      { label: "使用指南", href: "/docs" },
      { label: "示例案例", href: "/docs/cookbook/cursor-sector-scanner" },
      { label: "更新日志", href: "/docs#changelog" },
      { label: "服务状态", href: "/docs#status" },
    ],
  },
  {
    title: "公司",
    links: [
      { label: "关于我们", href: "/about" },
      { label: "联系", href: "/about#contact" },
      { label: "服务条款", href: "/about#terms" },
      { label: "隐私政策", href: "/about#privacy" },
    ],
  },
];

export function Footer() {
  return (
    <footer className="bg-cream-200 border-t hairline mt-24 relative overflow-hidden">
      {/* CTA banner with landscape art */}
      <section className="hero-landscape">
        <div className="container-narrow py-20 text-center">
          <h2 className="text-[34px] sm:text-[40px] font-medium tracking-hero leading-tight text-balance text-ink-900">
            把投研问题变成一份带引用的报告。
          </h2>
          <div className="mt-8 flex items-center justify-center gap-4 flex-wrap">
            <Link href="/docs" className="btn-ghost">
              查看使用指南 →
            </Link>
            <Link href="/agent" className="btn-primary">
              开始研究
              <span aria-hidden>→</span>
            </Link>
          </div>
        </div>
      </section>

      <div className="container-page py-14 border-t hairline">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-10">
          <div className="col-span-2">
            <div className="flex items-baseline gap-2">
              <span className="text-[20px] font-semibold tracking-tight text-ink">
                投研派
              </span>
              <span className="text-[12px] font-medium tracking-wide text-muted">
                ResearchPipe
              </span>
            </div>
            <p className="mt-4 max-w-sm text-[14px] leading-relaxed text-ink/70">
              给投资人的 AI 研究助手。问一句话，得到一份带引用的研究报告。
            </p>
            <p className="mt-6 text-[12px] tracking-wide text-muted">
              rp.zgen.xin
            </p>
          </div>

          {COLUMNS.map((c) => (
            <div key={c.title}>
              <h4 className="eyebrow">{c.title}</h4>
              <ul className="mt-4 space-y-3">
                {c.links.map((l) => (
                  <li key={l.label}>
                    <Link
                      href={l.href}
                      className="text-[14px] text-ink/75 hover:text-ink transition-colors"
                    >
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-14 pt-8 border-t hairline flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <p className="text-[12px] text-muted tracking-wide">
            © {new Date().getFullYear()} 投研派 ResearchPipe
          </p>
          <p className="text-[12px] text-muted tracking-wide">
            为不会编程的投资人而生
          </p>
        </div>
      </div>
    </footer>
  );
}
