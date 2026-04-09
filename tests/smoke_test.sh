#!/usr/bin/env bash
set -euo pipefail

required_files=(
  "AGENTS.md"
  "README.md"
  "doc_map.md"
  "docs/agent_commands.md"
  "Makefile"
)

for f in "${required_files[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "Missing required repository file: $f" >&2
    exit 1
  fi
done

echo "Smoke checks passed."
