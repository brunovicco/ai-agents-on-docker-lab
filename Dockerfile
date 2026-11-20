# syntax=docker/dockerfile:1
#
# Build with uv on the Docker Official Python image; run on a Docker Hardened Image.
# The hardened runtime has no shell or package manager, so the build installs the locked
# dependencies and the project into site-packages that the runtime interpreter loads
# through PYTHONPATH. Without dhi.io access, build with:
#   --build-arg RUNTIME_IMAGE=python:3.13-slim@sha256:6771159cd4fa5d9bba1258caf0b82e6b73458c694d178ad97c5e925c2d0e1a91

ARG RUNTIME_IMAGE=dhi.io/python:3.13@sha256:ab678ca8fa69d36f1386fb71f4252d1a9561b7542ca84f5d14babffebcf4f479

FROM python:3.13-slim@sha256:6771159cd4fa5d9bba1258caf0b82e6b73458c694d178ad97c5e925c2d0e1a91 AS builder

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
