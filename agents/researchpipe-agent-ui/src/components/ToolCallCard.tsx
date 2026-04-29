"use client";

const TOOL_LABELS: Record<string, { icon: string; label: string }> = {
  search_corpus_semantic: { icon: "🧠", label: "语义检索研报内容" },
  search_corpus_metadata: { icon: "📂", label: "搜索研报标题" },
  search_companies: { icon: "🏢", label: "查询公司" },
  get_company: { icon: "🏷️", label: "公司详情" },
  search_deals: { icon: "💰", label: "融资事件" },
  industry_overview: { icon: "🌐", label: "行业图谱" },
  research_sector: { icon: "📊", label: "深度行业研究" },
  web_search: { icon: "🔎", label: "网络搜索" },
};

interface Props {
  tool: string;
  args: Record<string, unknown>;
  status: "running" | "done";
  nResults?: number;
  elapsedMs?: number;
}

export function ToolCallCard({ tool, args, status, nResults, elapsedMs }: Props) {
  const meta = TOOL_LABELS[tool] || { icon: "⚙️", label: tool };
  const argSummary = summarize(args);

  return (
    <div className="my-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm">
      <div className="flex items-start gap-2">
        <span className="text-base">{meta.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-slate-700">
            {meta.label}
            {status === "running" && (
              <span className="ml-2 text-slate-400 font-normal">运行中…</span>
            )}
            {status === "done" && (
              <span className="ml-2 text-emerald-600 font-normal">
                {nResults != null ? `命中 ${nResults} 条` : "完成"}
                {elapsedMs != null && ` · ${(elapsedMs / 1000).toFixed(1)}s`}
              </span>
            )}
          </div>
          {argSummary && (
            <div className="mt-0.5 text-xs text-slate-500 truncate">{argSummary}</div>
          )}
        </div>
      </div>
    </div>
  );
}

function summarize(args: Record<string, unknown>): string {
  const parts: string[] = [];
  if (args.query) parts.push(`"${String(args.query).slice(0, 50)}"`);
  if (args.industry) parts.push(`行业=${args.industry}`);
  if (args.broker) parts.push(`broker=${args.broker}`);
  if (args.company_name) parts.push(`公司=${args.company_name}`);
  if (args.company_id) parts.push(`公司=${args.company_id}`);
  if (args.industry_id) parts.push(`行业=${args.industry_id}`);
  if (args.sector) parts.push(`赛道=${args.sector}`);
  return parts.join(" · ");
}
