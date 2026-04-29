const PERSONAS = [
  {
    role: "VC 行研",
    quote: "30 分钟搞定一个新赛道的扫描，原来要花两天。",
    workflow: "research/sector → companies/screen → investors/portfolio",
  },
  {
    role: "公众号 KOL",
    quote: "cron 跑 watch/digest，每周一早上 8 点行业日报自动写好。",
    workflow: "watch/create → cron → research/sector → 文章模板",
  },
  {
    role: "Cursor 用户",
    quote: "vibe code 一上午，写出一个自己的赛道扫描器。",
    workflow: "pip install researchpipe → 写 100 行 Python",
  },
  {
    role: "Claude Desktop 用户",
    quote: "@researchpipe 帮我看下这家公司的红旗，Claude 自己 orchestrate。",
    workflow: "MCP Server → 8 个智能 tool → 自然语言尽调",
  },
];

export function Audience() {
  return (
    <section className="py-24 border-b border-line bg-cream">
      <div className="container-page">
        <div className="max-w-2xl">
          <p className="eyebrow">Who builds with ResearchPipe</p>
          <h2 className="mt-4 font-serif text-[40px] md:text-[44px] leading-[1.1] tracking-tightest text-ink text-balance">
            四类人，<br />同一套基础设施。
          </h2>
        </div>

        <div className="mt-14 grid md:grid-cols-2 gap-x-12 gap-y-10">
          {PERSONAS.map((p) => (
            <div key={p.role} className="border-l-2 border-accent pl-6 py-1">
              <div className="eyebrow">{p.role}</div>
              <blockquote className="mt-3 font-serif text-[22px] leading-[1.35] tracking-tight text-ink text-balance">
                “{p.quote}”
              </blockquote>
              <p className="mt-4 font-mono text-[12.5px] text-muted leading-relaxed">
                {p.workflow}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
