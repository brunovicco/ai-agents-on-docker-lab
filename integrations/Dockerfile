# syntax=docker/dockerfile:1
#
# Package the read-only forecast and decoy MCP servers so sbx can launch them with Docker
# isolation instead of as host processes. Build with uv on the Docker Official Python image
# and run on a Docker Hardened Image, as the application image does. Build from the
# repository root:
#   docker build -f integrations/Dockerfile -t solar-forecast-mcp:dev .
# Without dhi.io access, reuse the builder image as the runtime:
#   --build-arg RUNTIME_IMAGE=<the python:3.13-slim reference in the builder FROM line>

# The hardened runtime is a named stage so Dependabot sees its digest on a FROM line. BuildKit
# skips the stage when RUNTIME_IMAGE points elsewhere, so a fallback build never pulls it.
ARG RUNTIME_IMAGE=hardened-runtime

FROM dhi.io/python:3.13@sha256:e1469187c0e6cc4b564c1e1a85cb69c90b816049e161b46d279fcd10172c12c7 AS hardened-runtime

FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90 AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa /uv /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project --extra mcp

FROM ${RUNTIME_IMAGE}

WORKDIR /app

# Root owns everything the servers read; the runtime user cannot modify code or the fixture.
COPY --from=builder /app/.venv/lib/python3.13/site-packages /app/site-packages
COPY integrations/forecast_mcp.py integrations/decoy_mcp.py /app/integrations/
COPY lab/forecast/day.json /app/lab/forecast/day.json

ENV PYTHONPATH=/app/site-packages \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER 65532

ENTRYPOINT ["python", "integrations/forecast_mcp.py"]
