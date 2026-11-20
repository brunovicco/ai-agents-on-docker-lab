#!/usr/bin/env bash
# Plan with a local model through Docker Agent and Docker Model Runner, then verify the
# proposal on the host against the original forecast.
set -euo pipefail
cd "$(dirname "$0")/.."

# The lab was run with Docker Agent v1.163.0; v1.128.0 lacked flags it relied on.
version=$(docker agent version 2>/dev/null | sed -n 's/^docker agent version v\([0-9.]*\).*/\1/p')
if ! python3 -c 'import sys; v = tuple(map(int, sys.argv[1].split("."))); sys.exit(v < (1, 147, 0))' \
  "${version:-0}"; then
  echo "Docker Agent v1.147.0 or later is required, found ${version:-none}. See docs/SANDBOX-LAB.md section 5." >&2
  exit 1
fi
model=$(sed -n 's/^ *model: \(ai\/.*\)$/\1/p' lab/agent/solar-planner.yaml)
if ! docker model inspect "$model" >/dev/null 2>&1; then
  echo "Model $model is not available. Enable Model Runner with 'docker desktop enable model-runner'," >&2
  echo "wait for Docker to restart, then run 'docker model pull $model'." >&2
  exit 1
fi

# Serve the forecast tool from a running container. A server started per session by Docker
# Agent missed the 30-second turn budget. The port is published on loopback only, and the
# container keeps a read-only filesystem, no capabilities, and an unprivileged user.
container=solar-forecast-mcp-http
docker rm -f "$container" >/dev/null 2>&1 || true
docker run -d --rm --name "$container" -p 127.0.0.1:8822:8000 --read-only --cap-drop ALL \
  --security-opt no-new-privileges solar-forecast-mcp:dev \
  --transport streamable-http --host 0.0.0.0 --port 8000 >/dev/null
trap 'docker rm -f "$container" >/dev/null 2>&1 || true' EXIT
for _ in $(seq 1 40); do
  status=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8822/mcp || true)
  [ "$status" != "000" ] && break
  sleep 0.25
done
if [ "$status" = "000" ]; then
  echo "The forecast MCP server did not start. Build it with section 2 of docs/SANDBOX-LAB.md." >&2
  exit 1
fi

# restricted runs read-only-annotated tools and denies every other tool call. The host keeps the
# full transcript: the evidence gate accepts the proposal only if the agent called forecast_day
# before its final answer, and the verifier then checks the answer itself.
transcript=${SOLAR_AGENT_TRANSCRIPT:-$(mktemp)}
if ! docker agent run --exec --json --safety restricted lab/agent/solar-planner.yaml \
  "Plan the charging hours for the forecast." >"$transcript"; then
  echo "Docker Agent failed before producing a proposal. Transcript: $transcript" >&2
  exit 1
fi
export PYTHONPATH=src
if ! proposal=$(python3 -m solar_dispatch.entrypoints.agent_evidence <"$transcript"); then
  echo "Transcript: $transcript" >&2
  exit 1
fi
printf '%s\n' "$proposal" | python3 -m solar_dispatch.entrypoints.dispatch verify lab/forecast/day.json
