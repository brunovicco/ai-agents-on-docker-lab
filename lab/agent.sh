#!/usr/bin/env bash
# Plan with a local model through Docker Agent and Docker Model Runner, then verify the
# proposal on the host against the original forecast.
set -euo pipefail
cd "$(dirname "$0")/.."
# restricted runs read-only-annotated tools and denies every other tool call.
docker agent run --exec --last --json --safety restricted lab/agent/solar-planner.yaml \
  "Plan the charging hours for the forecast." |
  PYTHONPATH=src python3 -m solar_dispatch.entrypoints.dispatch verify lab/forecast/day.json
