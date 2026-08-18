#!/usr/bin/env bash
set -euo pipefail

CACHE="${PRODUCT_VISUALS_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/product-visuals/bezels}"
mkdir -p "$CACHE"

IPHONE_URL="https://devimages-cdn.apple.com/design/resources/download/Bezel-iPhone-17.dmg"
MAC_URL="https://devimages-cdn.apple.com/design/resources/download/Bezel-MacBook-Pro-M5.dmg"

need_iphone=0
need_mac=0
[[ -f "$CACHE/iphone-17-pro-silver-portrait.png" ]] || need_iphone=1
[[ -f "$CACHE/macbook-pro-m5-14-space-black.png" ]] || need_mac=1

if [[ "$need_iphone" -eq 0 && "$need_mac" -eq 0 ]]; then
  echo "$CACHE"
  exit 0
fi

TMP="$(mktemp -d)"
IPHONE_VOL=""
MAC_VOL=""
trap '[[ -n "$IPHONE_VOL" ]] && hdiutil detach "$IPHONE_VOL" >/dev/null 2>&1 || true
      [[ -n "$MAC_VOL" ]] && hdiutil detach "$MAC_VOL" >/dev/null 2>&1 || true
      rm -rf "$TMP"' EXIT

attach() {
  local dmg="$1"
  printf 'Y\n' | hdiutil attach -nobrowse -readonly -noverify "$dmg" | awk '/\/Volumes\//{print $NF}'
}

if [[ "$need_iphone" -eq 1 ]]; then
  curl -fsSL -o "$TMP/iphone.dmg" "$IPHONE_URL"
  IPHONE_VOL="$(attach "$TMP/iphone.dmg")"
  cp "$IPHONE_VOL/PNG/iPhone 17 Pro/iPhone 17 Pro - Silver - Portrait.png" \
    "$CACHE/iphone-17-pro-silver-portrait.png"
  cp "$IPHONE_VOL/PNG/iPhone 17 Pro/iPhone 17 Pro - Deep Blue - Portrait.png" \
    "$CACHE/iphone-17-pro-deep-blue-portrait.png"
  cp "$IPHONE_VOL/PNG/iPhone 17 Pro/iPhone 17 Pro - Cosmic Orange - Portrait.png" \
    "$CACHE/iphone-17-pro-cosmic-orange-portrait.png"
  hdiutil detach "$IPHONE_VOL" >/dev/null
  IPHONE_VOL=""
fi

if [[ "$need_mac" -eq 1 ]]; then
  curl -fsSL -o "$TMP/mac.dmg" "$MAC_URL"
  MAC_VOL="$(attach "$TMP/mac.dmg")"
  cp "$MAC_VOL/PNG/MacBook Pro M5 14-inch Space Black.png" \
    "$CACHE/macbook-pro-m5-14-space-black.png"
  cp "$MAC_VOL/PNG/MacBook Pro M5 14-inch Silver.png" \
    "$CACHE/macbook-pro-m5-14-silver.png"
  hdiutil detach "$MAC_VOL" >/dev/null
  MAC_VOL=""
fi

echo "$CACHE"
