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

# Strip <state> before updating: envelopes are reused from create (where
# <state>draft</state> is the norm), and sending it would flip an already
# published post back to draft, making it vanish for readers. Publish state
# changes go through `mxs post publish|unpublish` only. (Newer mxs ignores
# envelope state on update, but the installed binary may predate that guard.)
SAFE="$(mktemp "${TMPDIR:-/tmp}/mxs-update.XXXXXX")"
trap 'rm -f "$SAFE"' EXIT
sed '/<state>[^<]*<\/state>/d' "$SRC" > "$SAFE"

mxs post update "$SLUG" --file "$SAFE" --open --silent
