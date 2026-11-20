#!/usr/bin/env bash
# Plan with a local model through Docker Agent and Docker Model Runner, then verify the
# proposal on the host against the original forecast.
set -euo pipefail
cd "$(dirname "$0")/.."

# --exec --last needs Docker Agent v1.147.0 or later.
version=$(docker agent version 2>/dev/null | sed -n 's/^docker agent version v\([0-9.]*\).*/\1/p')
if ! python3 -c 'import sys; v = tuple(map(int, sys.argv[1].split("."))); sys.exit(v < (1, 147, 0))' \
  "${version:-0}"; then
  echo "Docker Agent v1.147.0 or later is required, found ${version:-none}. Update Docker Desktop." >&2
  exit 1
fi
model=$(sed -n 's/^ *model: \(ai\/.*\)$/\1/p' lab/agent/solar-planner.yaml)
if ! docker model inspect "$model" >/dev/null 2>&1; then
  echo "Model $model is not available. Enable Model Runner with 'docker desktop enable model-runner'," >&2
  echo "wait for Docker to restart, then run 'docker model pull $model'." >&2
  exit 1
fi

# restricted runs read-only-annotated tools and denies every other tool call. Keep the answer
# separate so that an agent failure is reported as such, not as a rejected proposal.
if ! answer=$(docker agent run --exec --last --json --safety restricted \
  lab/agent/solar-planner.yaml "Plan the charging hours for the forecast."); then
  echo "Docker Agent failed before producing a proposal." >&2
  exit 1
fi
printf '%s\n' "$answer" |
  PYTHONPATH=src python3 -m solar_dispatch.entrypoints.dispatch verify lab/forecast/day.json
