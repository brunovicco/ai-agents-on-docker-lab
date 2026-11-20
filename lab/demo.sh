#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src
cli=solar_dispatch.entrypoints.dispatch
forecast=lab/forecast/day.json
case "${1:-local}" in
  local) python3 -m "$cli" plan "$forecast" | python3 -m "$cli" verify "$forecast";;
  sandbox)
    sbx env plan lab/sbxenv.yaml
    if sbx inspect solar-dispatch >/dev/null 2>&1; then
      echo "Reusing sandbox solar-dispatch. Run 'sbx env rm lab/sbxenv.yaml' to recreate it." >&2
    else
      sbx env create lab/sbxenv.yaml
    fi
    sbx env exec lab/sbxenv.yaml -- solar-plan |
      python3 -m "$cli" verify "$forecast"
    sbx inspect solar-dispatch
    ;;
  *) echo 'Usage: bash lab/demo.sh [local|sandbox]' >&2; exit 2;;
esac
