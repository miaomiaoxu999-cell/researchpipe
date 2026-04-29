import Link from "next/link";
import { ENDPOINTS_BY_LINE, DATA_GROUPS } from "@/lib/endpoints";

export default function Endpoints() {
  return (
    <>
      <h1 className="font-serif text-[40px] tracking-tight text-ink">Endpoints</h1>
      <p className="text-[15px] text-muted mt-2 mb-10">50+ endpoints across 4 product lines + Account.</p>

      <h2 id="search">Search · 6 endpoints</h2>
      <EndpointTable list={ENDPOINTS_BY_LINE.Search} />

      <h2 id="research">Research · 3 endpoints (async)</h2>
      <p>异步多步 LLM 编排 + output_schema 自定义 + citations 默认带。</p>
      <EndpointTable list={ENDPOINTS_BY_LINE.Research} />

      <h2 id="data">Data · 38 endpoints</h2>
      <p>毫秒级查询；按实体分组：companies / investors / deals / industries / valuations / filings / news / tasks。</p>
      {DATA_GROUPS.map((g) => {
        const list = ENDPOINTS_BY_LINE.Data.filter((e) => e.group === g);
        if (list.length === 0) return null;
        return (
          <section key={g} className="my-6">
            <h3>{g}</h3>
            <EndpointTable list={list} />
          </section>
        );
      })}

      <h2 id="watch">Watch · 2 endpoints</h2>
      <EndpointTable list={ENDPOINTS_BY_LINE.Watch} />

      <h2 id="account">Account · 3 endpoints</h2>
      <EndpointTable list={ENDPOINTS_BY_LINE.Account} />
    </>
  );
}

function EndpointTable({
  list,
}: {
  list: { id: string; code: string; name: string; path: string; credits: number; creditsRange?: string; phase: string; star?: boolean; desc: string }[];
}) {
  return (
    <div className="border border-line my-3 overflow-x-auto">
      <table className="w-full text-[13.5px]">
        <thead className="bg-cream">
          <tr>
            <th className="text-left py-2 px-3 font-semibold w-[20px]"></th>
            <th className="text-left py-2 px-3 font-semibold">Endpoint</th>
            <th className="text-left py-2 px-3 font-semibold">Path</th>
            <th className="text-left py-2 px-3 font-semibold">Credits</th>
            <th className="text-left py-2 px-3 font-semibold">Phase</th>
          </tr>
        </thead>
        <tbody>
          {list.map((e) => (
            <tr key={e.id} className="border-t border-line hover:bg-cream/50">
              <td className="px-3 py-2 text-accent">{e.star ? "★" : ""}</td>
              <td className="px-3 py-2 font-medium">
                <Link href={`/playground?endpoint=${e.id}`} className="hover:text-accent">
                  {e.name}
                </Link>
                <div className="text-muted text-[12px] mt-0.5">{e.desc}</div>
              </td>
              <td className="px-3 py-2 font-mono text-[12px]">{e.path}</td>
              <td className="px-3 py-2 font-mono text-[12px]">{e.creditsRange ?? e.credits}</td>
              <td className="px-3 py-2 text-muted text-[12px]">{e.phase}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
