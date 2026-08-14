#!/usr/bin/env bash
# Fetch the latest `no-ai-slop` skill subtree from
# github.com/petergyang/no-ai-slop/skills/no-ai-slop via degit.
# Always overwrites the cache. Prints the cache path on stdout.
# If fetch fails and no cache exists, exit 1. Report the missing external
# detector and continue with writing-style.md's internal hard-ban sweep.
#
# Usage: load-no-ai-slop.sh
#        SLOP_CACHE=$(load-no-ai-slop.sh)
set -euo pipefail

CACHE="$HOME/.cache/innei-skills/no-ai-slop"
mkdir -p "$(dirname "$CACHE")"

if ! npx -y degit petergyang/no-ai-slop/skills/no-ai-slop "$CACHE" --force >&2; then
  if [ -d "$CACHE" ]; then
    echo "warning: degit fetch failed; using stale cache" >&2
  else
    echo "error: degit fetch failed and no cache available" >&2
    echo "continue with writing-style.md's internal hard-ban sweep" >&2
    exit 1
  fi
fi

echo "$CACHE"
