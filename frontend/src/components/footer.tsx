import Link from "next/link";

const COLUMNS: { title: string; links: { label: string; href: string }[] }[] = [
  {
    title: "Product",
    links: [
      { label: "Playground", href: "/playground" },
      { label: "Docs", href: "/#docs" },
      { label: "Pricing", href: "/#pricing" },
      { label: "MCP Server", href: "/#mcp" },
    ],
  },
  {
    title: "Resources",
    links: [
      { label: "Cookbook", href: "/#cookbook" },
      { label: "Changelog", href: "/#changelog" },
      { label: "Status", href: "/#status" },
      { label: "GitHub", href: "https://github.com" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", href: "/#about" },
      { label: "Contact", href: "/#contact" },
      { label: "Terms", href: "/#terms" },
      { label: "Privacy", href: "/#privacy" },
    ],
  },
];

export function Footer() {
  return (
    <footer className="bg-cream border-t border-line mt-24">
      <div className="container-page py-16">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-10">
          <div className="col-span-2">
            <div className="flex items-baseline gap-2">
              <span className="font-serif text-[22px] font-semibold tracking-tight text-ink">
                投研派
              </span>
              <span className="font-sans text-[13px] font-medium tracking-wide text-muted">
                ResearchPipe
              </span>
            </div>
            <p className="mt-4 max-w-sm text-[14px] leading-relaxed text-ink/70">
              聚焦投资与行业研究的垂类基础设施。为手搓 Agent 大军而生的
              API · SDK · MCP。
            </p>
            <p className="mt-6 text-[12px] tracking-wide text-muted">
              rp.zgen.xin · Built for analysts who code.
            </p>
          </div>

          {COLUMNS.map((c) => (
            <div key={c.title}>
              <h4 className="eyebrow font-sans">{c.title}</h4>
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

        <div className="mt-14 pt-8 border-t border-line flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <p className="text-[12px] text-muted tracking-wide">
            © {new Date().getFullYear()} ResearchPipe. All rights reserved.
          </p>
          <p className="text-[12px] text-muted tracking-wide">
            Built in WSL · Deployed on Vercel
          </p>
        </div>
      </div>
    </footer>
  );
}
