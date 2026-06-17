#!/usr/bin/env bash
# Push a SKILL.md to the mx-space backend as a snippet of type=skill.
# Idempotent: if a snippet already exists at reference=skill, name=<frontmatter
# name>, this updates it; otherwise it creates one. Emits ONLY the snowflake id
# on stdout (suitable for command substitution).
#
# Requires `mxs` ≥ the version that supports `--type skill` (SNIPPET_TYPES
# list in packages/cli/src/cli/snippet/_flags.ts).
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

extract_id() {
  jq -r '(.data.data.id // .data.id // .id) // empty'
}

if EXISTING=$(mxs snippet get "skill/$NAME" --json 2>/dev/null); then
  ID=$(printf '%s' "$EXISTING" | extract_id)
  if [ -z "$ID" ]; then
    echo "error: existing snippet at skill/$NAME has no id" >&2
    exit 1
  fi
  mxs snippet update "$ID" --file "$SRC" --json >/dev/null
else
  RESPONSE=$(mxs snippet create --name "$NAME" --type skill --file "$SRC" --json)
  ID=$(printf '%s' "$RESPONSE" | extract_id)
fi

if [ -z "$ID" ]; then
  echo "error: failed to capture skill id" >&2
  exit 1
fi

printf '%s\n' "$ID"
