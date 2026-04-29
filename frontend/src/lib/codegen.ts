import type { Endpoint } from "./endpoints";

function pathTemplate(ep: Endpoint, values: Record<string, unknown>): string {
  // Replace {param} placeholders in path
  return ep.path.replace(/{(\w+)}/g, (_, name) => {
    const v = values[name];
    return v == null || v === "" ? `{${name}}` : String(v);
  });
}

function bodyValues(ep: Endpoint, values: Record<string, unknown>): Record<string, unknown> {
  // Filter out empty + path-param values
  const pathParams = Array.from(ep.path.matchAll(/{(\w+)}/g)).map((m) => m[1]);
  const out: Record<string, unknown> = {};
  for (const p of ep.params) {
    if (pathParams.includes(p.name)) continue;
    const v = values[p.name];
    if (v == null || v === "" || (Array.isArray(v) && v.length === 0)) continue;
    out[p.name] = v;
  }
  return out;
}

function methodAndUrl(ep: Endpoint, values: Record<string, unknown>): { method: string; urlPath: string } {
  const tokens = ep.path.split(" ");
  const method = tokens[0];
  const urlPath = tokens.slice(1).join(" ");
  const filled = urlPath.replace(/{(\w+)}/g, (_, name) => {
    const v = values[name];
    return v == null || v === "" ? `{${name}}` : encodeURIComponent(String(v));
  });
  return { method, urlPath: filled };
}

export function genPython(ep: Endpoint, values: Record<string, unknown>): string {
  const { method, urlPath } = methodAndUrl(ep, values);
  const body = bodyValues(ep, values);
  const hasBody = Object.keys(body).length > 0;
  const fnName = ep.id.replace(/-/g, "_");

  if (method === "GET") {
    return `from researchpipe import ResearchPipe

rp = ResearchPipe(api_key="rp-...")

result = rp.get("${urlPath}"${hasBody ? `, params=${pythonDict(body)}` : ""})
print(result)
`;
  }
  return `from researchpipe import ResearchPipe

rp = ResearchPipe(api_key="rp-...")

result = rp.${fnName}(
${Object.entries(body)
  .map(([k, v]) => `    ${k}=${pythonValue(v)},`)
  .join("\n")}
)
print(result)
`;
}

export function genCurl(ep: Endpoint, values: Record<string, unknown>): string {
  const { method, urlPath } = methodAndUrl(ep, values);
  const body = bodyValues(ep, values);
  const hasBody = Object.keys(body).length > 0;
  const url = `https://rp.zgen.xin${urlPath}`;
  const lines = [
    `curl -X ${method} "${url}" \\`,
    `  -H "Authorization: Bearer $RESEARCHPIPE_KEY" \\`,
    `  -H "Idempotency-Key: $(uuidgen)"${hasBody ? " \\" : ""}`,
  ];
  if (hasBody) {
    lines.push(`  -H "Content-Type: application/json" \\`);
    lines.push(
      `  -d '${JSON.stringify(body, null, 2).split("\n").join("\n     ")}'`,
    );
  }
  return lines.join("\n");
}

export function genNode(ep: Endpoint, values: Record<string, unknown>): string {
  const { method, urlPath } = methodAndUrl(ep, values);
  const body = bodyValues(ep, values);
  const fnName = ep.id.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
  const isPost = method === "POST";

  return `import { ResearchPipe } from "@researchpipe/sdk";

const rp = new ResearchPipe({ apiKey: process.env.RESEARCHPIPE_KEY });

const result = await rp.${fnName}(${
    isPost
      ? JSON.stringify(body, null, 2)
      : `"${urlPath}"${Object.keys(body).length ? `, ${JSON.stringify(body, null, 2)}` : ""}`
  });
console.log(result);
`;
}

export function genMcp(ep: Endpoint, values: Record<string, unknown>): string {
  const body = bodyValues(ep, values);
  return `// Claude Desktop config (~/Library/Application Support/Claude/claude_desktop_config.json)
{
  "mcpServers": {
    "researchpipe": {
      "command": "npx",
      "args": ["-y", "@researchpipe/mcp-server"],
      "env": { "RESEARCHPIPE_KEY": "rp-..." }
    }
  }
}

// Then ask Claude:
"用 @researchpipe 的 ${ep.name} 帮我查 ${
    Object.entries(body).slice(0, 2).map(([k, v]) => `${k}=${valuePreview(v)}`).join(", ") || "..."
  }"

// Internally Claude calls the MCP tool which wraps:
${ep.path}
${JSON.stringify(body, null, 2)}
`;
}

function pythonValue(v: unknown): string {
  if (typeof v === "string") return JSON.stringify(v);
  if (typeof v === "boolean") return v ? "True" : "False";
  if (Array.isArray(v)) return `[${v.map((x) => pythonValue(x)).join(", ")}]`;
  if (v === null || v === undefined) return "None";
  if (typeof v === "object") return pythonDict(v as Record<string, unknown>);
  return String(v);
}
function pythonDict(o: Record<string, unknown>): string {
  return `{${Object.entries(o)
    .map(([k, v]) => `${JSON.stringify(k)}: ${pythonValue(v)}`)
    .join(", ")}}`;
}
function valuePreview(v: unknown): string {
  if (Array.isArray(v)) return `[${v.slice(0, 2).join(",")}${v.length > 2 ? "…" : ""}]`;
  return String(v).slice(0, 30);
}
