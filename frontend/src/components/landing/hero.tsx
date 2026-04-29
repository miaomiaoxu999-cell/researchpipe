import Link from "next/link";

const STATS = [
  { value: "8", label: "类一手数据源" },
  { value: "67K", label: "上市公司文件" },
  { value: "26K", label: "一级市场 deals" },
  { value: "50+", label: "结构化端点" },
];

export function Hero() {
  return (
    <section className="relative pt-20 pb-24 border-b border-line">
      <div className="container-page">
        <div className="max-w-[860px]">
          <p className="eyebrow">Investment research API · SDK · MCP</p>

          <h1 className="mt-6 font-serif text-[64px] md:text-[84px] leading-[0.96] tracking-tightest text-ink text-balance">
            投研派<span className="text-muted/40 mx-3 font-sans font-light text-[44px] md:text-[56px] align-middle">/</span>
            <span className="text-ink">ResearchPipe</span>
          </h1>

          <p className="mt-8 max-w-[640px] text-[19px] md:text-[20px] leading-[1.55] text-ink/80 text-pretty">
            投研垂类的 API · SDK · MCP，为手搓 Agent 大军而生。
            从一级市场 deal 到上市公司招股书，从券商研报到政策文件 ——
            一套接口给你的 agent，让它像分析师一样工作。
          </p>

          <div className="mt-10 flex flex-wrap items-center gap-4">
            <Link
              href="/agent"
              className="inline-flex h-12 items-center px-6 bg-ink text-white text-[15px] font-medium tracking-wide hover:bg-navy-700 transition-colors"
            >
              Try Agent in browser
              <span aria-hidden className="ml-2">→</span>
            </Link>
            <Link
              href="/#get-key"
              className="inline-flex h-12 items-center px-6 border border-ink text-ink text-[15px] font-medium tracking-wide hover:bg-ink hover:text-white transition-colors"
            >
              Get a free API key
            </Link>
            <a
              href="/downloads/researchpipe-agent-ui-latest.zip"
              className="inline-flex h-12 items-center px-6 border border-line text-ink text-[15px] font-medium tracking-wide hover:border-ink transition-colors group"
              download
            >
              <span aria-hidden className="mr-2">📦</span>
              Download Agent UI
              <span className="ml-2 text-[12px] text-muted group-hover:text-ink/60">v0.1.1 · MIT</span>
            </a>
          </div>

          <p className="mt-6 text-[13px] text-muted tracking-wide">
            Free tier · 100 credits / month · No credit card required ·
            <span className="ml-1">Agent UI ships open-source — bring your own key.</span>
          </p>
        </div>

        {/* Stats strip */}
        <div className="mt-24 grid grid-cols-2 md:grid-cols-4 border-t border-line">
          {STATS.map((s, i) => (
            <div
              key={s.label}
              className={`py-8 ${
                i !== 0 ? "md:border-l border-line md:pl-10" : "md:pl-0"
              }`}
            >
              <div className="font-serif text-[48px] md:text-[56px] leading-none tracking-tightest text-ink">
                {s.value}
              </div>
              <div className="mt-3 text-[13px] tracking-wide text-muted uppercase font-medium">
                {s.label}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
