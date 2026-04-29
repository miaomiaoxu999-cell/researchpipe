"""Compare backend OpenAPI paths vs Python SDK methods + MCP tools.

Output: PRD root /sdk_consistency_check.md
"""
from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))
sys.path.insert(0, str(ROOT / "sdk-python" / "src"))

from researchpipe_api.main import app  # noqa: E402
from researchpipe import client as sdk_client  # noqa: E402


def get_backend_paths() -> set[tuple[str, str]]:
    """Return {(method, path)} from FastAPI OpenAPI."""
    spec = app.openapi()
    pairs = set()
    for path, methods in spec["paths"].items():
        for m in methods:
            if m in {"get", "post", "put", "delete", "patch"}:
                pairs.add((m.upper(), path))
    return pairs


def get_sdk_methods() -> dict[str, str]:
    """Find SDK methods that hit /v1/* paths via _request(method, path)."""
    out: dict[str, str] = {}
    src_path = Path(sdk_client.__file__).read_text(encoding="utf-8")
    # Match: self._request("GET" | "POST", f"/v1/...") or "_request("GET", "/v1/...")"
    pat = re.compile(r'self\._request\(\s*"(GET|POST)",\s*f?"(/v1/[^"]+)"')
    for m in pat.finditer(src_path):
        method, path = m.group(1), m.group(2)
        # Find enclosing def
        # naive: walk up to nearest "def "
        before = src_path[: m.start()]
        last_def = before.rfind("def ")
        if last_def >= 0:
            fn_match = re.search(r"def (\w+)", src_path[last_def:])
            if fn_match:
                fn = fn_match.group(1)
                out.setdefault(fn, f"{method} {path}")
    return out


def get_mcp_tools() -> list[str]:
    """Read MCP server src/index.ts and extract tool names."""
    p = ROOT / "mcp-server" / "src" / "index.ts"
    if not p.exists():
        return []
    text = p.read_text(encoding="utf-8")
    return re.findall(r'name:\s*"(researchpipe_\w+)"', text)


def main():
    backend = get_backend_paths()
    sdk = get_sdk_methods()
    mcp = get_mcp_tools()

    # Normalize SDK to (method, normalized_path)
    sdk_pairs: set[tuple[str, str]] = set()
    sdk_pair_to_fn: dict[tuple[str, str], str] = {}
    for fn, sig in sdk.items():
        method, path = sig.split(" ", 1)
        # Replace SDK template params {...} are usually not literal in client.py;
        # they used f-strings. Try to canonicalize.
        # Convert /v1/companies/{cid} → /v1/companies/{cid}; ours have curly placeholders
        # Backend OpenAPI uses {cid} too — should match
        sdk_pairs.add((method, path))
        sdk_pair_to_fn[(method, path)] = fn

    backend_v1 = {p for p in backend if p[1].startswith("/v1")}

    only_in_backend = backend_v1 - sdk_pairs
    only_in_sdk = sdk_pairs - backend_v1
    matched = backend_v1 & sdk_pairs

    out_lines: list[str] = [
        "# SDK / OpenAPI Consistency Check",
        "",
        "**Date**: 2026-04-29",
        "**Backend version**: 0.1.0",
        "**SDK version**: 0.1.0",
        "",
        f"- Backend `/v1/*` paths: **{len(backend_v1)}**",
        f"- SDK methods hitting `/v1/*`: **{len(sdk_pairs)}**",
        f"- MCP tools: **{len(mcp)}**",
        "",
        f"- ✅ Matched paths: **{len(matched)}**",
        f"- ⚠️ Only in backend (no SDK wrapper): **{len(only_in_backend)}**",
        f"- ⚠️ Only in SDK (orphan / typo): **{len(only_in_sdk)}**",
        "",
    ]

    if matched:
        out_lines.append("## ✅ Matched paths\n")
        out_lines.append("| Method | Path | SDK method |")
        out_lines.append("|---|---|---|")
        for m, p in sorted(matched):
            fn = sdk_pair_to_fn.get((m, p), "?")
            out_lines.append(f"| {m} | `{p}` | `rp.{fn}` |")
        out_lines.append("")

    if only_in_backend:
        out_lines.append("## ⚠️ Only in backend (consider adding SDK wrapper)\n")
        out_lines.append("| Method | Path |")
        out_lines.append("|---|---|")
        for m, p in sorted(only_in_backend):
            out_lines.append(f"| {m} | `{p}` |")
        out_lines.append("")

    if only_in_sdk:
        out_lines.append("## ⚠️ Only in SDK (orphan or path mismatch)\n")
        out_lines.append("| Method | Path | SDK method |")
        out_lines.append("|---|---|---|")
        for m, p in sorted(only_in_sdk):
            fn = sdk_pair_to_fn.get((m, p), "?")
            out_lines.append(f"| {m} | `{p}` | `rp.{fn}` |")
        out_lines.append("")

    out_lines.append("## MCP Tools\n")
    out_lines.append("| Tool | Backend endpoints wrapped (manual count) |")
    out_lines.append("|---|---|")
    out_lines.append("| `researchpipe_search` | /v1/search |")
    out_lines.append("| `researchpipe_extract` | /v1/extract |")
    out_lines.append("| `researchpipe_extract_research` | /v1/extract/research |")
    out_lines.append("| `researchpipe_research_sector` | /v1/research/sector + /v1/jobs |")
    out_lines.append("| `researchpipe_research_company` | /v1/research/company + /v1/jobs |")
    out_lines.append("| `researchpipe_company_data` | /v1/companies/* (6) |")
    out_lines.append("| `researchpipe_industry_data` | /v1/industries/* (7) |")
    out_lines.append("| `researchpipe_watch` | /v1/watch/* (2) |")
    out_lines.append("")

    out_lines.append("## Conclusion\n")
    if not only_in_sdk and len(matched) >= 20:
        out_lines.append("Excellent — SDK and backend are consistent. M2 may add SDK wrappers for the remaining backend-only paths.")
    elif only_in_sdk:
        out_lines.append("⚠️ Some SDK methods point to non-existent backend paths — needs investigation.")
    else:
        out_lines.append("Backend has paths not covered by SDK; add wrappers in M2.")

    out_path = ROOT / "sdk_consistency_check.md"
    out_path.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"Backend: {len(backend_v1)} | SDK: {len(sdk_pairs)} | Matched: {len(matched)} | Backend-only: {len(only_in_backend)} | SDK-only: {len(only_in_sdk)}")


if __name__ == "__main__":
    main()
