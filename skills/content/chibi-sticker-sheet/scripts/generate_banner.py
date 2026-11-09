# /// script
# dependencies = ["google-genai", "Pillow", "python-dotenv"]
# ///
"""Multi-platform chibi banner generator.

Usage:
    uv run generate_banner.py <char_ref> <theme> <out_path> --platform <name> [--provider codex|gemini]

Platforms:
    wechat   750x400  WeChat sticker detail-page banner
    twitter  1500x500 Twitter/X profile header (3:1, letterbox-aware crop)

Add a new platform by appending an entry to `PLATFORMS`. Each preset declares
target dimensions, the source aspect_ratio used at generation time, and a
composition_hint appended to the prompt. The hint tells the image model where
subjects must sit RELATIVE TO THE SOURCE CANVAS it generates, accounting
for the post-crop region the user will actually see.

Letterbox lesson (Twitter, ratios more extreme than ~16:9):
    Gemini only supports a fixed aspect-ratio menu (1:1, 4:3, 3:4, 16:9,
    9:16). For 3:1 we generate at 16:9 and center-crop the middle 56% of
    the canvas height. Telling Gemini to "fill the canvas vertically" then
    clips heads/feet. Tell it instead that the top/bottom 22% are off-screen
    letterbox bars, and place subjects in the middle 25-75% band — the
    subjects then fill the visible final frame with a small safety margin.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

from generate import generate_image
from PIL import Image


@dataclass(frozen=True)
class Platform:
    width: int
    height: int
    aspect_ratio: str
    composition_hint: str


PLATFORMS: dict[str, Platform] = {
    "wechat": Platform(
        width=750,
        height=400,
        aspect_ratio="16:9",
        composition_hint="",
    ),
    "twitter": Platform(
        width=1500,
        height=500,
        aspect_ratio="16:9",
        composition_hint=(
            "Frame model: treat the top 22 percent and the bottom 22 percent of this 16:9 canvas "
            "as off-screen letterbox overflow that will be discarded. The visible final frame is only "
            "the middle 56 percent of canvas height. "
            "Composition inside the source canvas: top of every chibi's hair must sit at approximately "
            "25 percent from the canvas top (NOT at 5 percent, NOT touching the top edge). Bottom of every "
            "chibi's feet must sit at approximately 75 percent from the canvas top. The three chibis fill "
            "this central 25-to-75 percent vertical band tightly. The top 22 percent of canvas shows only "
            "background overflow (rainy sky, hanging wind chimes peeking in from above, drifting petals, "
            "tree canopy). The bottom 22 percent of canvas shows only background overflow (hydrangea bushes, "
            "wet ground reflection, scattered petals). Spread the three chibis evenly across the horizontal "
            "width. Leave the lower-left of the visible frame (about 18 percent of width, circular area) "
            "visually calm, using mostly background scenery, so a profile avatar overlay does not collide "
            "with faces."
        ),
    ),
}


def _fit_crop(img: Image.Image, w: int, h: int) -> Image.Image:
    src_w, src_h = img.size
    scale = max(w / src_w, h / src_h)
    nw = max(w, math.ceil(src_w * scale))
    nh = max(h, math.ceil(src_h * scale))
    img = img.resize((nw, nh), Image.LANCZOS)
    x, y = (nw - w) // 2, (nh - h) // 2
    return img.crop((x, y, x + w, y + h))


def _build_prompt(theme: str, composition_hint: str) -> str:
    base = (
        f"Generate a wide horizontal banner image featuring 3 chibi versions of this character "
        f"in a {theme} themed scene, each showing a different fun expression and pose. "
        f"Background: colorful vivid pastel tones with {theme} decorative elements — "
        f"NOT white, NOT transparent. "
        f"Art style: LINE/WeChat sticker chibi, extreme super-deformed 2-head body ratio, "
        f"thick bold black ink outline, flat cel shading, mochi chibi aesthetic. "
        f"No text, no captions. Rich storytelling wide cinematic composition."
    )
    if composition_hint:
        return f"{base} {composition_hint}"
    return base


def generate_banner(
    char_ref: Image.Image, theme: str, platform: Platform, *, provider: str = "codex",
) -> Image.Image:
    prompt = _build_prompt(theme, platform.composition_hint)
    raw = generate_image(
        prompt, char_ref, provider=provider, aspect_ratio=platform.aspect_ratio,
    )
    return _fit_crop(raw, platform.width, platform.height)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a chibi banner for a target platform.",
    )
    parser.add_argument("char_ref", type=Path)
    parser.add_argument("theme", type=str)
    parser.add_argument("out_path", type=Path)
    parser.add_argument(
        "--platform",
        choices=sorted(PLATFORMS.keys()),
        required=True,
    )
    parser.add_argument("--provider", choices=("codex", "gemini"), default="codex", help="Image provider (default: codex)")
    ns = parser.parse_args()

    platform = PLATFORMS[ns.platform]
    char_ref = Image.open(ns.char_ref).convert("RGB")
    print(f"platform   : {ns.platform} {platform.width}x{platform.height} ar={platform.aspect_ratio}")
    print(f"char ref   : {ns.char_ref.name} {char_ref.size}")
    print(f"theme      : {ns.theme}")
    print(f"provider   : {ns.provider}")
    banner = generate_banner(char_ref, ns.theme, platform, provider=ns.provider)
    ns.out_path.parent.mkdir(parents=True, exist_ok=True)
    banner.save(ns.out_path, "PNG")
    print(f"saved      : {ns.out_path} {banner.size}")


if __name__ == "__main__":
    main()
