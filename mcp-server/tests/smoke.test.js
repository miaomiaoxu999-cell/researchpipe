// Node native test runner — basic stdio smoke test for MCP server
import { test } from "node:test";
import { spawn } from "node:child_process";
import { strict as assert } from "node:assert";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SERVER = resolve(__dirname, "../dist/index.js");

function runServer(env = {}) {
  return spawn("node", [SERVER], {
    stdio: ["pipe", "pipe", "pipe"],
    env: { ...process.env, ...env },
  });
}

function sendJsonRpc(proc, request) {
  proc.stdin.write(JSON.stringify(request) + "\n");
}

async function readOneResponse(proc, timeoutMs = 5000) {
  return new Promise((resolve, reject) => {
    let buf = "";
    const onData = (chunk) => {
      buf += chunk.toString();
      const newline = buf.indexOf("\n");
      if (newline >= 0) {
        const line = buf.slice(0, newline);
        proc.stdout.off("data", onData);
        try {
          resolve(JSON.parse(line));
        } catch (e) {
          reject(e);
        }
      }
    };
    proc.stdout.on("data", onData);
    setTimeout(() => {
      proc.stdout.off("data", onData);
      reject(new Error(`timeout after ${timeoutMs}ms`));
    }, timeoutMs);
  });
}

test("server exits with hint when no API key is set", async () => {
  const proc = runServer({ RESEARCHPIPE_KEY: "" });
  const code = await new Promise((resolve) => proc.on("exit", resolve));
  assert.equal(code, 1);
});

test("initialize + tools/list returns 8 tools", async () => {
  const proc = runServer({ RESEARCHPIPE_KEY: "rp-test" });
  try {
    sendJsonRpc(proc, {
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: {
        protocolVersion: "2024-11-05",
        capabilities: {},
        clientInfo: { name: "test", version: "0" },
      },
    });
    const initResp = await readOneResponse(proc);
    assert.equal(initResp.result.serverInfo.name, "researchpipe");

    sendJsonRpc(proc, { jsonrpc: "2.0", id: 2, method: "tools/list", params: {} });
    const toolsResp = await readOneResponse(proc);
    assert.equal(toolsResp.result.tools.length, 8);
    const names = toolsResp.result.tools.map((t) => t.name).sort();
    assert.ok(names.includes("researchpipe_search"));
    assert.ok(names.includes("researchpipe_extract_research"));
    assert.ok(names.includes("researchpipe_research_sector"));
    assert.ok(names.includes("researchpipe_watch"));
  } finally {
    proc.kill();
  }
});

test("each tool has English description with Chinese example", async () => {
  const proc = runServer({ RESEARCHPIPE_KEY: "rp-test" });
  try {
    sendJsonRpc(proc, {
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: { protocolVersion: "2024-11-05", capabilities: {}, clientInfo: { name: "t", version: "0" } },
    });
    await readOneResponse(proc);
    sendJsonRpc(proc, { jsonrpc: "2.0", id: 2, method: "tools/list", params: {} });
    const resp = await readOneResponse(proc);
    for (const tool of resp.result.tools) {
      assert.ok(tool.description.length > 50, `${tool.name}: description too short`);
      assert.ok(/例：/.test(tool.description), `${tool.name}: missing 例：example`);
      assert.ok(tool.inputSchema, `${tool.name}: missing inputSchema`);
    }
  } finally {
    proc.kill();
  }
});
