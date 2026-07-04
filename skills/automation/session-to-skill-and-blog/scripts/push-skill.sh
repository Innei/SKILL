#!/usr/bin/env bash
# Push a SKILL.md to the mx-space backend as a snippet of type=skill.
# Idempotent: `mxs snippet put` upserts by path, so re-runs update the
# existing snippet at sk/<frontmatter-name>/SKILL.md. Emits ONLY the
# snowflake id on stdout (suitable for command substitution).
#
# The canonical snippet path root for skills is `sk/` — the backend
# normalizes skill-type snippets to it and the Yohaku web /skills/<name>
# pages read from `/s/sk/<name>/...`.
#
# Usage: push-skill.sh <SKILL.md>
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "usage: $(basename "$0") <SKILL.md>" >&2
  exit 2
fi

SRC="$1"
[ -f "$SRC" ] || { echo "error: $SRC not found" >&2; exit 1; }

command -v jq >/dev/null 2>&1 || {
  echo "error: jq is required" >&2
  exit 1
}

NAME=$(awk '
  BEGIN { in_fm = 0 }
  /^---[[:space:]]*$/ {
    if (in_fm == 0) { in_fm = 1; next }
    else { exit }
  }
  in_fm && $1 == "name:" {
    sub(/^name:[[:space:]]*/, "")
    gsub(/^"|"$/, "")
    gsub(/^'\''|'\''$/, "")
    print
    exit
  }
' "$SRC")

if [ -z "$NAME" ]; then
  echo "error: no \`name:\` in frontmatter of $SRC" >&2
  exit 1
fi

REMOTE="sk/$NAME/SKILL.md"

extract_id() {
  jq -r '(.data.data.id // .data.id // .id) // empty'
}

RESPONSE=$(mxs snippet put "$REMOTE" --type skill --file "$SRC" --json)
ID=$(printf '%s' "$RESPONSE" | extract_id)

if [ -z "$ID" ]; then
  ID=$(mxs snippet get "$REMOTE" --json | extract_id)
fi

if [ -z "$ID" ]; then
  echo "error: failed to capture skill id" >&2
  exit 1
fi

printf '%s\n' "$ID"
