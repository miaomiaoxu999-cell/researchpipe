const TARGETS = [
  { name: "Cursor", desc: "vibe code 投研工具" },
  { name: "Claude Desktop", desc: "@researchpipe 自然语言尽调" },
  { name: "Cline / Roo", desc: "VS Code 内 agent 流" },
  { name: "Your backend", desc: "REST / SDK 直接接入" },
];

const SNIPPETS: { lang: string; code: string }[] = [
  { lang: "Python", code: "pip install researchpipe" },
  { lang: "Node", code: "npm install @researchpipe/sdk" },
  { lang: "MCP", code: "npx @researchpipe/mcp-server" },
];

export function BuiltFor() {
  return (
    <section className="py-24 border-b border-line">
      <div className="container-page">
        <div className="grid md:grid-cols-12 gap-12">
          <div className="md:col-span-4">
            <p className="eyebrow">Built for AI agent builders</p>
            <h2 className="mt-4 font-serif text-[40px] md:text-[44px] leading-[1.1] tracking-tightest text-ink">
              在 agent 工作流里<br />原生工作。
            </h2>
            <p className="mt-5 text-[15px] leading-relaxed text-ink/70 max-w-md">
              不是又一个等你登录的 SaaS Web App，而是直接装进 Cursor / Claude Desktop /
              你自家后端的投研基础设施。
            </p>
          </div>

          <div className="md:col-span-8">
            <div className="grid grid-cols-2 md:grid-cols-4 border border-line">
              {TARGETS.map((t, i) => (
                <div
                  key={t.name}
                  className={`p-6 ${
                    i % 2 === 1 ? "border-l border-line" : ""
                  } ${i >= 2 ? "border-t border-line md:border-t-0" : ""} ${
                    i >= 1 && i % 4 !== 0 ? "md:border-l" : ""
                  }`}
                >
                  <div className="font-serif text-[18px] font-semibold text-ink">
                    {t.name}
                  </div>
                  <div className="mt-2 text-[13px] text-ink/65 leading-snug">
                    {t.desc}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-8 space-y-3">
              {SNIPPETS.map((s) => (
                <div
                  key={s.lang}
                  className="flex items-center gap-4 bg-cream border border-line"
                >
                  <span className="px-4 py-3 text-[12px] font-medium tracking-widest uppercase text-muted border-r border-line w-[80px] flex-shrink-0">
                    {s.lang}
                  </span>
                  <code className="flex-1 px-4 py-3 font-mono text-[13.5px] text-ink">
                    {s.code}
                  </code>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
