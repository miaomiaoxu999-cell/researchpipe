"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const SECTIONS = [
  {
    title: "Get started",
    items: [
      { href: "/docs/quickstart", label: "Quickstart" },
      { href: "/docs/sdks", label: "SDKs (Python / Node / MCP)" },
      { href: "/docs/errors", label: "Errors & rate limits" },
    ],
  },
  {
    title: "Endpoints",
    items: [
      { href: "/docs/endpoints#search", label: "Search · 6 endpoints" },
      { href: "/docs/endpoints#research", label: "Research · 3 endpoints" },
      { href: "/docs/endpoints#data", label: "Data · 38 endpoints" },
      { href: "/docs/endpoints#watch", label: "Watch · 2 endpoints" },
      { href: "/docs/endpoints#account", label: "Account · 3 endpoints" },
    ],
  },
  {
    title: "Cookbook",
    items: [
      { href: "/docs/cookbook/cursor-sector-scanner", label: "Cursor + 30min 写赛道扫描器" },
      { href: "/docs/cookbook/claude-desktop-mcp", label: "Claude Desktop + MCP 自然语言尽调" },
      { href: "/docs/cookbook/n8n-watch-digest", label: "n8n + watch digest 公众号 cron" },
      { href: "/docs/cookbook/notion-webhook", label: "Notion 看板接 webhook" },
    ],
  },
];

export function DocsSidebar() {
  const pathname = usePathname();
  return (
    <nav className="w-[280px] flex-shrink-0 border-r border-line bg-cream/40 px-6 py-10 sticky top-[72px] h-[calc(100vh-72px)] overflow-y-auto">
      <Link href="/docs" className="block mb-8">
        <div className="font-serif text-[20px] font-semibold text-ink">投研派 Docs</div>
        <div className="text-[12px] text-muted mt-1">v0.1.0 · M1 dev preview</div>
      </Link>
      {SECTIONS.map((s) => (
        <div key={s.title} className="mb-7">
          <div className="eyebrow mb-3">{s.title}</div>
          <ul className="space-y-1.5">
            {s.items.map((it) => (
              <li key={it.href}>
                <Link
                  href={it.href}
                  className={cn(
                    "block text-[13.5px] leading-snug px-2 py-1 -mx-2 transition-colors",
                    pathname === it.href.split("#")[0]
                      ? "text-ink font-medium border-l-2 border-accent"
                      : "text-ink/70 hover:text-ink",
                  )}
                >
                  {it.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}
