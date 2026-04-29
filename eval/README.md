# ResearchPipe — Eval (W1 prompt validation)

验证 ResearchPipe 三个旗舰端点的 prompt 出货质量。当前 W1 范围：`POST /v1/extract/research`。

## 跑一遍

```bash
cd ~/projects/ResearchPipe/eval

# 1) 抓 9 篇研报（PDF + GS / MS HTML）
uv run python -m src.fetch

# 2) PDF/HTML → 文本
uv run python -m src.parse

# 3) 跑 LLM 抽取（V4-Pro no-think，~ 35-40 min）
uv run python -m src.extract

# 4) 出验证报告
uv run python -m src.report
```

## 目录

```
eval/
├── data/
│   ├── manifest.json            # 9 篇报告元信息
│   ├── raw/                     # 下载下来的 PDF / HTML
│   └── parsed/                  # 转成纯文本的 markdown
├── src/
│   ├── llm.py                   # 百炼 OpenAI 兼容 client
│   ├── schemas.py               # 11 字段 pydantic schema
│   ├── prompts/extract_research.py
│   ├── fetch.py                 # 下载
│   ├── parse.py                 # PDF/HTML → text
│   ├── extract.py               # LLM 抽取主入口
│   └── report.py                # 出 W1_eval_*.md
└── output/
    ├── extractions/<id>.json    # 抽取的原始 JSON
    ├── readable/<id>.md         # 单份可读视图
    └── W1_eval_<date>.md        # 总报告（含自评打分表）
```

## LLM 配置

通过 `.env` 走环境变量（VIA `aliyun-bailian` 拿 key）：
- BAILIAN_API_KEY=…
- BAILIAN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
- BAILIAN_MODEL=deepseek-v4-pro
- BAILIAN_ENABLE_THINKING=false

V4 系列**默认开 thinking**，必须显式 `false` 才走快通道。

## 自评打分

每篇 4 维度 × 0-3 分（满分 12），≥ 9 为单篇通过：
1. **字段覆盖** — 11 字段缺几个
2. **内容准确** — core_thesis / target_price 等是否对得上原文
3. **翻译质量** — 海外英文研报翻译是否流畅、术语对
4. **数据点结构** — key_data_points 是否齐 metric+value+source+year

≥ 7/9 篇过门 → 进朋友盲测。
