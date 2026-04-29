FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5.1 /uv /usr/local/bin/uv

# Layer cache: copy only manifest first
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Then source
COPY src/ ./src/
RUN uv sync --frozen --no-dev

EXPOSE 3725
ENV PYTHONUNBUFFERED=1
CMD ["uv", "run", "uvicorn", "researchpipe_api.main:app", "--host", "0.0.0.0", "--port", "3725"]
