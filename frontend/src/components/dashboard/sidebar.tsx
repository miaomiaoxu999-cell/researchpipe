"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const SECTIONS = [
  {
    title: "账户",
    items: [
      { href: "/dashboard", label: "总览" },
      { href: "/dashboard/keys", label: "API Keys" },
      { href: "/dashboard/billing", label: "账单与充值" },
    ],
  },
  {
    title: "活动",
    items: [
      { href: "/dashboard/usage", label: "用量趋势" },
      { href: "/dashboard/logs", label: "最近调用" },
    ],
  },
];

export function DashboardSidebar() {
  const pathname = usePathname();
  return (
    <nav className="w-[240px] flex-shrink-0 border-r hairline bg-cream-200 px-5 py-10 sticky top-[64px] h-[calc(100vh-64px)] overflow-y-auto">
      <Link href="/dashboard" className="block mb-8">
        <div className="text-[16px] font-semibold text-ink-900">我的账户</div>
        <div className="text-[11.5px] text-muted mt-1">投研派 ResearchPipe</div>
      </Link>
      {SECTIONS.map((s) => (
        <div key={s.title} className="mb-7">
          <div className="eyebrow mb-3">{s.title}</div>
          <ul className="space-y-1">
            {s.items.map((it) => {
              const active = pathname === it.href;
              return (
                <li key={it.href}>
                  <Link
                    href={it.href}
                    className={cn(
                      "block text-[13px] leading-snug px-2 py-1.5 -mx-2 rounded-md transition-colors",
                      active
                        ? "text-ink-900 font-medium bg-soft"
                        : "text-ink/70 hover:text-ink hover:bg-soft",
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
      <div className="mt-10 pt-6 border-t hairline text-[11.5px] text-muted leading-relaxed">
        需要帮助？
        <br />
        <Link href="/about#contact" className="text-accent-link hover:underline">
          联系我们 →
        </Link>
      </div>
    </nav>
  );
}
