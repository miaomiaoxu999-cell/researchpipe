import { AgentChat } from "@/components/AgentChat";

export default function Home() {
  return (
    <main>
      {/* Header */}
      <header className="border-b border-slate-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded bg-slate-900 flex items-center justify-center text-white font-bold text-sm">
              RP
            </div>
            <div>
              <div className="text-sm font-semibold tracking-tight text-slate-900">
                ResearchPipe <span className="text-slate-400 font-normal">· Agent UI</span>
              </div>
              <div className="text-xs text-slate-500">Open-source · MIT · Bring your own API key</div>
            </div>
          </div>
          <div className="text-xs text-slate-500 hidden md:block">
            Backend: <code className="font-mono">{process.env.NEXT_PUBLIC_RP_BACKEND_URL || "http://localhost:3725"}</code>
          </div>
        </div>
      </header>

      <AgentChat />

      <footer className="mt-12 border-t border-slate-200 py-6 text-center text-xs text-slate-500">
        <a href="https://rp.zgen.xin" target="_blank" rel="noreferrer" className="hover:text-slate-700">
          Powered by ResearchPipe
        </a>
        {" · "}
        <a href="https://rp.zgen.xin/docs" target="_blank" rel="noreferrer" className="hover:text-slate-700">
          API Docs
        </a>
        {" · "}
        <span>v0.1.0</span>
      </footer>
    </main>
  );
}
