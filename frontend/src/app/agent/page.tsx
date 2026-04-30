import { ResearchApp } from "@/components/agent/ResearchApp";
import "./agent.css";

export const metadata = {
  title: "研究 — 投研派",
  description:
    "用最自然的中文问投研问题。Agent 自动拆问题、查资料、综合答案，每个观点都带出处。",
};

export default function AgentPage({
  searchParams,
}: {
  searchParams?: { q?: string };
}) {
  const initialQuery = typeof searchParams?.q === "string" ? searchParams.q : "";
  return <ResearchApp initialQuery={initialQuery} />;
}
