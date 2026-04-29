"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const SECTIONS = [
  {
    title: "Account",
    items: [
      { href: "/dashboard", label: "Overview" },
      { href: "/dashboard/keys", label: "API Keys" },
      { href: "/dashboard/billing", label: "Billing" },
    ],
  },
  {
    title: "Activity",
    items: [
      { href: "/dashboard/usage", label: "Usage" },
      { href: "/dashboard/logs", label: "Recent Logs" },
    ],
  },
];

export function DashboardSidebar() {
  const pathname = usePathname();
  return (
    <nav className="w-[260px] flex-shrink-0 border-r border-line bg-cream/40 px-6 py-10 sticky top-[72px] h-[calc(100vh-72px)] overflow-y-auto">
      <Link href="/dashboard" className="block mb-8">
        <div className="font-serif text-[20px] font-semibold text-ink">Dashboard</div>
        <div className="text-[12px] text-muted mt-1">Pro · ¥5,000 / mo</div>
      </Link>
      {SECTIONS.map((s) => (
        <div key={s.title} className="mb-7">
          <div className="eyebrow mb-3">{s.title}</div>
          <ul className="space-y-1.5">
            {s.items.map((it) => {
              const active = pathname === it.href;
              return (
                <li key={it.href}>
                  <Link
                    href={it.href}
                    className={cn(
                      "block text-[13.5px] leading-snug px-2 py-1 -mx-2 transition-colors",
                      active
                        ? "text-ink font-medium border-l-2 border-accent"
                        : "text-ink/70 hover:text-ink",
                    )}
                  >
                    {it.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
      <div className="mt-12 pt-6 border-t border-line text-[11.5px] text-muted leading-relaxed">
        Backend: <span className="font-mono text-ink">localhost:3725</span>
        <br />
        SQLite-backed
      </div>
    </nav>
  );
}
