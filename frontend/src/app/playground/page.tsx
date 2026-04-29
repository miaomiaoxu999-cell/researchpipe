"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { CreditsBar } from "@/components/playground/credits-bar";
import { EndpointNav } from "@/components/playground/endpoint-nav";
import { ParamForm } from "@/components/playground/param-form";
import { ResponseTabs } from "@/components/playground/response-tabs";
import { ENDPOINTS, findEndpoint } from "@/lib/endpoints";
import { getMock, SAMPLE_ERRORS } from "@/lib/mocks";

function PlaygroundInner() {
  const router = useRouter();
  const sp = useSearchParams();

  const initialId = useMemo(() => {
    const fromQuery = sp.get("endpoint");
    if (fromQuery && findEndpoint(fromQuery)) return fromQuery;
    const line = sp.get("line");
    if (line) {
      const first = ENDPOINTS.find((e) => e.line.toLowerCase() === line.toLowerCase());
      if (first) return first.id;
    }
    return "research-sector";
  }, [sp]);

  const [selectedId, setSelectedId] = useState<string>(initialId);
  const endpoint = findEndpoint(selectedId) ?? ENDPOINTS[0];

  const defaults = useMemo(() => {
    const out: Record<string, unknown> = {};
    for (const p of endpoint.params) {
      if (p.default !== undefined) out[p.name] = p.default;
    }
    // URL prefill
    const prefillRaw = sp.get("prefill");
    if (prefillRaw) {
      try {
        const obj = JSON.parse(prefillRaw);
        Object.assign(out, obj);
      } catch {}
    }
    return out;
  }, [endpoint, sp]);

  const [values, setValues] = useState<Record<string, unknown>>(defaults);

  useEffect(() => {
    setValues(defaults);
    setResponse(null);
    setIsError(false);
  }, [defaults]);

  const [response, setResponse] = useState<unknown | null>(null);
  const [isError, setIsError] = useState(false);
  const [running, setRunning] = useState(false);

  const handleSelect = (id: string) => {
    setSelectedId(id);
    const next = new URLSearchParams(sp.toString());
    next.set("endpoint", id);
    next.delete("prefill");
    next.delete("line");
    router.replace(`/playground?${next.toString()}`, { scroll: false });
  };

  const [useReal, setUseReal] = useState<boolean>(false);

  const handleRun = async () => {
    setRunning(true);
    setResponse(null);
    setIsError(false);

    if (!useReal) {
      // Mock mode: keep existing behavior
      setTimeout(() => {
        const showError =
          endpoint.id === "search" && (values.query === "rate-limit-demo" as unknown);
        if (showError) {
          setResponse(SAMPLE_ERRORS.rate_limit);
          setIsError(true);
        } else {
          setResponse(getMock(endpoint.mockKey, endpoint.id));
        }
        setRunning(false);
      }, 480);
      return;
    }

    // Real mode: call live backend on localhost:3725
    try {
      const [method, pathTemplate] = endpoint.path.split(" ");
      const filledPath = pathTemplate.replace(/{(\w+)}/g, (_, name) => {
        const v = values[name as keyof typeof values];
        return v != null && v !== "" ? encodeURIComponent(String(v)) : `{${name}}`;
      });
      const url = `${process.env.NEXT_PUBLIC_RP_BACKEND_URL || "http://localhost:3725"}${filledPath}`;
      const isPost = method === "POST";

      // Body excludes path params
      const pathParamNames = Array.from(pathTemplate.matchAll(/{(\w+)}/g)).map((m) => m[1]);
      const body: Record<string, unknown> = {};
      const params: Record<string, string> = {};
      for (const p of endpoint.params) {
        if (pathParamNames.includes(p.name)) continue;
        const v = values[p.name];
        if (v == null || v === "" || (Array.isArray(v) && v.length === 0)) continue;
        if (isPost) body[p.name] = v as unknown;
        else params[p.name] = String(v);
      }

      const headers: Record<string, string> = {
        "Authorization": `Bearer ${process.env.NEXT_PUBLIC_RP_DEV_KEY || "rp-demo-public"}`,
        "Content-Type": "application/json",
      };
      const finalUrl = isPost ? url : `${url}?${new URLSearchParams(params).toString()}`;
      const resp = await fetch(finalUrl, {
        method,
        headers,
        body: isPost ? JSON.stringify(body) : undefined,
      });
      const data = await resp.json();
      setResponse(data);
      setIsError(!resp.ok);
    } catch (e) {
      setResponse({
        error: {
          code: "network_error",
          message: String(e),
          hint_for_agent: "Make sure backend is running on http://localhost:3725 (uv run uvicorn researchpipe_api.main:app --port 3725).",
        },
      });
      setIsError(true);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-72px)]">
      <CreditsBar used={9847} total={80000} />
      <div className="flex items-center justify-end gap-3 px-6 py-2 border-b border-line bg-cream/40 text-[12.5px]">
        <span className="text-muted">Backend</span>
        <button
          onClick={() => setUseReal(false)}
          className={`px-3 py-1 ${!useReal ? "bg-ink text-white" : "bg-white text-ink/70 border border-line"}`}
        >
          Mock
        </button>
        <button
          onClick={() => setUseReal(true)}
          className={`px-3 py-1 ${useReal ? "bg-accent text-white" : "bg-white text-ink/70 border border-line"}`}
        >
          Real (localhost:3725)
        </button>
        {useReal && (
          <span className="text-muted ml-3">
            ⚠️ 真后端：search/extract/extract-research 走 Tavily + V4，companies/deals/investors/valuations 走 qmp_data
          </span>
        )}
      </div>
      <div className="flex-1 flex overflow-hidden">
        <EndpointNav selectedId={selectedId} onSelect={handleSelect} />
        <ParamForm
          endpoint={endpoint}
          values={values}
          onChange={setValues}
          onRun={handleRun}
          running={running}
        />
        <ResponseTabs
          endpoint={endpoint}
          values={values}
          response={response}
          isError={isError}
        />
      </div>
    </div>
  );
}

export default function PlaygroundPage() {
  return (
    <Suspense
      fallback={
        <div className="container-page py-20 text-muted">Loading playground…</div>
      }
    >
      <PlaygroundInner />
    </Suspense>
  );
}
