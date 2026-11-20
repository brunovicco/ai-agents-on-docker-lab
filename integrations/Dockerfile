# syntax=docker/dockerfile:1
#
# Package the read-only forecast and decoy MCP servers so sbx can launch them with Docker
# isolation instead of as host processes. Build from the repository root:
#   docker build -f integrations/Dockerfile -t solar-forecast-mcp:dev .

FROM python:3.13-slim@sha256:6771159cd4fa5d9bba1258caf0b82e6b73458c694d178ad97c5e925c2d0e1a91 AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa /uv /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project --extra mcp

FROM python:3.13-slim@sha256:6771159cd4fa5d9bba1258caf0b82e6b73458c694d178ad97c5e925c2d0e1a91

RUN groupadd --system app && useradd --system --gid app --no-create-home app

WORKDIR /app

# Root owns everything the servers read; the app user cannot modify code or the fixture.
COPY --from=builder /app/.venv /app/.venv
COPY integrations/forecast_mcp.py integrations/decoy_mcp.py /app/integrations/
COPY lab/forecast/day.json /app/lab/forecast/day.json

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER app

ENTRYPOINT ["python", "integrations/forecast_mcp.py"]
