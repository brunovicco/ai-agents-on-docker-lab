# syntax=docker/dockerfile:1
#
# Build with uv on the Docker Official Python image; run on a Docker Hardened Image.
# The hardened runtime has no shell or package manager, so the build installs the locked
# dependencies and the project into site-packages that the runtime interpreter loads
# through PYTHONPATH. Without dhi.io access, reuse the builder image as the runtime:
#   --build-arg RUNTIME_IMAGE=<the python:3.13-slim reference in the builder FROM line>

# The hardened runtime is a named stage so Dependabot sees its digest on a FROM line. BuildKit
# skips the stage when RUNTIME_IMAGE points elsewhere, so a fallback build never pulls it.
ARG RUNTIME_IMAGE=hardened-runtime

FROM dhi.io/python:3.13@sha256:ab678ca8fa69d36f1386fb71f4252d1a9561b7542ca84f5d14babffebcf4f479 AS hardened-runtime

FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90 AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa /uv /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Cache dependencies independently from source changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

# Install the project as a regular package, not an editable link to /app/src.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

FROM ${RUNTIME_IMAGE}

WORKDIR /app

# Root owns the code and the fixture; the runtime user can read but not modify them.
COPY --from=builder /app/.venv/lib/python3.13/site-packages /app/site-packages
COPY lab/forecast/day.json /app/lab/forecast/day.json

ENV PYTHONPATH=/app/site-packages \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER 65532

ENTRYPOINT ["python", "-m", "solar_dispatch.entrypoints.dispatch"]
CMD ["plan", "lab/forecast/day.json"]
