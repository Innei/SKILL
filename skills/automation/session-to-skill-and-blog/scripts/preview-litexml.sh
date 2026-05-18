#!/usr/bin/env bash
# Render a LiteXML article to HTML via @haklex/rich-litexml-cli and open it.
#
# Usage: preview-litexml.sh <article.xml> [title] [lang]
#   defaults: title=Preview, lang=zh
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $(basename "$0") <article.xml> [title] [lang]" >&2
  exit 2
fi

SRC="$1"
TITLE="${2:-Preview}"
LANG_TAG="${3:-zh}"
OUT="${SRC%.xml}.html"

npx -y @haklex/rich-litexml-cli@latest "$SRC" \
  --format html --variant article --theme light \
  --title "$TITLE" --lang "$LANG_TAG" -o "$OUT"

case "$(uname -s)" in
  Darwin) open "$OUT" ;;
  Linux)  command -v xdg-open >/dev/null && xdg-open "$OUT" || echo "preview: $OUT" ;;
  *)      echo "preview: $OUT" ;;
esac
