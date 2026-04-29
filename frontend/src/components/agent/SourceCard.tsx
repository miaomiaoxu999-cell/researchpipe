"use client";

import { SourceItem } from "@/lib/sse-client";

const TYPE_BADGE: Record<string, { label: string; color: string }> = {
  corpus_chunk: { label: "研报全文", color: "bg-blue-50 text-blue-700 border-blue-200" },
  corpus_metadata: { label: "研报标题", color: "bg-sky-50 text-sky-700 border-sky-200" },
  qmp_company: { label: "公司", color: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  qmp_deal: { label: "融资", color: "bg-amber-50 text-amber-700 border-amber-200" },
  web: { label: "网页", color: "bg-slate-50 text-slate-700 border-slate-200" },
};

export function SourceCard({ source }: { source: SourceItem }) {
  const badge = TYPE_BADGE[source.source_type] || { label: source.source_type, color: "bg-slate-50 text-slate-700 border-slate-200" };

  return (
    <div id={`source-${source.n}`} className="rounded-md border border-slate-200 bg-white p-3 text-sm scroll-mt-20">
      <div className="flex items-start gap-2">
        <span className="cite-pill bg-slate-700 hover:bg-slate-900">{source.n}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span className={`inline-flex items-center rounded border px-1.5 py-0.5 font-medium ${badge.color}`}>
              {badge.label}
            </span>
            {source.broker && <span className="font-medium text-slate-700">{source.broker}</span>}
            {source.date && <span>· {source.date}</span>}
            {source.page_no != null && <span>· p.{source.page_no}</span>}
            {source.rerank_score != null && (
              <span title="rerank score">· {source.rerank_score.toFixed(2)}</span>
            )}
          </div>
          <div className="mt-1 font-medium text-slate-800 line-clamp-2">{source.title}</div>
          {source.snippet && (
            <div className="mt-1 text-xs text-slate-600 line-clamp-3">{source.snippet}</div>
          )}
          {source.industry_tags && source.industry_tags.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {source.industry_tags.slice(0, 5).map((t) => (
                <span key={t} className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600">
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
