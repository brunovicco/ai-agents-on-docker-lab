#!/usr/bin/env bash
# Enumerate the help tree from the installed binary, including cloud-only commands.
set -euo pipefail
case "${1:-local}" in
  local) cli=(sbx);;
  cloud) cli=(sbx --cloud);;
  *) echo "Usage: bash lab/catalog.sh local|cloud" >&2; exit 2;;
esac
walk() {
  local help_text child
  if ! help_text=$("${cli[@]}" "$@" --help 2>&1); then
    printf '\n## %s %s\n\nHelp is unavailable in this session.\n\n' "${cli[*]}" "$*"
    return
  fi
  printf '\n## %s %s\n\n```text\n%s\n```\n' "${cli[*]}" "$*" "$help_text"
  while IFS= read -r child; do
    case "$child" in help|completion|'') continue;; esac
    walk "$@" "$child"
  done < <(printf '%s\n' "$help_text" | awk '
    /^[^ ].*Commands:$/ {group=1;next}
    /^Commands:$/ {group=1;next}
    /^[^ ]/ || /^$/ {group=0}
    group && /^  [[:alnum:]-]+  +/ {print $1}
  ')
}
sbx version
walk
