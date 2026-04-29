"use client";

import { useMemo, useState } from "react";
import {
  ENDPOINTS_BY_LINE,
  DATA_GROUPS,
  type Endpoint,
  type ProductLine,
} from "@/lib/endpoints";
import { cn } from "@/lib/utils";

interface Props {
  selectedId: string;
  onSelect: (id: string) => void;
}

const LINES: ProductLine[] = ["Search", "Research", "Data", "Watch", "Account"];

export function EndpointNav({ selectedId, onSelect }: Props) {
  const [filter, setFilter] = useState("");
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const filtered = useMemo(() => {
    if (!filter) return null;
    const f = filter.toLowerCase();
    return Object.fromEntries(
      LINES.map((line) => [
        line,
        ENDPOINTS_BY_LINE[line].filter(
          (e) =>
            e.name.toLowerCase().includes(f) ||
            e.path.toLowerCase().includes(f) ||
            e.desc.toLowerCase().includes(f),
        ),
      ]),
    );
  }, [filter]);

  return (
    <aside className="w-[300px] flex-shrink-0 border-r border-line bg-cream/40 overflow-y-auto">
      <div className="p-4 sticky top-0 bg-cream/95 backdrop-blur border-b border-line">
        <input
          type="text"
          placeholder="Filter endpoints…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="w-full h-9 px-3 bg-white border border-line text-[13px] focus:outline-none focus:border-ink transition-colors"
        />
        <div className="mt-2 text-[11px] text-muted tracking-wide">
          50+ endpoints · 4 product lines
        </div>
      </div>

      <div className="p-2">
        {LINES.map((line) => {
          const list =
            filtered != null ? filtered[line] : ENDPOINTS_BY_LINE[line];
          if (!list || list.length === 0) return null;
          return (
            <ProductLineGroup
              key={line}
              line={line}
              endpoints={list}
              selectedId={selectedId}
              onSelect={onSelect}
              collapsed={collapsed[line] ?? false}
              onToggle={() => setCollapsed((c) => ({ ...c, [line]: !c[line] }))}
            />
          );
        })}
      </div>
    </aside>
  );
}

function ProductLineGroup({
  line,
  endpoints,
  selectedId,
  onSelect,
  collapsed,
  onToggle,
}: {
  line: ProductLine;
  endpoints: Endpoint[];
  selectedId: string;
  onSelect: (id: string) => void;
  collapsed: boolean;
  onToggle: () => void;
}) {
  // Data line groups by sub-category
  if (line === "Data") {
    const grouped = DATA_GROUPS.map((g) => ({
      group: g,
      items: endpoints.filter((e) => e.group === g),
    })).filter((x) => x.items.length > 0);

    return (
      <div className="mb-3">
        <button
          onClick={onToggle}
          className="w-full flex items-center justify-between px-3 py-2 text-[12px] uppercase tracking-widest font-semibold text-ink hover:text-accent transition-colors"
        >
          <span>{line}</span>
          <span className="text-muted">{endpoints.length}</span>
        </button>
        {!collapsed &&
          grouped.map(({ group, items }) => (
            <div key={group} className="mt-2 mb-3">
              <div className="px-3 py-1 text-[10.5px] uppercase tracking-wider text-muted font-medium">
                {group}
              </div>
              {items.map((ep) => (
                <EndpointRow
                  key={ep.id}
                  ep={ep}
                  selected={ep.id === selectedId}
                  onSelect={onSelect}
                />
              ))}
            </div>
          ))}
      </div>
    );
  }

  return (
    <div className="mb-3">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-3 py-2 text-[12px] uppercase tracking-widest font-semibold text-ink hover:text-accent transition-colors"
      >
        <span>{line}</span>
        <span className="text-muted">{endpoints.length}</span>
      </button>
      {!collapsed &&
        endpoints.map((ep) => (
          <EndpointRow
            key={ep.id}
            ep={ep}
            selected={ep.id === selectedId}
            onSelect={onSelect}
          />
        ))}
    </div>
  );
}

function EndpointRow({
  ep,
  selected,
  onSelect,
}: {
  ep: Endpoint;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  return (
    <button
      onClick={() => onSelect(ep.id)}
      className={cn(
        "w-full text-left px-3 py-2 group transition-colors flex items-center gap-2",
        selected
          ? "bg-ink text-white"
          : "hover:bg-white text-ink/85 hover:text-ink",
      )}
    >
      <span className="font-mono text-[12.5px] flex-1 truncate">
        {ep.name}
      </span>
      {ep.star && <span className={cn("text-[10px]", selected ? "text-white/70" : "text-accent")}>★</span>}
      <span
        className={cn(
          "text-[10px] font-medium tracking-wide px-1.5 rounded-sm",
          selected
            ? "bg-white/15 text-white/85"
            : "bg-line/60 text-muted group-hover:bg-line",
        )}
      >
        {ep.phase}
      </span>
    </button>
  );
}
