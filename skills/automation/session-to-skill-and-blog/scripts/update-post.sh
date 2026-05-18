#!/usr/bin/env bash
# Round-trip step 2: PATCH an existing post from an edited XML file.
# Opens the admin edit page after success; silences the response body.
#
# Usage: update-post.sh <slug> <article.xml>
set -euo pipefail

if [ $# -ne 2 ]; then
  echo "usage: $(basename "$0") <slug> <article.xml>" >&2
  exit 2
fi

SLUG="$1"
SRC="$2"
[ -f "$SRC" ] || { echo "error: $SRC not found" >&2; exit 1; }

mxs post update "$SLUG" --file "$SRC" --open --silent
