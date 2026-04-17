# /// script
# dependencies = ["google-genai", "Pillow", "python-dotenv"]
# ///
"""Generate WeChat sticker submission extras: banner, cover, icon.

Usage:
    uv run generate_extras.py <sticker_dir> <char_ref_image> <theme_hint>

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

import io
import os
import sys
import time
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


def _load_api_key() -> str:
    for p in ENV_CANDIDATES:
        if p.exists():
            load_dotenv(p)
    key = os.environ.get("GOOGLE_AI_STUDIO_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise EnvironmentError(
            "Set GOOGLE_AI_STUDIO_API_KEY or GEMINI_API_KEY in your environment or .env"
        )
    return key


def _fit_crop(img: Image.Image, w: int, h: int) -> Image.Image:
    """Scale-to-fill then center-crop to exact (w, h)."""
    src_w, src_h = img.size
    scale = max(w / src_w, h / src_h)
    nw, nh = int(src_w * scale), int(src_h * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    x, y = (nw - w) // 2, (nh - h) // 2
    return img.crop((x, y, x + w, y + h))


def generate_banner(char_ref: Image.Image, theme: str) -> Image.Image:
    """Call Gemini to produce a 750×400 banner; retry on transient errors."""
    client = genai.Client(api_key=_load_api_key())
    prompt = (
        f"Generate a wide horizontal banner image featuring 3 chibi versions of this character "
        f"in a {theme} themed scene, each showing a different fun expression and pose. "
        f"Background: colorful vivid pastel tones with {theme} decorative elements — "
        f"NOT white, NOT transparent. "
        f"Art style: LINE/WeChat sticker chibi, extreme super-deformed 2-head body ratio, "
        f"thick bold black ink outline, flat cel shading, mochi chibi aesthetic. "
        f"No text, no captions. Rich storytelling wide cinematic composition."
    )
    cfg = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(aspect_ratio="16:9"),
    )
    for attempt in range(6):
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=[prompt, char_ref],
                config=cfg,
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
                return _fit_crop(raw, 750, 400)

        finish = [getattr(c, "finish_reason", None) for c in (getattr(resp, "candidates", None) or [])]
        print(f"  [{attempt+1}/6] no image; finish={finish}")
        time.sleep(3)

    raise RuntimeError("banner generation failed after 6 attempts")


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
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    sticker_dir = Path(sys.argv[1])
    char_ref_path = Path(sys.argv[2])
    theme = sys.argv[3]

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

    print("generating banner via Gemini...")
    banner = generate_banner(char_ref, theme)
    banner_path = sticker_dir / "banner.png"
    banner.save(banner_path, "PNG")
    print(f"saved banner: {banner_path} {banner.size}")


if __name__ == "__main__":
    main()
