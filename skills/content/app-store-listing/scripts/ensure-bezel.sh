#!/usr/bin/env bash
set -euo pipefail

URL="${APP_STORE_BEZEL_URL:-https://devimages-cdn.apple.com/design/resources/download/Bezel-iPhone-17.dmg}"
CACHE="${APP_STORE_BEZEL_CACHE:-$HOME/.cache/app-store-listing}"
SRC_NAME="${APP_STORE_BEZEL_SRC:-PNG/iPhone 17/iPhone 17 - Black - Portrait.png}"
OUT="${1:-$CACHE/iphone17-black.png}"

if [ -f "$OUT" ]; then
  echo "$OUT"
  exit 0
fi

mkdir -p "$CACHE" "$(dirname "$OUT")"
DMG="$CACHE/Bezel-iPhone-17.dmg"
if [ ! -f "$DMG" ]; then
  curl -fL --retry 3 -o "$DMG" "$URL"
fi

# Apple's DMG shows an EULA; a single Y is required to attach.
MOUNT="$(mktemp -d)"
printf 'Y\n' | hdiutil attach "$DMG" -nobrowse -readonly -mountpoint "$MOUNT" >/dev/null
trap 'hdiutil detach "$MOUNT" >/dev/null 2>&1 || true' EXIT
cp "$MOUNT/$SRC_NAME" "$OUT"
echo "$OUT"
