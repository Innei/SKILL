#!/usr/bin/env bash
# Create a draft post on mx-space from a LiteXML envelope, mark it as
# AI-written (aiGen=2), optionally attach a skill snippet via
# meta.skillIds, open the admin edit page for Innei to preview, and
# silence the full server response. Does NOT publish — run
# `mxs post publish <slug>` after Innei approves.
#
# Usage:
#   publish-post.sh <article.xml>
#   publish-post.sh <article.xml> --skill-id <id> [--skill-id <id> ...]
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $(basename "$0") <article.xml> [--skill-id <id> ...]" >&2
  exit 2
fi

SRC="$1"
shift
[ -f "$SRC" ] || { echo "error: $SRC not found" >&2; exit 1; }

SKILL_IDS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --skill-id)
      [ $# -ge 2 ] || { echo "error: --skill-id requires a value" >&2; exit 2; }
      SKILL_IDS+=("$2")
      shift 2
      ;;
    *)
      echo "error: unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

if [ "${#SKILL_IDS[@]}" -eq 0 ]; then
  META='{"aiGen":2}'
else
  command -v jq >/dev/null 2>&1 || {
    echo "error: jq is required when --skill-id is passed" >&2
    exit 1
  }
  META=$(printf '%s\n' "${SKILL_IDS[@]}" | jq -R . | jq -s '{aiGen: 2, skillIds: .}' -c)
fi

mxs post create --file "$SRC" --meta "$META" --open --silent
