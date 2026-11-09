# /// script
# dependencies = ["google-genai", "Pillow", "python-dotenv"]
# ///
"""Generate a chibi sticker sheet via Codex CLI (default) or Gemini.

Usage:
    uv run generate.py <char_ref_image> <prompt_file> [output.png] [--anchor style_anchor.png] [--provider codex|gemini]

    char_ref_image  : character reference PNG/JPEG
    prompt_file     : plain-text file containing the full generation prompt
    output.png      : destination (default: sheet_white.png next to char_ref)
    --anchor        : optional style-anchor image (e.g. sheet_white_a.png for Call B)

Codex: install Codex CLI, run `codex login`, and enable native image generation.
Gemini environment (only with --provider gemini; any one auth path):
    GOOGLE_AI_STUDIO_API_KEY | GEMINI_API_KEY | GOOGLE_API_KEY          (AI Studio)
    VERTEX_AI_KEY                                                       (Vertex Express)
    GOOGLE_GENAI_USE_VERTEXAI=true + GOOGLE_CLOUD_PROJECT/LOCATION       (Vertex ADC)

See SKILL.md for prompt structure guidelines.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from google import genai
    from google.genai import types

MODEL = "gemini-3.1-flash-image-preview"

# Search these paths for an .env file
ENV_CANDIDATES = [
    Path.home() / ".env",
    Path.home() / ".env.local",
    Path.cwd() / ".env",
    Path.cwd() / ".env.local",
]


def _load_env() -> None:
    from dotenv import load_dotenv

    for p in ENV_CANDIDATES:
        if p.exists():
            load_dotenv(p)


def _is_vertex() -> bool:
    return bool(os.environ.get("VERTEX_AI_KEY")) or os.environ.get(
        "GOOGLE_GENAI_USE_VERTEXAI", ""
    ).lower() in ("1", "true", "yes")


def _make_client() -> genai.Client:
    """Resolve auth: Vertex Express → Vertex ADC → AI Studio."""
    from google import genai

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
        raise OSError(
            "No API key. Set one of: VERTEX_AI_KEY, GOOGLE_AI_STUDIO_API_KEY, "
            "GEMINI_API_KEY, GOOGLE_API_KEY; or GOOGLE_GENAI_USE_VERTEXAI=true "
            "with GOOGLE_CLOUD_PROJECT/LOCATION."
        )
    return genai.Client(api_key=key)


def _image_config(aspect_ratio: str, image_size: str | None) -> types.ImageConfig:
    """Vertex does NOT accept image_size — drop it there."""
    from google.genai import types

    if _is_vertex() or image_size is None:
        return types.ImageConfig(aspect_ratio=aspect_ratio)
    return types.ImageConfig(aspect_ratio=aspect_ratio, image_size=image_size)


def _generate_gemini(
    prompt: str, char_ref: Image.Image, anchor: Image.Image | None,
    aspect_ratio: str, image_size: str | None,
) -> Image.Image:
    """Call Gemini with retry; return a detached RGB image.

    anchor: optional style-anchor image (e.g. sheet_white_a.png for Call B cross-sheet consistency).
    """
    from google.genai import types

    client = _make_client()
    cfg = types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=_image_config(aspect_ratio=aspect_ratio, image_size=image_size),
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


def _generate_codex(
    prompt: str, char_ref: Image.Image, anchor: Image.Image | None, aspect_ratio: str,
) -> Image.Image:
    """Run native Codex image generation in an isolated writable workspace."""
    executable = shutil.which("codex")
    if executable is None:
        raise RuntimeError("Codex CLI not found. Install it and run `codex login`, or use --provider gemini.")

    with tempfile.TemporaryDirectory(prefix="chibi-codex-") as directory:
        workspace = Path(directory).resolve()
        reference = workspace / "character.png"
        char_ref.save(reference, "PNG")
        output = workspace / "generated.png"
        last_message = workspace / "result.txt"
        command = [
            executable, "--ask-for-approval", "never", "exec",
            "--sandbox", "workspace-write", "--skip-git-repo-check", "--ephemeral",
            "--enable", "image_generation", "--cd", str(workspace),
            "--image", str(reference),
        ]
        if anchor is not None:
            anchor_path = workspace / "style-anchor.png"
            anchor.save(anchor_path, "PNG")
            command.extend(["--image", str(anchor_path)])
        command.extend(["--output-last-message", str(last_message), "-"])
        instructions = (
            "$imagegen\nUse native image_generation to generate exactly one image. "
            "The first attached image defines the character identity. "
            + ("The second attached image is a style anchor; preserve its palette, shading and line weight. " if anchor is not None else "")
            + f"Request a {aspect_ratio} canvas.\n\n{prompt}\n\n"
            f"Save or copy the actual generated image as a PNG to {output}. "
            "Use the image generation tool, not programmatic drawing, SVG, or a text-only response. "
            "If native image generation is unavailable, stop and report the error. "
            "Do not call external image APIs or switch providers."
        )
        try:
            result = subprocess.run(
                command, input=instructions, text=True, capture_output=True,
                cwd=workspace, timeout=900, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Codex image generation timed out after 900 seconds.") from exc
        if result.returncode:
            detail = (result.stderr or result.stdout)[-4000:]
            raise RuntimeError(f"Codex CLI failed (exit {result.returncode}): {detail}")
        if not output.is_file():
            detail = last_message.read_text(encoding="utf-8") if last_message.exists() else result.stdout
            raise RuntimeError(f"Codex did not produce generated.png: {detail[-4000:]}")
        try:
            with Image.open(output) as image:
                return image.convert("RGB")
        except OSError as exc:
            raise RuntimeError("Codex produced an unreadable image.") from exc


def generate_image(
    prompt: str, char_ref: Image.Image, anchor: Image.Image | None = None, *,
    provider: str = "codex", aspect_ratio: str = "1:1", image_size: str | None = None,
) -> Image.Image:
    """Select one provider explicitly; failures never switch providers."""
    if provider == "codex":
        return _generate_codex(prompt, char_ref, anchor, aspect_ratio)
    if provider == "gemini":
        return _generate_gemini(prompt, char_ref, anchor, aspect_ratio, image_size)
    raise ValueError(f"Unknown image provider: {provider}")


def generate_sheet(
    prompt: str, char_ref: Image.Image, anchor: Image.Image | None = None, *,
    provider: str = "codex",
) -> Image.Image:
    return generate_image(prompt, char_ref, anchor, provider=provider, image_size="2K")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate a chibi sticker sheet via Codex CLI or Gemini.")
    parser.add_argument("char_ref", help="Character reference image path")
    parser.add_argument("prompt_file", help="Plain-text prompt file")
    parser.add_argument("output", nargs="?", default=None, help="Output PNG path")
    parser.add_argument("--anchor", default=None, help="Style anchor image (for Call B cross-sheet consistency)")
    parser.add_argument("--provider", choices=("codex", "gemini"), default="codex", help="Image provider (default: codex)")
    args = parser.parse_args()

    char_ref_path = Path(args.char_ref)
    prompt_path = Path(args.prompt_file)
    out_path = Path(args.output) if args.output else char_ref_path.parent / "sheet_white.png"

    char_ref = Image.open(char_ref_path)
    anchor = Image.open(args.anchor) if args.anchor else None
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    if not prompt:
        parser.error("Prompt file must not be empty")

    print(f"character ref : {char_ref_path.name} {char_ref.size}")
    if anchor:
        print(f"style anchor  : {args.anchor}")
    print(f"prompt        : {len(prompt)} chars, first line: {prompt.splitlines()[0][:80]}")
    print(f"output        : {out_path}")
    print(f"provider      : {args.provider}")
    print("generating...")

    sheet = generate_sheet(prompt, char_ref, anchor=anchor, provider=args.provider)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)
    print(f"saved {out_path} {sheet.size}")


if __name__ == "__main__":
    main()
