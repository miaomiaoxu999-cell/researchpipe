"""ResearchPipe Python SDK.

Quick start:

    from researchpipe import ResearchPipe

    rp = ResearchPipe(api_key="rp-...")
    result = rp.search(query="具身智能 融资 2026")
    print(result.results)

Async variant:

    import asyncio
    from researchpipe import AsyncResearchPipe

    async def main():
        async with AsyncResearchPipe(api_key="rp-...") as rp:
            r = await rp.search(query="...")
            print(r.results)

    asyncio.run(main())
"""
from .client import ResearchPipe, AsyncResearchPipe
from .errors import ResearchPipeError, AuthError, RateLimitError, UpstreamError

__version__ = "0.1.0"

__all__ = [
    "ResearchPipe",
    "AsyncResearchPipe",
    "ResearchPipeError",
    "AuthError",
    "RateLimitError",
    "UpstreamError",
    "__version__",
]
