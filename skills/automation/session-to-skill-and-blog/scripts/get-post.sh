#!/usr/bin/env bash
# Round-trip step 1: fetch an existing post as XML so it can be edited
# locally. Prints to stdout.
#
# Usage: get-post.sh <slug> > /tmp/blog/article.xml
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "usage: $(basename "$0") <slug>" >&2
  exit 2
fi

mxs post get "$1" --output xml
