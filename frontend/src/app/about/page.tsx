import Link from "next/link";

export const metadata = {
  title: "关于 — 投研派",
  description: "投研派 ResearchPipe 是给投资人的 AI 研究助手。",
};

export default function AboutPage() {
  return (
    <>
      <section className="hero-landscape">
        <div className="container-narrow pt-16 sm:pt-24 pb-20 text-center">
          <p className="text-[13px] tracking-wide text-muted mb-5">
            <span className="text-ink/50">/</span>
            <span className="text-ink/85">关于</span>
          </p>
          <h1 className="text-[40px] sm:text-[52px] font-medium tracking-hero leading-tight text-balance">
            为不会编程的投资人而生。
          </h1>
          <p className="mt-7 text-[16.5px] text-ink/70 leading-relaxed max-w-xl mx-auto">
            投研派把"读 50 份研报、查 100 个数据点、整理一份 memo"
            的两小时活，压缩成"问一句话、30 秒拿到带引用的报告"。
          </p>
        </div>
      </section>

      <section className="bg-cream py-20">
        <div className="container-narrow">
          <h2 className="text-[28px] font-medium tracking-hero mb-6">
            我们相信什么
          </h2>
          <div className="space-y-5 text-[15.5px] text-ink/75 leading-relaxed">
            <p>
              <strong className="text-ink-900">研究是分析师的核心能力。</strong>
              AI 不应该取代你的判断，但应该把你从重复劳动里解放出来。
              投研派只做"前 80% 的资料整合"——那个最磨人、最消耗注意力的部分。
              真正的判断、真正的 thesis，留给你自己。
            </p>
            <p>
              <strong className="text-ink-900">引用比答案更重要。</strong>
              一个不带出处的 AI 答案只是噪音。
              投研派每个观点都标注来源——具体到哪份研报、哪一页、哪位分析师，
              这样你才敢把它写进自己的 memo 里。
            </p>
            <p>
              <strong className="text-ink-900">投资人不该被技术门槛挡住。</strong>
              我们不卖 API、不卖 SDK、不强迫你学 prompt engineering。
              你只需要会问问题——剩下的事我们替你办。
            </p>
          </div>
        </div>
      </section>

      <section id="contact" className="bg-cream-200 py-20 border-t hairline">
        <div className="container-narrow text-center">
          <p className="eyebrow mb-3">/联系</p>
          <h2 className="text-[28px] font-medium tracking-hero mb-5">
            想聊聊？
          </h2>
          <p className="text-[15.5px] text-ink/70 leading-relaxed mb-8">
            产品意见、合作、定制需求、企业版咨询——都可以。
          </p>
          <div className="flex flex-col sm:flex-row gap-3 items-center justify-center">
            <a
              href="mailto:hi@rp.zgen.xin"
              className="btn-primary"
            >
              发邮件
              <span aria-hidden>→</span>
            </a>
            <a href="#wechat" className="btn-ghost">
              加微信
            </a>
          </div>
          <p className="mt-8 text-[13px] text-muted">
            邮箱 hi@rp.zgen.xin · 工作日 24 小时内回复
          </p>
        </div>
      </section>

      {/* terms / privacy anchors so footer links don't 404 */}
      <section id="terms" className="bg-cream py-20 border-t hairline">
        <div className="container-narrow">
          <h2 className="text-[24px] font-medium tracking-hero mb-4">
            服务条款（摘要）
          </h2>
          <p className="text-[14px] text-ink/70 leading-relaxed">
            投研派提供的所有研究内容仅供参考，不构成投资建议。我们尽力保证数据准确，
            但 AI 可能出错——重要决策请回到原始来源核实。完整条款详见{" "}
            <Link href="/about" className="text-accent-link hover:underline">
              联系我们 →
            </Link>{" "}
            索取。
          </p>
        </div>
      </section>
      <section id="privacy" className="bg-cream-200 py-20 border-t hairline">
        <div className="container-narrow">
          <h2 className="text-[24px] font-medium tracking-hero mb-4">
            隐私政策（摘要）
          </h2>
          <p className="text-[14px] text-ink/70 leading-relaxed">
            我们存储你的问题与答案历史以便回看。可在设置里关闭。
            我们绝不用客户问题训练模型。完整政策请联系索取。
          </p>
        </div>
      </section>
    </>
  );
}
