"""ResearchPipe API — FastAPI app entry point."""
from __future__ import annotations

import asyncio
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__, corpus_db, db, siliconflow, storage
from .middleware import install_middleware
from .routes import admin as admin_routes
from .routes import agent as agent_routes
from .routes import corpus as corpus_routes
from .routes import data as data_routes
from .routes import downloads as downloads_routes
from .routes import search as search_routes
from .routes import stub as stub_routes
from .routes import v3_combined as v3_routes
from .settings import PORT, RP_DEV_API_KEY  # noqa: F401  (PORT is used by uvicorn launcher)

# Init persistence at import (idempotent)
storage.init_db()
storage.ensure_dev_account(RP_DEV_API_KEY)

app = FastAPI(
    title="ResearchPipe API",
    version=__version__,
    description="投研垂类 API · SDK · MCP — 4 product lines, 50+ endpoints.",
)

import os as _os

_DEFAULT_ALLOWED_ORIGINS = [
    "https://rp.zgen.xin",
    "https://www.rp.zgen.xin",
    "http://localhost:3001",   # agent-ui dev
    "http://localhost:3726",   # frontend dev
    "http://localhost:3000",   # generic dev
]
_extra_origins = [o.strip() for o in _os.environ.get("RP_ALLOWED_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_DEFAULT_ALLOWED_ORIGINS + _extra_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Admin-Key"],
)


# Install token-bucket rate limit + Idempotency-Key middleware (handles X-RateLimit-*)
install_middleware(app)


@app.middleware("http")
async def add_response_headers(request: Request, call_next):
    started = time.time()
    response = await call_next(request)
    response.headers["X-Response-Time-Ms"] = f"{round((time.time() - started) * 1000, 1)}"
    response.headers["X-Researchpipe-Version"] = __version__
    return response




@app.get("/healthz")
async def healthz():
    return {"status": "ok", "version": __version__}


@app.get("/")
async def root():
    return {
        "name": "ResearchPipe API",
        "version": __version__,
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    # Log details server-side; never reflect raw exception (may contain SQL, paths).
    import logging
    logging.getLogger(__name__).exception("unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "An internal error occurred. The team has been notified.",
                "hint_for_agent": "Retry with exponential backoff. If persistent, the issue is on our side — please contact support.",
                "documentation_url": "https://rp.zgen.xin/docs/errors/internal_error",
            }
        },
    )


# Routes — order matters: corpus + v3_combined first → data_routes → stub_routes.
# FastAPI uses first-match for route resolution.
app.include_router(admin_routes.router)
app.include_router(agent_routes.router)
app.include_router(downloads_routes.router)
app.include_router(corpus_routes.router)
app.include_router(search_routes.router)
app.include_router(v3_routes.router)
app.include_router(data_routes.router)
app.include_router(stub_routes.router)


@app.on_event("shutdown")
async def shutdown_db():
    await db.close_pool()
    await corpus_db.close_pool()
    await siliconflow.close()
