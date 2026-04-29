"""Centralized settings via env vars."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def env(name: str, default: str | None = None, *, required: bool = False) -> str:
    v = os.environ.get(name, default)
    if required and not v:
        raise RuntimeError(f"missing required env var: {name}")
    return v or ""


TAVILY_API_KEY = env("TAVILY_API_KEY", required=True)
BOCHA_API_KEY = env("BOCHA_API_KEY", "")
SERPER_API_KEY = env("SERPER_API_KEY", "")

BAILIAN_API_KEY = env("BAILIAN_API_KEY", required=True)
BAILIAN_BASE_URL = env("BAILIAN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
BAILIAN_MODEL = env("BAILIAN_MODEL", "deepseek-v4-flash")
BAILIAN_ENABLE_THINKING = env("BAILIAN_ENABLE_THINKING", "true").lower() == "true"

# Auth — comma-separated valid keys, simplest possible
RP_DEV_API_KEY = env("RP_DEV_API_KEY", "rp-dev")
RP_DEMO_API_KEY = env("RP_DEMO_API_KEY", "rp-demo-public")
VALID_API_KEYS = {RP_DEV_API_KEY, RP_DEMO_API_KEY}

PORT = int(env("RP_PORT", "3725"))

# qmp_data PostgreSQL (READ-ONLY)
QMP_DB_HOST = env("QMP_DB_HOST", "192.168.1.23")
QMP_DB_PORT = int(env("QMP_DB_PORT", "5432"))
QMP_DB_NAME = env("QMP_DB_NAME", "qmp_data")
QMP_DB_USER = env("QMP_DB_USER", "postgres")
QMP_DB_PASSWORD = env("QMP_DB_PASSWORD", "postgres")
QMP_DB_DSN = f"postgresql://{QMP_DB_USER}:{QMP_DB_PASSWORD}@{QMP_DB_HOST}:{QMP_DB_PORT}/{QMP_DB_NAME}"

# researchpipe_postgres (READ-WRITE, our own DB on same host as qmp_postgres)
RP_PG_HOST = env("RP_PG_HOST", "192.168.1.23")
RP_PG_PORT = int(env("RP_PG_PORT", "5433"))
RP_PG_NAME = env("RP_PG_NAME", "researchpipe")
RP_PG_USER = env("RP_PG_USER", "postgres")
RP_PG_PASSWORD = env("RP_PG_PASSWORD", "postgres")
RP_PG_DSN = f"postgresql://{RP_PG_USER}:{RP_PG_PASSWORD}@{RP_PG_HOST}:{RP_PG_PORT}/{RP_PG_NAME}"

# SiliconFlow — embedding + rerank + OCR (free tier for bge-m3 / bge-reranker-v2-m3)
SILICONFLOW_API_KEY = env("SILICONFLOW_API_KEY", "")
SILICONFLOW_BASE_URL = env("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
SILICONFLOW_EMBED_MODEL = env("SILICONFLOW_EMBED_MODEL", "BAAI/bge-m3")
SILICONFLOW_RERANK_MODEL = env("SILICONFLOW_RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
