export default function NotionWebhook() {
  return (
    <>
      <h1 className="font-serif text-[36px] tracking-tight text-ink">Notion 看板接 ResearchPipe webhook</h1>
      <p className="text-[15px] text-muted mt-2 mb-8">VC 团队共享看板：触发 ResearchPipe 自动写入 Notion 页面。</p>

      <h2>场景</h2>
      <p>VC 同事在群里发了个公司名，自动触发 ResearchPipe 跑公司尽调，结果作为新 Notion 页面落到团队看板。</p>

      <h2>Step 1 - Notion 准备</h2>
      <ul>
        <li>建一个 Database "Pipeline"，字段：Company / Stage / Industry / Risks / Source</li>
        <li>拿 Notion API integration token + database_id</li>
      </ul>

      <h2>Step 2 - 一个 Python webhook server (FastAPI)</h2>
      <pre className="bg-cream border border-line p-4 my-3 overflow-x-auto">
        <code className="font-mono text-[12.5px]">{`from fastapi import FastAPI, Request
from researchpipe import ResearchPipe
import httpx, os

app = FastAPI()
rp = ResearchPipe(api_key=os.environ["RESEARCHPIPE_KEY"])
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DB_ID = os.environ["NOTION_DB_ID"]

@app.post("/webhook")
async def webhook(req: Request):
    body = await req.json()
    company_name = body["company_name"]

    # 1) ResearchPipe 跑公司尽调
    job = rp.research_company(input=company_name)
    result = job["result"]

    # 2) 提炼字段
    page = {
        "parent": {"database_id": DB_ID},
        "properties": {
            "Company": {"title": [{"text": {"content": company_name}}]},
            "Stage": {"rich_text": [{"text": {"content": result.get("valuation_anchor", {}).get("latest_round", "?")}}]},
            "Industry": {"rich_text": [{"text": {"content": result.get("company_basic", {}).get("sector", "?")}}]},
            "Risks": {"rich_text": [{"text": {"content": "\\n".join(r.get("description", "") for r in result.get("red_flags", []))}}]},
        },
    }

    # 3) 写入 Notion
    async with httpx.AsyncClient() as cli:
        r = await cli.post(
            "https://api.notion.com/v1/pages",
            json=page,
            headers={
                "Authorization": f"Bearer {NOTION_TOKEN}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json",
            },
        )
    return {"notion_page_id": r.json().get("id"), "credits_used": result.get("metadata", {}).get("credits_charged")}`}</code>
      </pre>

      <h2>Step 3 - 部署</h2>
      <ul>
        <li>简单：<code>uvicorn webhook:app --host 0.0.0.0 --port 8000</code> + ngrok / cloudflare tunnel</li>
        <li>稳定：上 Vercel Edge Function 或 Cloudflare Worker</li>
      </ul>

      <h2>Step 4 - 触发</h2>
      <pre className="bg-cream border border-line p-4 my-3 overflow-x-auto">
        <code className="font-mono text-[12.5px]">{`curl -X POST https://your-webhook.example/webhook \\
  -H "Content-Type: application/json" \\
  -d '{"company_name":"宁德时代"}'`}</code>
      </pre>

      <h2>成本</h2>
      <p>每个公司尽调 = 50 credits ≈ ¥0.30。VC 团队一周触发 20 次 ≈ ¥6/周。</p>
    </>
  );
}
