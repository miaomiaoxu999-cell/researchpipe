"use client";

import { useState } from "react";
import type { Endpoint } from "@/lib/endpoints";
import { genCurl, genMcp, genNode, genPython } from "@/lib/codegen";
import { cn } from "@/lib/utils";

const TABS = ["Response", "Python", "cURL", "Node", "MCP"] as const;
type Tab = (typeof TABS)[number];

interface Props {
  endpoint: Endpoint;
  values: Record<string, unknown>;
  response: unknown | null;
  isError: boolean;
}

export function ResponseTabs({ endpoint, values, response, isError }: Props) {
  const [tab, setTab] = useState<Tab>("Response");
  const [copied, setCopied] = useState(false);

  const codeFor = (t: Tab): string => {
    switch (t) {
      case "Python":
        return genPython(endpoint, values);
      case "cURL":
        return genCurl(endpoint, values);
      case "Node":
        return genNode(endpoint, values);
      case "MCP":
        return genMcp(endpoint, values);
      default:
        return "";
    }
  };

  const responseText =
    response == null
      ? '{\n  "info": "Click Run to execute against mock data."\n}'
      : JSON.stringify(response, null, 2);

  const copyContent = tab === "Response" ? responseText : codeFor(tab);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(copyContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {}
  };

  return (
    <aside className="w-[520px] flex-shrink-0 border-l border-line bg-cream/30 flex flex-col">
      {/* Tab strip */}
      <div className="flex items-center justify-between border-b border-line bg-white">
        <div className="flex">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                "px-4 py-3 text-[13px] font-medium tracking-wide border-b-2 transition-colors",
                tab === t
                  ? "border-accent text-ink"
                  : "border-transparent text-muted hover:text-ink",
              )}
            >
              {t}
            </button>
          ))}
        </div>
        <button
          onClick={onCopy}
          className="px-4 text-[12px] font-medium text-muted hover:text-ink transition-colors"
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>

      {/* Status row (Response tab only) */}
      {tab === "Response" && response != null && (
        <div className="flex items-center gap-4 px-4 py-2.5 border-b border-line bg-white text-[12px]">
          <span
            className={cn(
              "inline-flex items-center gap-1.5 font-medium",
              isError ? "text-[#B91C1C]" : "text-[#0E7C3A]",
            )}
          >
            <span
              className={cn(
                "w-1.5 h-1.5 rounded-full",
                isError ? "bg-[#B91C1C]" : "bg-[#0E7C3A]",
              )}
            />
            {isError ? "429" : "200 OK"}
          </span>
          <span className="text-muted">·</span>
          <span className="font-mono text-muted">142 ms</span>
          <span className="text-muted">·</span>
          <span className="font-mono text-muted">x-credits-cost: {endpoint.credits}</span>
        </div>
      )}

      <div className="flex-1 overflow-auto">
        <pre
          className={cn(
            "font-mono text-[12.5px] leading-[1.55] p-5 whitespace-pre-wrap break-words",
            tab === "Response" ? "text-ink" : "text-ink",
          )}
        >
          {tab === "Response" ? responseText : codeFor(tab)}
        </pre>
      </div>

      {tab === "MCP" && (
        <div className="border-t border-line bg-white p-4 text-[12px] text-muted">
          MCP Server 暴露 8 个智能 tool（聚合 50 个 HTTP 端点）。Claude Desktop / Cursor / Cline 直连。
        </div>
      )}
    </aside>
  );
}
