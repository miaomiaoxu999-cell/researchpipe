import { DeepResearchApp } from "@/components/research/DeepResearchApp";

export const metadata = {
  title: "深度研究 — 投研派",
  description:
    "提一个投研问题，AI 会自动拟订研究计划、并行搜索多个数据源、综合成一份带引用的报告。",
};

export default function ResearchPage({
  searchParams,
}: {
  searchParams?: { q?: string };
}) {
  const initialQuery = typeof searchParams?.q === "string" ? searchParams.q : "";
  return <DeepResearchApp initialQuery={initialQuery} />;
}
