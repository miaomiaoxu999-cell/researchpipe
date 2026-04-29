"""Quality eval for /v1/corpus/semantic_search using real research-style queries.

Captures top-K results per query and prints title + rerank + cosine + content preview.
Manual judgment afterwards.
"""
from __future__ import annotations

import json
import time

import httpx

BACKEND = "http://localhost:3725"
KEY = "rp-demo-public"
HEADERS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

QUERIES = [
    # 1. 行业垂直 — 应命中具体研报
    {"id": "Q1_battery", "query": "宁德时代固态电池量产计划进展", "expect": "ningde / 固态 / 量产相关 / 动力电池 broker 报告"},
    # 2. 半导体设备
    {"id": "Q2_semi_dev", "query": "光刻机国产化突破刻蚀薄膜沉积", "expect": "半导体设备 / 国产替代 / 刻蚀 / 沉积"},
    # 3. 具身智能 + filter
    {"id": "Q3_robot_filtered", "query": "人形机器人灵巧手成本结构", "industry": "具身智能", "expect": "人形机器人 / 灵巧手 / 成本拆解；行业 filter 应只命中具身智能 tag"},
    # 4. 创新药 / BD
    {"id": "Q4_biotech_BD", "query": "中国 biotech 创新药出海 BD 交易首付款", "expect": "BD / license-out / 创新药"},
    # 5. AI 应用 — 软件
    {"id": "Q5_ai_app", "query": "DeepSeek V4 开源对国产大模型生态影响", "expect": "DeepSeek / 大模型 / 国产生态"},
    # 6. 跨域宏观
    {"id": "Q6_macro", "query": "美联储降息周期对中国权益资产配置", "expect": "美联储 / 降息 / 权益配置 / 宏观策略"},
    # 7. 英文混合 (国际投行)
    {"id": "Q7_intl_macro", "query": "China 2026 GDP outlook recovery momentum", "expect": "Morgan Stanley/UBS/Barclays 类宏观研报"},
    # 8. 公司战略
    {"id": "Q8_strategy", "query": "比亚迪海外建厂欧洲泰国巴西", "expect": "比亚迪 / 海外 / 建厂 / 出海"},
]


def run_one(cli: httpx.Client, q: dict) -> dict:
    body = {"query": q["query"], "top_n": 5, "candidate_k": 50}
    if "industry" in q:
        body["industry"] = q["industry"]
    if "broker" in q:
        body["broker"] = q["broker"]
    started = time.time()
    try:
        r = cli.post(f"{BACKEND}/v1/corpus/semantic_search", json=body, timeout=120.0)
        d = r.json()
    except Exception as e:
        return {"id": q["id"], "ok": False, "error": str(e)[:200]}
    if r.status_code != 200:
        return {"id": q["id"], "ok": False, "error": f"http_{r.status_code}: {str(d)[:200]}"}
    elapsed = round((time.time() - started) * 1000, 1)
    md = d.get("metadata", {})
    return {
        "id": q["id"],
        "ok": True,
        "elapsed_ms": elapsed,
        "phases": md.get("phases_ms"),
        "n_results": d.get("total"),
        "results": [
            {
                "rerank": round(r.get("rerank_score") or 0, 3),
                "cosine": round(r.get("cosine_sim") or 0, 3),
                "title": (r.get("title") or "")[:60],
                "broker": r.get("broker"),
                "page_no": r.get("page_no"),
                "industry_tags": r.get("industry_tags"),
                "preview": (r.get("content_preview") or "")[:240],
            }
            for r in (d.get("results") or [])[:5]
        ],
    }


def main():
    cli = httpx.Client(headers=HEADERS)
    rows = []
    for q in QUERIES:
        print(f"\n{'='*88}")
        print(f"{q['id']}: {q['query']}")
        if q.get("industry"):
            print(f"  filter: industry={q['industry']}")
        print(f"  expect: {q['expect']}")
        out = run_one(cli, q)
        rows.append(out)
        if not out["ok"]:
            print(f"  ❌ ERROR: {out['error']}")
            continue
        print(f"  phases: {out['phases']} | wall {out['elapsed_ms']}ms")
        for i, r in enumerate(out["results"]):
            print(f"\n  #{i+1}  rerank={r['rerank']:.3f}  cosine={r['cosine']:.3f}")
            broker_str = r['broker'] or '-'
            tags_str = ','.join(r['industry_tags'] or []) or '-'
            print(f"      {broker_str[:18]:18s} | page {r['page_no']} | tags=[{tags_str}]")
            print(f"      title: {r['title']}")
            preview = r['preview'].replace('\n', ' ').strip()
            print(f"      \"{preview[:200]}\"")
    cli.close()
    # Save raw
    out_path = "/home/muye/projects/ResearchPipe/eval/semantic_eval_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"\n\nSaved raw → {out_path}")


if __name__ == "__main__":
    main()
