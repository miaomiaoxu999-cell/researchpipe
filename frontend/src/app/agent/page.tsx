import { AgentChat } from "@/components/agent/AgentChat";
import "./agent.css";

export const metadata = {
  title: "Agent — ResearchPipe",
  description: "中文投研问答 · 14k+ 篇 2026 券商研报 + 一级市场 deal 数据",
};

export default function AgentPage() {
  return (
    <div className="bg-[#fafafa] py-6">
      <AgentChat />
    </div>
  );
}
