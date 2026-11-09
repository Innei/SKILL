# /// script
# dependencies = ["google-genai", "Pillow", "python-dotenv"]
# ///
"""Generate WeChat sticker submission extras: banner, cover, icon.

Usage:
    uv run generate_extras.py <sticker_dir> <char_ref_image> <theme_hint> [--provider codex|gemini]

    sticker_dir    : directory that already contains cells/*.png
    char_ref_image : original character reference PNG used for sticker generation
    theme_hint     : short English theme for banner scene, e.g. "autumn ginkgo forest"

Outputs written into sticker_dir:
    banner.png   750×400 PNG, colorful background (WeChat detail-page banner)
    cover.png    240×240 transparent PNG (album cover)
    icon.png      50×50 transparent PNG (chat-page icon)

WeChat requirements recap:
    banner : JPG/PNG 750×400, >500 KB compressed; colorful bg, no white, no text
    cover  : PNG 240×240, transparent bg, half/full body, no white outline
    icon   : PNG  50×50, transparent bg, head shot, no hard square border
"""

from __future__ import annotations

import argparse
from pathlib import Path

from generate_banner import PLATFORMS
from generate_banner import generate_banner as _gen_banner
from PIL import Image


def generate_banner(char_ref: Image.Image, theme: str, *, provider: str = "codex") -> Image.Image:
    return _gen_banner(char_ref, theme, PLATFORMS["wechat"], provider=provider)


def make_cover(cell: Image.Image) -> Image.Image:
    """Resize a transparent sticker cell to 240×240."""
    return cell.resize((240, 240), Image.LANCZOS)


def make_icon(cell: Image.Image) -> Image.Image:
    """Resize the full transparent sticker cell to 50×50 (no crop)."""
    return cell.resize((50, 50), Image.LANCZOS)


def _pick_cover_cell(cells_dir: Path) -> Path:
    """Pick a recognisable cell for cover/icon.

    Priority: thumbs_up_wink.png > 07.png > first cell alphabetically.
    """
    for name in ("thumbs_up_wink.png", "07.png"):
        candidate = cells_dir / name
        if candidate.exists():
            return candidate
    candidates = sorted(cells_dir.glob("*.png"))
    if not candidates:
        raise FileNotFoundError(f"No cells found in {cells_dir}")
    return candidates[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate WeChat banner, cover and icon.")
    parser.add_argument("sticker_dir", type=Path)
    parser.add_argument("char_ref", type=Path)
    parser.add_argument("theme_hint")
    parser.add_argument("--provider", choices=("codex", "gemini"), default="codex", help="Image provider (default: codex)")
    args = parser.parse_args()
    sticker_dir = args.sticker_dir
    char_ref_path = args.char_ref
    theme = args.theme_hint

    cells_dir = sticker_dir / "cells"
    cover_cell_path = _pick_cover_cell(cells_dir)

    cell_img = Image.open(cover_cell_path).convert("RGBA")
    char_ref = Image.open(char_ref_path)

    print(f"sticker dir : {sticker_dir}")
    print(f"char ref    : {char_ref_path.name} {char_ref.size}")
    print(f"theme       : {theme}")
    print(f"cover cell  : {cover_cell_path.name}")

    cover = make_cover(cell_img)
    cover_path = sticker_dir / "cover.png"
    cover.save(cover_path, "PNG")
    print(f"saved cover : {cover_path} {cover.size}")

    icon = make_icon(cell_img)
    icon_path = sticker_dir / "icon.png"
    icon.save(icon_path, "PNG")
    print(f"saved icon  : {icon_path} {icon.size}")

    print(f"generating banner via {args.provider}...")
    banner = generate_banner(char_ref, theme, provider=args.provider)
    banner_path = sticker_dir / "banner.png"
    banner.save(banner_path, "PNG")
    print(f"saved banner: {banner_path} {banner.size}")


if __name__ == "__main__":
    main()
