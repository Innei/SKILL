#!/usr/bin/env bash
set -euo pipefail

CACHE="$HOME/.cache/innei-skills/lieflat-less-ai-tone"
mkdir -p "$(dirname "$CACHE")"

if ! npx -y degit larashero3-dotcom/lieflat-less-ai-tone "$CACHE" --force >&2; then
  if [ -f "$CACHE/scripts/detect.py" ]; then
    echo "warning: degit fetch failed; using stale cache" >&2
  else
    echo "error: degit fetch failed and no cache available" >&2
    echo "continue with writing-style.md's internal hard-ban sweep" >&2
    exit 1
  fi
fi

echo "$CACHE"
