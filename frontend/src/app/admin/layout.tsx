import Link from "next/link";

export const metadata = {
  title: "Admin — ResearchPipe",
  description: "Internal control panel",
};

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-[calc(100vh-72px)] bg-slate-50">
      <div className="border-b border-slate-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 lg:px-8 py-3 flex items-center justify-between text-sm">
          <div className="flex items-center gap-6">
            <Link href="/admin" className="font-semibold text-slate-900">
              RP Admin
            </Link>
            <nav className="flex items-center gap-4 text-slate-600">
              <Link href="/admin" className="hover:text-slate-900">Overview</Link>
              <Link href="/admin/accounts" className="hover:text-slate-900">Accounts</Link>
              <Link href="/admin/usage" className="hover:text-slate-900">Usage</Link>
              <Link href="/admin/corpus" className="hover:text-slate-900">Corpus</Link>
              <Link href="/admin/jobs" className="hover:text-slate-900">Jobs</Link>
            </nav>
          </div>
          <div className="text-xs text-slate-400">Internal · do not share URL</div>
        </div>
      </div>
      <main className="max-w-7xl mx-auto px-4 lg:px-8 py-6">{children}</main>
    </div>
  );
}
