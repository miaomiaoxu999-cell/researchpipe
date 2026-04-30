import Link from "next/link";

const NAV_LINKS = [
  { href: "/agent", label: "研究" },
  { href: "/playground", label: "试用" },
  { href: "/docs", label: "使用指南" },
  { href: "/pricing", label: "定价" },
  { href: "/about", label: "关于" },
];

export function Nav() {
  return (
    <header className="fixed top-0 left-0 right-0 z-40 bg-cream/85 backdrop-blur-md border-b hairline">
      <div className="container-page flex h-[64px] items-center justify-between">
        <Link href="/" className="flex items-baseline gap-2 group">
          <span className="text-[20px] font-semibold tracking-tight text-ink">
            投研派
          </span>
          <span className="text-[12px] font-medium tracking-wide text-muted group-hover:text-ink transition-colors">
            ResearchPipe
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-8">
          {NAV_LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="text-[14px] font-medium text-ink/80 hover:text-ink transition-colors"
            >
              {l.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <Link
            href="/dashboard"
            className="hidden sm:inline-flex h-9 items-center px-3 text-[14px] font-medium text-ink/70 hover:text-ink transition-colors"
          >
            登录
          </Link>
          <Link href="/pricing" className="btn-primary !py-2 !px-3.5 !text-[13px]">
            获取 API Key
            <span aria-hidden>→</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
