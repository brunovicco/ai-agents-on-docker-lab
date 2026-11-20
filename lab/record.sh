#!/usr/bin/env bash
# Record a reviewable transcript of the local Docker Sandboxes experiment.
# Run `bash lab/demo.sh sandbox` first so the environment exists and its plan is approved.
# Extra arguments name sandboxes to inspect, for example: bash lab/record.sh solar-codex
# Review the transcript before committing it: sbx output can include usernames and host paths.
set -uo pipefail
cd "$(dirname "$0")/.."
if ! command -v sbx >/dev/null; then
  echo "sbx is not installed or not on PATH. See https://docs.docker.com/ai/sandboxes/" >&2
  exit 1
fi
out=${SOLAR_EVIDENCE:-docs/evidence/$(date -u +%Y-%m-%d)-local.md}
mkdir -p "$(dirname "$out")"

step() {
  local title=$1 shown=$2 status
  shift 2
  printf '\n## %s\n\n```console\n$ %s\n' "$title" "$shown" >>"$out"
  "$@" 2>&1 | tee -a "$out"
  status=${PIPESTATUS[0]}
  printf '```\n\nExit status: %s\n' "$status" >>"$out"
}

propose_and_verify() {
  sbx env exec lab/sbxenv.yaml -- solar-plan |
    PYTHONPATH=src python3 -m solar_dispatch.entrypoints.dispatch verify lab/forecast/day.json
}

printf '# Docker Sandboxes evidence\n\nRecorded %s with `bash lab/record.sh`.\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >"$out"
step "CLI version" "sbx version" sbx version
step "Sandbox proposal verified on the host" \
  "sbx env exec lab/sbxenv.yaml -- solar-plan | python3 -m solar_dispatch.entrypoints.dispatch verify lab/forecast/day.json" \
  propose_and_verify
step "Sandbox configuration" "sbx inspect solar-dispatch" sbx inspect solar-dispatch
step "Filesystem and network policy probe (the policy check exits 1 when the kit denies github.com)" \
  "bash lab/probe.sh" bash lab/probe.sh
step "Blocked request from inside the sandbox (expected to fail)" \
  "sbx env exec lab/sbxenv.yaml -- curl --max-time 5 -fsS -o /dev/null https://github.com/" \
  sbx env exec lab/sbxenv.yaml -- curl --max-time 5 -fsS -o /dev/null https://github.com/
step "Policy log" "sbx policy log solar-dispatch" sbx policy log solar-dispatch
for name in "$@"; do
  step "MCP mode of $name" "sbx inspect $name" sbx inspect "$name"
done
echo "Wrote $out. Review it before committing."
