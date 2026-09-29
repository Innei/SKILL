#!/usr/bin/env bash
# Create a native draft entity on mx-space from a LiteXML envelope, mark it
# with an AI disclosure (aiGen, default 2 = fully AI-written), optionally
# attach one or more skill snippets via meta.skillIds, open the admin draft
# editor for the user to preview, and emit only { ok, id }. The draft is
# invisible on the site until `mxs draft publish <id>` — no post exists yet.
#
# Requires `mxs` with the `draft` command group (@mx-space/cli >= 0.14).
# This script does not implement a fallback. If `mxs draft` is missing, follow
# the human fallback in references/publish-flow.md.
#
# Usage:
#   create-draft.sh <article.xml>
#   create-draft.sh <article.xml> --skill-id <id> [--skill-id <id> ...]
#   create-draft.sh <article.xml> --ai-gen '[0,8]'   # AI disclosure preset(s), default 2
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $(basename "$0") <article.xml> [--skill-id <id> ...]" >&2
  exit 2
fi

SRC="$1"
shift
[ -f "$SRC" ] || { echo "error: $SRC not found" >&2; exit 1; }

SKILL_IDS=()
AI_GEN=2
while [ $# -gt 0 ]; do
  case "$1" in
    --skill-id)
      [ $# -ge 2 ] || { echo "error: --skill-id requires a value" >&2; exit 2; }
      SKILL_IDS+=("$2")
      shift 2
      ;;
    --ai-gen)
      [ $# -ge 2 ] || { echo "error: --ai-gen requires a JSON value" >&2; exit 2; }
      AI_GEN="$2"
      shift 2
      ;;
    *)
      echo "error: unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

if [ "${#SKILL_IDS[@]}" -eq 0 ]; then
  META="{\"aiGen\":$AI_GEN}"
else
  command -v jq >/dev/null 2>&1 || {
    echo "error: jq is required when --skill-id is passed" >&2
    exit 1
  }
  META=$(printf '%s\n' "${SKILL_IDS[@]}" | jq -R . | jq -s --argjson aiGen "$AI_GEN" '{aiGen: $aiGen, skillIds: .}' -c)
fi

mxs draft create --file "$SRC" --meta "$META" --open --silent
