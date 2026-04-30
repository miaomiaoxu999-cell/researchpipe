import Link from "next/link";

export default function HomePage() {
  return (
    <>
      {/* Hero with landscape art */}
      <section className="hero-landscape">
        <div className="container-page pt-20 pb-32 sm:pt-28 sm:pb-44">
          <div className="text-center max-w-3xl mx-auto">
            <p className="text-[13px] tracking-wide text-muted mb-6">
              <span className="text-ink/50">/</span>
              <span className="text-ink/80">投研派</span>
              <span className="text-ink/40 mx-2">·</span>
              给投资人的 AI 研究助手
            </p>
            <h1 className="text-[44px] sm:text-[64px] font-medium tracking-hero leading-[1.05] text-balance text-ink-900">
              问一句话，
              <br />
              得到一份带引用的研究报告。
            </h1>
            <p className="mt-7 text-[17px] sm:text-[18px] leading-relaxed text-ink/70 max-w-xl mx-auto text-balance">
              基于 14,000 多篇 2026 年券商研报与一级市场数据，AI
              自动综合答案、标注每个观点的出处、可一键导出。不需要写代码。
            </p>
            <div className="mt-10 flex items-center justify-center gap-4 flex-wrap">
              <Link href="/agent" className="btn-primary">
                开始研究
                <span aria-hidden>→</span>
              </Link>
              <Link href="/about" className="btn-ghost">
                了解更多
              </Link>
            </div>
            <p className="mt-7 text-[13px] text-muted">
              注册即享 1,000 个免费 credits · 无需信用卡
            </p>
          </div>
        </div>
      </section>

      {/* Social proof / audience */}
      <section className="border-t hairline bg-cream">
        <div className="container-page py-16 text-center">
          <p className="eyebrow mb-6">为这些人而生</p>
          <div className="flex flex-wrap justify-center gap-3">
            {[
              "VC / PE 投资经理",
              "二级市场分析师",
              "一级市场尽调岗",
              "创业者做市场调研",
              "FA / 投行 BD",
              "公司战投部",
            ].map((t) => (
              <span key={t} className="chip">
                {t}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Three feature highlights */}
      <section className="bg-cream-200 border-t hairline">
        <div className="container-page py-24">
          <h2 className="text-[32px] sm:text-[40px] font-medium tracking-hero leading-tight text-center text-balance max-w-2xl mx-auto">
            为分析师设计，不是为程序员。
          </h2>
          <div className="mt-16 grid md:grid-cols-3 gap-8">
            {[
              {
                eyebrow: "01",
                title: "中文投研问答",
                body: "用最自然的中文问问题。Agent 会自己拆问题、查资料、综合答案，像一个高效的实习分析师。",
              },
              {
                eyebrow: "02",
                title: "每个观点都带出处",
                body: "答案中所有数字、引用、判断都标注来源——具体到哪份研报、哪一页、哪位分析师。可点击查看原文。",
              },
              {
                eyebrow: "03",
                title: "一键导出成报告",
                body: "输出可直接复制粘贴到内部 memo、PDF、Word、Notion——随时给老板汇报，省去自己整合的工夫。",
              },
            ].map((f) => (
              <div key={f.title} className="card-cream p-7">
                <p className="eyebrow">{f.eyebrow}</p>
                <h3 className="mt-4 text-[20px] font-semibold leading-snug text-ink-900">
                  {f.title}
                </h3>
                <p className="mt-3 text-[15px] leading-relaxed text-ink/70">
                  {f.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Sample output preview — "投研派 in action" */}
      <section className="bg-cream border-t hairline">
        <div className="container-page py-24">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <p className="eyebrow mb-4">投研派实战</p>
              <h2 className="text-[32px] sm:text-[40px] font-medium tracking-hero leading-tight text-balance">
                像让一个分析师帮你写 memo 一样。
              </h2>
              <p className="mt-6 text-[16px] leading-relaxed text-ink/70">
                问一个具体问题，比如"中信建投最近的半导体研报观点"。
                几十秒后你会拿到一份结构化答案，每条结论都有可点击的来源。
                不满意可以追问，可以让它换券商，可以让它聚焦某个细分。
              </p>
              <div className="mt-8 flex flex-wrap gap-2">
                <span className="chip">行业研究</span>
                <span className="chip">公司尽调</span>
                <span className="chip">估值对标</span>
                <span className="chip">政策匹配</span>
                <span className="chip">赛道扫描</span>
              </div>
              <Link
                href="/agent"
                className="mt-8 inline-flex items-center text-[14px] font-medium text-ink/80 hover:text-ink transition-colors gap-1"
              >
                去试一下 <span aria-hidden>→</span>
              </Link>
            </div>

            {/* Mock answer preview */}
            <div className="card-cream p-6 shadow-card">
              <div className="flex items-center justify-between mb-5">
                <p className="text-[12px] text-muted">
                  <span className="text-ink/50">/</span>
                  研究 ·{" "}
                  <span className="text-ink/80">中信建投半导体观点</span>
                </p>
                <span className="text-[11px] tracking-wide text-muted">
                  53.7s · 5 引用
                </span>
              </div>
              <div className="text-[14.5px] leading-relaxed text-ink/85 space-y-3">
                <p className="font-medium text-ink-900">
                  ## 模拟 IC：行业拐点确认
                </p>
                <p>
                  根据中信建投 2026-03-01 报告
                  <sup className="text-accent-link mx-0.5">[1]</sup>，
                  海外模拟 IC 龙头业绩验证拐点：TI / ADI / MPS 已恢复同比正增长，
                  2026 Q1 指引环比增长——近 15 年来首次。
                </p>
                <p>
                  库存去化基本完成，Book-to-Bill 持续大于 1
                  <sup className="text-accent-link mx-0.5">[3]</sup>。
                </p>
                <p>
                  AI 数据中心是核心引擎，MPS 数据中心敞口达 53.3%，
                  连续 9 个季度环比增长
                  <sup className="text-accent-link mx-0.5">[6]</sup>。
                </p>
              </div>
              <div className="mt-5 pt-4 border-t hairline">
                <p className="text-[11px] tracking-wide text-muted mb-2">
                  来源
                </p>
                <p className="text-[12.5px] text-ink/70 leading-relaxed">
                  [1] 中信建投 ·{" "}
                  <span className="text-ink-900">
                    海外模拟 IC 龙头业绩验证拐点
                  </span>
                  <span className="text-muted"> · 21 页 · 刘双锋</span>
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing teaser */}
      <section className="bg-cream-200 border-t hairline">
        <div className="container-page py-24">
          <div className="text-center max-w-2xl mx-auto">
            <p className="eyebrow mb-4">/定价</p>
            <h2 className="text-[32px] sm:text-[40px] font-medium tracking-hero leading-tight text-balance">
              从免费开始，按需付费。
            </h2>
            <p className="mt-5 text-[16px] leading-relaxed text-ink/70">
              注册即获 1,000 credits（约 200 次研究）。无需信用卡。
            </p>
            <div className="mt-8 flex items-center justify-center gap-4">
              <Link href="/pricing" className="btn-ghost">
                查看完整定价 →
              </Link>
              <Link href="/agent" className="btn-primary">
                开始免费研究
                <span aria-hidden>→</span>
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
