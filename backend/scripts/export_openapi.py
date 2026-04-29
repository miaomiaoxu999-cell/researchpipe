"""Export OpenAPI 3 spec + Postman Collection. Run after route changes.

Outputs:
  backend/openapi.json
  backend/postman_collection.json
  frontend/public/openapi.json (so /openapi.json is reachable from web)
  frontend/public/postman_collection.json
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from researchpipe_api.main import app  # noqa: E402


def export_openapi():
    spec = app.openapi()
    out_backend = ROOT / "backend" / "openapi.json"
    out_frontend = ROOT / "frontend" / "public" / "openapi.json"
    for p in (out_backend, out_frontend):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OpenAPI: {len(spec['paths'])} paths → {out_backend}, {out_frontend}")
    return spec


def export_postman(spec: dict):
    """Convert FastAPI's OpenAPI spec to a Postman v2.1 collection."""
    items: list[dict] = []
    for path, methods in spec["paths"].items():
        for method, op in methods.items():
            if method not in {"get", "post", "put", "delete", "patch"}:
                continue
            # Gather body example
            body_example = None
            req_body = op.get("requestBody")
            if req_body:
                content = req_body.get("content", {}).get("application/json", {})
                schema = content.get("schema") or {}
                body_example = _example_from_schema(schema, spec)

            postman_path = path.replace("{", ":").replace("}", "")
            url_segments = [s for s in postman_path.lstrip("/").split("/") if s]

            request: dict = {
                "method": method.upper(),
                "header": [
                    {"key": "Authorization", "value": "Bearer {{api_key}}"},
                    {"key": "Content-Type", "value": "application/json"},
                    {"key": "Idempotency-Key", "value": "{{$guid}}"},
                ],
                "url": {
                    "raw": f"{{{{base_url}}}}{path}",
                    "host": ["{{base_url}}"],
                    "path": url_segments,
                },
            }
            if body_example is not None and method.upper() in {"POST", "PUT", "PATCH"}:
                request["body"] = {
                    "mode": "raw",
                    "raw": json.dumps(body_example, ensure_ascii=False, indent=2),
                    "options": {"raw": {"language": "json"}},
                }

            items.append(
                {
                    "name": f"{method.upper()} {path}",
                    "request": request,
                    "response": [],
                    "event": [],
                }
            )

    collection = {
        "info": {
            "_postman_id": str(uuid.uuid4()),
            "name": "ResearchPipe API",
            "description": "投研派 ResearchPipe — 投研垂类 API。"
            " auto-generated from FastAPI OpenAPI spec.",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "variable": [
            {"key": "base_url", "value": "https://rp.zgen.xin"},
            {"key": "api_key", "value": "rp-..."},
        ],
        "item": sorted(items, key=lambda x: x["name"]),
    }
    out_backend = ROOT / "backend" / "postman_collection.json"
    out_frontend = ROOT / "frontend" / "public" / "postman_collection.json"
    for p in (out_backend, out_frontend):
        p.write_text(json.dumps(collection, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Postman: {len(items)} requests → {out_backend}, {out_frontend}")


def _example_from_schema(schema: dict, spec: dict, _depth: int = 0) -> object:
    """Generate a small example object from a JSON schema. Crude but enough for Postman."""
    if _depth > 5:
        return None
    if "$ref" in schema:
        ref = schema["$ref"].split("/")[-1]
        target = (spec.get("components", {}).get("schemas", {}) or {}).get(ref, {})
        return _example_from_schema(target, spec, _depth + 1)

    if "anyOf" in schema or "oneOf" in schema:
        opts = schema.get("anyOf") or schema.get("oneOf") or []
        if opts:
            return _example_from_schema(opts[0], spec, _depth + 1)

    t = schema.get("type")
    if t == "object":
        out: dict = {}
        for name, prop in (schema.get("properties") or {}).items():
            out[name] = _example_from_schema(prop, spec, _depth + 1)
        return out
    if t == "array":
        return [_example_from_schema(schema.get("items") or {}, spec, _depth + 1)]
    if t == "string":
        if schema.get("enum"):
            return schema["enum"][0]
        return schema.get("default") or "string"
    if t in {"integer", "number"}:
        return schema.get("default") if schema.get("default") is not None else 0
    if t == "boolean":
        return schema.get("default") if schema.get("default") is not None else False
    return None


def main():
    spec = export_openapi()
    export_postman(spec)


if __name__ == "__main__":
    main()
