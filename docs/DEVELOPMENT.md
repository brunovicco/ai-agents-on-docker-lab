# Development guide

## Setup

```bash
uv sync --frozen --all-groups --extra mcp
```

The development environment uses Python 3.13. The package itself has no runtime dependencies;
the `mcp` extra installs the SDK for the forecast server and its protocol check.

## Run checks

```bash
uv run python scripts/quality_gate.py
uv run --extra mcp python integrations/check_mcp.py
```

Use the quality gate to check lint, formatting, architecture, typing, pytest, governance, and
dependency security. The MCP check starts the forecast and decoy servers over stdio, checks the
read-only annotations and output schema of `forecast_day`, and calls both tools. Add
`--image solar-forecast-mcp:dev` to run the same checks against the container built from
`integrations/Dockerfile`, or `--url http://127.0.0.1:8822/mcp` to check a server started with
`--transport streamable-http`.

### Dispatch smoke tests

```bash
bash lab/demo.sh local
printf '%s\n' '{"hours":[9,12]}' |
  PYTHONPATH=src python3 -m solar_dispatch.entrypoints.dispatch verify lab/forecast/day.json
```

The first command should accept hours 10 and 11 with 600 Wh of grid energy. The second should
exit with status 1 because a lower-cost schedule is available. See the
[dispatch model](DISPATCH.md) for the full fixture and CLI contract.

## Container

```bash
docker login dhi.io
docker build -t solar-dispatch:dev .
docker run --rm --read-only --network none solar-dispatch:dev
```

The Dockerfile uses uv on the Docker Official Python image to install the locked dependencies and
the project, not as an editable link, into `site-packages`. The runtime stage copies only those
packages and the bundled forecast onto `dhi.io/python:3.13`, a Docker Hardened Image without a
shell or package manager, and runs the dispatch CLI as user 65532. With its default arguments it
emits a proposal for the bundled forecast. Without `dhi.io` access, pass `--build-arg RUNTIME_IMAGE=`
with the `docker.io/library/python:3.13-slim` reference from the `FROM … AS builder` line, so the runtime matches the builder.

The `container` CI job builds the application and MCP images, runs the application without network
on a read-only filesystem, verifies its proposal on the runner, checks the runtime user, confirms
that a suboptimal proposal is rejected inside the container, and runs the MCP checks inside the
MCP image. It also builds both images for arm64 under QEMU and verifies the arm64 application
image's proposal, so a platform-specific failure shows up before merge. It uses the hardened runtime when the `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`
repository secrets hold a Docker username and a read-only personal access token. Otherwise it falls
back to the official image with a warning. The `publish` job runs on pushes to `main`, requires
those secrets, and publishes the images and the kit for `linux/amd64` and `linux/arm64` to GitHub Container Registry
with SBOM and
provenance attestations. See the [sandbox walkthrough](SANDBOX-LAB.md#published-images-and-attestations)
to inspect them.

Dependabot proposes weekly updates for the pinned base images, GitHub Actions, and `uv.lock`.
It bundles each ecosystem's updates, and each base image across both Dockerfiles, into one pull
request, because `main` requires branches to be up to date before merge. It ignores Python minor
and major versions for the images, which must match the hardened 3.13 runtime, and major versions
of Python dependencies.

## Harness provenance

The project started from the [Codex Python Engineering Harness](https://github.com/brunovicco/codex-python-engineering-harness/tree/e9e297456573d216f070a41a7cdaa108dd599c5b)
v1.2.1 using the `service` and `agentic` profiles. The original generator metadata is in
`.harness.json`. The scaffold's OpenTelemetry, Langfuse, and structured-logging adapters, with
their tests and the empty application layer, were removed because the dispatch flow never used
them; `.harness.json` still lists them as generated files. The project was named `solar-dispatch-lab` then. The following command reproduces the scaffold from that checkout:

```bash
python3 bootstrap.py --name solar-dispatch-lab --package solar_dispatch \
  --target ../solar-dispatch-lab --profile service --governance-profile agentic
```

## Local configuration

Copy `.env.example` only when the application supports local dotenv loading. Never commit `.env` or real credentials.

## Codex

- Run `/status` to inspect the active project and configuration.
- Run `/hooks` to inspect configured hooks.
- Run `codex --version` from the shell for an installation check.
- Use `$plan-change` before complex work.
- Use `$quality-gate` before completion.
- Use `$prepare-pr` to produce a reviewable PR description.

Codex discovers durable project guidance in `AGENTS.md`, workflows in `.agents/skills/`, and
trusted project configuration and hooks under `.codex/`. Skills do not silently delegate work;
the active agent follows their checked-in workflow and the user's requested scope.
