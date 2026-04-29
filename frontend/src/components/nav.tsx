import Link from "next/link";

const NAV_LINKS = [
  { href: "/playground", label: "Playground" },
  { href: "/docs", label: "Docs" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/#pricing", label: "Pricing" },
];

export function Nav() {
  return (
    <header className="fixed top-0 left-0 right-0 z-40 bg-white/85 backdrop-blur-md border-b border-line">
      <div className="container-page flex h-[72px] items-center justify-between">
        <Link href="/" className="flex items-baseline gap-2 group">
          <span className="font-serif text-[22px] font-semibold tracking-tight text-ink">
            投研派
          </span>
          <span className="font-sans text-[13px] font-medium tracking-wide text-muted group-hover:text-ink transition-colors">
            ResearchPipe
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-9">
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

        <div className="flex items-center gap-3">
          <Link
            href="/#signin"
            className="hidden sm:inline-flex h-9 items-center px-3 text-[14px] font-medium text-ink/80 hover:text-ink transition-colors"
          >
            Sign in
          </Link>
          <Link
            href="/#get-key"
            className="inline-flex h-9 items-center px-4 bg-ink text-white text-[13.5px] font-medium tracking-wide hover:bg-navy-700 transition-colors"
          >
            Get API key
            <span aria-hidden className="ml-1.5">→</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
