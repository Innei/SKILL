# /// script
# dependencies = ["google-genai", "Pillow", "python-dotenv"]
# ///
"""Generate a chibi sticker sheet via Gemini image-to-image.

Usage:
    uv run generate.py <char_ref_image> <prompt_file> [output.png] [--anchor style_anchor.png]

    char_ref_image  : character reference PNG/JPEG
    prompt_file     : plain-text file containing the full generation prompt
    output.png      : destination (default: sheet_white.png next to char_ref)
    --anchor        : optional style-anchor image (e.g. sheet_white_a.png for Call B)

Environment (any one auth path):
    GOOGLE_AI_STUDIO_API_KEY | GEMINI_API_KEY | GOOGLE_API_KEY          (AI Studio)
    VERTEX_AI_KEY                                                       (Vertex Express)
    GOOGLE_GENAI_USE_VERTEXAI=true + GOOGLE_CLOUD_PROJECT/LOCATION       (Vertex ADC)

See SKILL.md for prompt structure guidelines.
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

# Search these paths for an .env file
ENV_CANDIDATES = [
    Path.home() / ".env",
    Path.home() / ".env.local",
    Path.cwd() / ".env",
    Path.cwd() / ".env.local",
]


def _load_env() -> None:
    for p in ENV_CANDIDATES:
        if p.exists():
            load_dotenv(p)


def _is_vertex() -> bool:
    return bool(os.environ.get("VERTEX_AI_KEY")) or os.environ.get(
        "GOOGLE_GENAI_USE_VERTEXAI", ""
    ).lower() in ("1", "true", "yes")


def _make_client() -> genai.Client:
    """Resolve auth: Vertex Express → Vertex ADC → AI Studio."""
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


def _image_config(aspect_ratio: str, image_size: str) -> types.ImageConfig:
    """Vertex does NOT accept image_size — drop it there."""
    if _is_vertex():
        return types.ImageConfig(aspect_ratio=aspect_ratio)
    return types.ImageConfig(aspect_ratio=aspect_ratio, image_size=image_size)


def generate_sheet(prompt: str, char_ref: Image.Image, anchor: Image.Image | None = None) -> Image.Image:
    """Call Gemini with retry; return PIL Image.

    anchor: optional style-anchor image (e.g. sheet_white_a.png for Call B cross-sheet consistency).
    """
    client = _make_client()
    cfg = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=_image_config(aspect_ratio="1:1", image_size="2K"),
    )
    contents = [char_ref]
    if anchor is not None:
        contents.append(anchor)
    contents.append(prompt)
    for attempt in range(6):
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=cfg,
            )
        except Exception as exc:
            msg = str(exc)
            if any(s in msg for s in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "ConnectError", "SSL", "EOF", "ConnectionReset", "timeout", "RemoteProtocol", "disconnected", "ConnectionError")) and attempt < 5:
                wait = 2 ** attempt * 5
                print(f"  [{attempt+1}/6] transient error, retry in {wait}s: {msg[:80]}")
                time.sleep(wait)
                continue
            raise

        for part in resp.parts or []:
            if img := part.as_image():
                data = getattr(img, "image_bytes", None)
                if data is None:
                    tmp = Path("/tmp/_gemini_tmp.png")
                    img.save(tmp)
                    data = tmp.read_bytes()
                    tmp.unlink(missing_ok=True)
                return Image.open(io.BytesIO(data)).convert("RGB")

        cands = getattr(resp, "candidates", None) or []
        finish = [getattr(c, "finish_reason", None) for c in cands]
        txt = (getattr(resp, "text", None) or "")[:120]
        print(f"  [{attempt+1}/6] no image; finish={finish} text={txt!r}")
        time.sleep(3)

    raise RuntimeError("generation failed after 6 attempts")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate a chibi sticker sheet via Gemini.")
    parser.add_argument("char_ref", help="Character reference image path")
    parser.add_argument("prompt_file", help="Plain-text prompt file")
    parser.add_argument("output", nargs="?", default=None, help="Output PNG path")
    parser.add_argument("--anchor", default=None, help="Style anchor image (for Call B cross-sheet consistency)")
    args = parser.parse_args()

    char_ref_path = Path(args.char_ref)
    prompt_path = Path(args.prompt_file)
    out_path = Path(args.output) if args.output else char_ref_path.parent / "sheet_white.png"

    char_ref = Image.open(char_ref_path)
    anchor = Image.open(args.anchor) if args.anchor else None
    prompt = prompt_path.read_text(encoding="utf-8").strip()

    print(f"character ref : {char_ref_path.name} {char_ref.size}")
    if anchor:
        print(f"style anchor  : {args.anchor}")
    print(f"prompt        : {len(prompt)} chars, first line: {prompt.splitlines()[0][:80]}")
    print(f"output        : {out_path}")
    print("generating...")

    sheet = generate_sheet(prompt, char_ref, anchor=anchor)
    sheet.save(out_path)
    print(f"saved {out_path} {sheet.size}")


if __name__ == "__main__":
    main()
