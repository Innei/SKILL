# /// script
# dependencies = ["google-genai", "Pillow", "python-dotenv"]
# ///
"""Multi-platform chibi banner generator.

Usage:
    uv run generate_banner.py <char_ref> <theme> <out_path> --platform <name>

Platforms:
    wechat   750x400  WeChat sticker detail-page banner
    twitter  1500x500 Twitter/X profile header (3:1, letterbox-aware crop)

Add a new platform by appending an entry to `PLATFORMS`. Each preset declares
target dimensions, the Gemini aspect_ratio used at generation time, and a
composition_hint appended to the prompt. The hint should tell Gemini where
subjects must sit RELATIVE TO THE SOURCE CANVAS Gemini generates, accounting
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
import io
import math
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

MODEL = "gemini-3.1-flash-image-preview"

ENV_CANDIDATES = [
    Path.home() / ".env",
    Path.home() / ".env.local",
    Path.cwd() / ".env",
    Path.cwd() / ".env.local",
]


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


def _load_env() -> None:
    for p in ENV_CANDIDATES:
        if p.exists():
            load_dotenv(p)


def _make_client() -> genai.Client:
    _load_env()
    if vkey := os.environ.get("VERTEX_AI_KEY"):
        return genai.Client(vertexai=True, api_key=vkey)
    if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in ("1", "true", "yes"):
        return genai.Client(
            vertexai=True,
            project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )
    key = (
        os.environ.get("GOOGLE_AI_STUDIO_API_KEY")
        or os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
    )
    if not key:
        raise EnvironmentError(
            "No API key. Set one of: VERTEX_AI_KEY, GOOGLE_AI_STUDIO_API_KEY, "
            "GEMINI_API_KEY, GOOGLE_API_KEY; or GOOGLE_GENAI_USE_VERTEXAI=true "
            "with GOOGLE_CLOUD_PROJECT/LOCATION."
        )
    return genai.Client(api_key=key)


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


def generate_banner(char_ref: Image.Image, theme: str, platform: Platform) -> Image.Image:
    client = _make_client()
    prompt = _build_prompt(theme, platform.composition_hint)
    cfg = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(aspect_ratio=platform.aspect_ratio),
    )
    for attempt in range(6):
        try:
            resp = client.models.generate_content(
                model=MODEL, contents=[prompt, char_ref], config=cfg
            )
        except Exception as exc:
            msg = str(exc)
            transient = any(s in msg for s in (
                "503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED",
                "ConnectError", "SSL", "EOF", "ConnectionError", "TimeoutError",
            ))
            if transient and attempt < 5:
                wait = 2 ** attempt * 5
                print(f"  [{attempt+1}/6] transient error, retry in {wait}s: {msg[:80]}")
                time.sleep(wait)
                continue
            raise

        for part in resp.parts or []:
            if img := part.as_image():
                data = getattr(img, "image_bytes", None)
                if data is None:
                    tmp = Path("/tmp/_banner_tmp.png")
                    img.save(tmp)
                    data = tmp.read_bytes()
                    tmp.unlink(missing_ok=True)
                raw = Image.open(io.BytesIO(data)).convert("RGB")
                return _fit_crop(raw, platform.width, platform.height)

        finish = [getattr(c, "finish_reason", None) for c in (getattr(resp, "candidates", None) or [])]
        print(f"  [{attempt+1}/6] no image; finish={finish}")
        time.sleep(3)

    raise RuntimeError("banner generation failed after 6 attempts")


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
    ns = parser.parse_args()

    platform = PLATFORMS[ns.platform]
    char_ref = Image.open(ns.char_ref).convert("RGB")
    print(f"platform   : {ns.platform} {platform.width}x{platform.height} ar={platform.aspect_ratio}")
    print(f"char ref   : {ns.char_ref.name} {char_ref.size}")
    print(f"theme      : {ns.theme}")
    banner = generate_banner(char_ref, ns.theme, platform)
    banner.save(ns.out_path, "PNG")
    print(f"saved      : {ns.out_path} {banner.size}")


if __name__ == "__main__":
    main()
