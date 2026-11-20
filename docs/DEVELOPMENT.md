# Development guide

## Setup

```bash
uv sync --frozen --all-groups --extra observability --extra mcp
```

The development environment uses Python 3.13. The `observability` extra provides the optional
OpenTelemetry runtime and the `mcp` extra installs the SDK for the forecast server and its
protocol check.

## Run checks

```bash
uv run python scripts/quality_gate.py
uv run --extra mcp python integrations/check_mcp.py
```

Use the quality gate to check lint, formatting, architecture, typing, pytest, governance, and
dependency security. The MCP check starts the forecast server over stdio, initializes a session,
discovers its tool, and calls `forecast_day`.

For focused observability tests:

```bash
uv run pytest tests/unit/test_observability.py tests/unit/test_logging.py
```

Tests use in-memory exporters or fakes. Do not point development or CI checks at a real backend.

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
docker build -t solar-dispatch-lab .
docker run --rm --read-only --network none solar-dispatch-lab
```

The Dockerfile uses uv to install locked dependencies into a virtual environment. The slim
runtime runs the dispatch CLI as a non-root user. With its default arguments it emits a
proposal for the bundled forecast. See the [sandbox walkthrough](SANDBOX-LAB.md) for the kit
build and the OCI export with attestations.

## Harness provenance

The project started from the [Codex Python Engineering Harness](https://github.com/brunovicco/codex-python-engineering-harness/tree/e9e297456573d216f070a41a7cdaa108dd599c5b)
v1.2.1 using the `service` and `agentic` profiles. The original generator metadata is in
`.harness.json`. The following command reproduces the scaffold from that checkout:

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
