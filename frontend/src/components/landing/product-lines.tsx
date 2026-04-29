import Link from "next/link";

const LINES = [
  {
    no: "01",
    name: "Search",
    tagline: "同步原料供应",
    desc: "同步秒级返回 —— 让 agent 自己合成。Web / News / 研报 / 政策 / 上市文件，5 种内容类型一个端点搞定。",
    credits: "1–5 credits",
    endpoints: "6 端点",
    samplePath: "POST /v1/search",
    color: "text-ink",
  },
  {
    no: "02",
    name: "Research",
    tagline: "异步成品交付",
    desc: "多步 LLM 编排 + output_schema 完全自定义 + citations 默认带。30 分钟跑完一个赛道全景报告。",
    credits: "30–100 credits",
    endpoints: "3 端点",
    samplePath: "POST /v1/research/sector",
    color: "text-accent",
  },
  {
    no: "03",
    name: "Data",
    tagline: "投研结构化数据",
    desc: "投研垂类真正的护城河。一级 deals · 上市文件 · 估值 · 投资机构 · 产业链 · 政策，毫秒级查询。",
    credits: "0.5–3 credits",
    endpoints: "38 端点",
    samplePath: "GET /v1/companies/{id}/deals",
    color: "text-ink",
  },
  {
    no: "04",
    name: "Watch",
    tagline: "订阅 / cron friendly",
    desc: "为公众号 KOL / 日报机器人而生。设一个监控条件，cron 触发 digest，结果回传 webhook 或邮件。",
    credits: "10 credits / digest",
    endpoints: "2 端点",
    samplePath: "POST /v1/watch/create",
    color: "text-ink",
  },
];

export function ProductLines() {
  return (
    <section id="products" className="py-24 border-b border-line bg-cream">
      <div className="container-page">
        <div className="max-w-3xl">
          <p className="eyebrow">The four product lines</p>
          <h2 className="mt-4 font-serif text-[44px] md:text-[52px] leading-[1.05] tracking-tightest text-ink text-balance">
            原料 + 成品 + 结构化数据 + 订阅，<br />
            投研垂类的<span className="underline-accent">完整基础设施</span>。
          </h2>
          <p className="mt-6 max-w-2xl text-[16px] leading-relaxed text-ink/70">
            Search 与 Research 分别给 agent 提供原料和成品；Data 与 Watch
            是中国一级市场分析师每天都需要、但市场上没人系统化做的能力。
          </p>
        </div>

        <div className="mt-16 grid md:grid-cols-2 gap-px bg-line border border-line">
          {LINES.map((l) => (
            <article
              key={l.name}
              className="bg-white p-10 md:p-12 flex flex-col"
            >
              <div className="flex items-baseline gap-4">
                <span className="font-mono text-[13px] tracking-widest text-muted">
                  {l.no}
                </span>
                <span className={`font-serif text-[36px] font-semibold tracking-tight ${l.color}`}>
                  {l.name}
                </span>
              </div>
              <p className="mt-2 text-[16px] font-medium text-ink/85">{l.tagline}</p>
              <p className="mt-5 text-[15px] leading-[1.6] text-ink/70 flex-1">
                {l.desc}
              </p>

              <div className="mt-8 flex items-center justify-between border-t border-line pt-5">
                <div>
                  <div className="text-[12px] uppercase tracking-widest text-muted">
                    {l.endpoints}
                  </div>
                  <div className="mt-1 font-mono text-[13.5px] text-ink">
                    {l.samplePath}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-[12px] uppercase tracking-widest text-muted">
                    Cost
                  </div>
                  <div className="mt-1 text-[14px] font-medium text-ink">
                    {l.credits}
                  </div>
                </div>
              </div>

              <Link
                href={`/playground?line=${l.name.toLowerCase()}`}
                className="mt-6 text-[13.5px] font-medium text-accent hover:text-accent-hover transition-colors"
              >
                Try {l.name} in playground →
              </Link>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
