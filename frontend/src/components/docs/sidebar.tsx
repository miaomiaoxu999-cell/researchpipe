"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const SECTIONS = [
  {
    title: "开始",
    items: [
      { href: "/docs/quickstart", label: "快速开始" },
      { href: "/docs/sdks", label: "技术接入（开发者）" },
      { href: "/docs/errors", label: "错误与限流" },
    ],
  },
  {
    title: "API 参考",
    items: [
      { href: "/docs/endpoints#search", label: "搜索 · 6 个端点" },
      { href: "/docs/endpoints#research", label: "研究 · 3 个端点" },
      { href: "/docs/endpoints#data", label: "数据 · 38 个端点" },
      { href: "/docs/endpoints#watch", label: "订阅 · 2 个端点" },
      { href: "/docs/endpoints#account", label: "账户 · 3 个端点" },
    ],
  },
  {
    title: "示例案例",
    items: [
      { href: "/docs/cookbook/cursor-sector-scanner", label: "用 Cursor 30 分钟做赛道扫描器" },
      { href: "/docs/cookbook/claude-desktop-mcp", label: "Claude Desktop 自然语言尽调" },
      { href: "/docs/cookbook/n8n-watch-digest", label: "n8n 自动化推送研究" },
      { href: "/docs/cookbook/notion-webhook", label: "Notion 看板接收推送" },
    ],
  },
];

export function DocsSidebar() {
  const pathname = usePathname();
  return (
    <nav className="w-[260px] flex-shrink-0 border-r hairline bg-cream-200 px-5 py-10 sticky top-[64px] h-[calc(100vh-64px)] overflow-y-auto">
      <Link href="/docs" className="block mb-8">
        <div className="text-[16px] font-semibold text-ink-900">使用指南</div>
        <div className="text-[11.5px] text-muted mt-1">投研派 ResearchPipe</div>
      </Link>
      {SECTIONS.map((s) => (
        <div key={s.title} className="mb-7">
          <div className="eyebrow mb-3">{s.title}</div>
          <ul className="space-y-1">
            {s.items.map((it) => (
              <li key={it.href}>
                <Link
                  href={it.href}
                  className={cn(
                    "block text-[13px] leading-snug px-2 py-1.5 -mx-2 rounded-md transition-colors",
                    pathname === it.href.split("#")[0]
                      ? "text-ink-900 font-medium bg-soft"
                      : "text-ink/70 hover:text-ink hover:bg-soft",
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
