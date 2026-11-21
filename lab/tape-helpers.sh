# Helpers for lab/demo.tape, sourced off camera. The sbx commands themselves stay on screen.
# shellcheck shell=bash

export PYTHONPATH=src
PS1='\[\e[1;34m\]$\[\e[0m\] '

# Title line that stays at the top of every frame.
banner() {
  clear
  printf '\e[1mAI Agents on Docker Lab\e[0m  \e[2m·  trust the verifier, not the agent\e[0m\n\n'
}

# Narration: replaces its own command line with one cyan line, so the recording shows the
# sentence and not the command that printed it.
say() {
  printf '\e[1A\e[2K\e[36m▸ %s\e[0m\n' "$*"
}

# Host verifier: green when it accepts, red when it rejects.
verify() {
  local out
  if out=$(python3 -m solar_dispatch.entrypoints.dispatch verify lab/forecast/day.json 2>&1); then
    printf '\e[1;32m%s\e[0m\n' "$out"
  else
    printf '\e[1;31m%s\e[0m\n' "$out"
  fi
}
