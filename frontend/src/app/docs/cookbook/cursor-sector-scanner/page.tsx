export default function CursorSectorScanner() {
  return (
    <>
      <h1 className="font-serif text-[36px] tracking-tight text-ink">用 Cursor + ResearchPipe 30 分钟写一个赛道扫描器</h1>
      <p className="text-[15px] text-muted mt-2 mb-8">
        目标：每周一早上 8 点自动跑 N 个赛道扫描，结果发到飞书 / 微信群。
      </p>

      <h2>Step 0 - 准备</h2>
      <ul>
        <li>Cursor IDE（含 Claude Sonnet 或 GPT-4o）</li>
        <li>Python 3.10+</li>
        <li>ResearchPipe API key（rp.zgen.xin/dashboard 拿）</li>
      </ul>

      <h2>Step 1 - 把 docs 喂给 Cursor</h2>
      <p>在 Cursor 里 <code>@docs https://rp.zgen.xin/docs</code> 添加为知识源。</p>

      <h2>Step 2 - 一句话生成骨架</h2>
      <p>给 Cursor agent 模式：</p>
      <pre className="bg-cream border border-line p-4 my-3 overflow-x-auto">
        <code className="font-mono text-[12.5px]">{`Build a Python script using the ResearchPipe SDK that:
1. takes a list of sectors (具身智能 / 半导体国产化 / 创新药出海)
2. calls rp.research_sector(input=sector, time_range="6m") for each
3. extracts executive_summary + top 5 deals + top 3 risks
4. formats as Markdown
5. POSTs to a Feishu webhook URL`}</code>
      </pre>

      <h2>Step 3 - Cursor 生成代码（≈ 50 行）</h2>
      <pre className="bg-cream border border-line p-4 my-3 overflow-x-auto">
        <code className="font-mono text-[12.5px]">{`from researchpipe import ResearchPipe
import requests, os

rp = ResearchPipe(api_key=os.environ["RESEARCHPIPE_KEY"])
SECTORS = ["具身智能", "半导体国产化", "创新药出海"]
FEISHU_URL = os.environ["FEISHU_WEBHOOK"]

def scan(sector: str) -> str:
    r = rp.research_sector(input=sector, time_range="6m")
    res = r["result"]
    md = [f"## {sector}", res["executive_summary"], "", "### 头部 deals"]
    for d in (res.get("deals", {}).get("domestic") or [])[:5]:
        md.append(f"- {d['company_name']} {d.get('round', '')} ({d.get('amount_cny_m', '?')} M)")
    md.append("\\n### Top 3 risks")
    for r in (res.get("risks") or [])[:3]:
        md.append(f"- [{r.get('severity', '?')}] {r['description']}")
    return "\\n".join(md)

if __name__ == "__main__":
    body = "\\n\\n".join(scan(s) for s in SECTORS)
    requests.post(FEISHU_URL, json={"msg_type": "text", "content": {"text": body}})`}</code>
      </pre>

      <h2>Step 4 - 加 cron（Linux/macOS）</h2>
      <pre className="bg-cream border border-line p-4 my-3 overflow-x-auto">
        <code className="font-mono text-[12.5px]">{`# crontab -e
0 8 * * 1 cd ~/scanner && /usr/bin/python3 scanner.py >> scanner.log 2>&1`}</code>
      </pre>

      <h2>Step 5 - 完事</h2>
      <p>每周一 8 点，飞书群里出现一份赛道扫描。一次调用花 ~150 credits（3 sector × 50c），月开销 ¥30 内。</p>

      <h3>下一步</h3>
      <ul>
        <li>加 <code>rp.companies_screen(...)</code> 把扫描转成可投标的清单</li>
        <li>加 <code>rp.watch_create(...)</code> 让 ResearchPipe 自己 cron，省你写脚本</li>
      </ul>
    </>
  );
}
