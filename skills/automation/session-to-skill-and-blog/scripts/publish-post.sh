#!/usr/bin/env bash
# Create a draft post on mx-space from a LiteXML envelope, mark it as
# AI-written (aiGen=2), open the admin edit page for Innei to preview,
# and silence the full server response. Does NOT publish — run
# `mxs post publish <slug>` after Innei approves.
#
# Usage: publish-post.sh <article.xml>
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "usage: $(basename "$0") <article.xml>" >&2
  exit 2
fi

SRC="$1"
[ -f "$SRC" ] || { echo "error: $SRC not found" >&2; exit 1; }

mxs post create --file "$SRC" --meta '{"aiGen":2}' --open --silent
