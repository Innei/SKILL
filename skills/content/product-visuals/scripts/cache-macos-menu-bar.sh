#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <MenuBar.svg>" >&2
  exit 2
fi

source_svg="$1"
if [[ ! -f "$source_svg" ]]; then
  echo "Menu Bar SVG not found: $source_svg" >&2
  exit 1
fi

if grep -Eiq '<text([[:space:]>])' "$source_svg"; then
  echo "Menu Bar SVG still contains live text; export outlined vectors from Figma" >&2
  exit 1
fi

if ! command -v magick >/dev/null 2>&1; then
  echo "ImageMagick is required to rasterize the official SVG: brew install imagemagick" >&2
  exit 1
fi

cache_dir="${HOME}/.cache/product-visuals/macos-ui"
cached_svg="${cache_dir}/macos-27-menu-bar.svg"
cached_png="${cache_dir}/macos-27-menu-bar.png"

mkdir -p "$cache_dir"
cp "$source_svg" "$cached_svg"
magick -background none -density 192 "$cached_svg" -resize 3022x68 "$cached_png"

echo "$cached_png"
