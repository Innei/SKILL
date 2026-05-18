#!/usr/bin/env bash
# Fetch the latest `litexml-authoring` skill subtree from
# github.com/Innei/haklex/.claude/skills/litexml-authoring via degit.
# Always overwrites the cache. Prints the cache path on stdout.
#
# Usage: load-litexml.sh                # fetch + print path
#        LITEXML_CACHE=$(load-litexml.sh)
set -euo pipefail

CACHE="$HOME/.cache/innei-skills/litexml-authoring"
mkdir -p "$(dirname "$CACHE")"

if ! npx -y degit Innei/haklex/.claude/skills/litexml-authoring "$CACHE" --force >&2; then
  if [ -d "$CACHE" ]; then
    echo "warning: degit fetch failed; using stale cache" >&2
  else
    echo "error: degit fetch failed and no cache available" >&2
    exit 1
  fi
fi

echo "$CACHE"
