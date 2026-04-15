---
name: gemini-image-generation
description: Use when a task requires Gemini text-to-image or image-to-image generation, including style transfer, character consistency, reference-image workflows, and watermark removal from Gemini-sourced images.
---

# Gemini Image Generation

## Overview

Generate and edit images with Gemini 3 native image models (Nano Banana). Supports text-to-image and image-to-image (reference-based) generation.

Core rules:

1. Describe style with precise visual vocabulary; do not rely on Gemini for exact text or typography in generated images.
2. Lock what must stay; describe what must change. Be specific but **concise** — overlong prompts trigger `MALFORMED_FUNCTION_CALL`.
3. For image-to-image, the model inherits the source image's watermarks. **Remove watermarks via prompt instructions, not by pre-patching the source.**

## When to Use

- Generate images from text prompts.
- Transfer or restyle a reference image while preserving its composition.
- Edit a single attribute of an existing image (outfit, lighting, background) while keeping character and pose identical.
- Maintain character consistency across multiple generated images by feeding prior outputs back as references.

Do not use this skill when:

- The output requires exact rendered text inside the image.
- The task is only cropping, resizing, or compressing existing assets.
- The source contains material that should not be sent to a third-party API.

## Prerequisites

- `GOOGLE_AI_STUDIO_API_KEY` (or `GEMINI_API_KEY`) in `.env.local` or `.env`.
- Python with `google-genai`, `Pillow`, `python-dotenv`. With `uv`, declare deps inline at the top of the script:

  ```python
  # /// script
  # dependencies = ["google-genai", "Pillow", "python-dotenv"]
  # ///
  ```

- Default model: `gemini-3.1-flash-image-preview`.

## Model Capabilities

| Model | Object refs (high-fidelity) | Character refs | Max total refs |
| --- | --- | --- | --- |
| `gemini-3.1-flash-image-preview` | Up to 10 | Up to 4 | 14 |
| `gemini-3-pro-image-preview` | Up to 6 | Up to 5 | 14 |

## Text-to-Image

```python
from google import genai
from google.genai import types

client = genai.Client()
resp = client.models.generate_content(
    model="gemini-3.1-flash-image-preview",
    contents=["A serene mountain landscape at dawn, watercolor style."],
    config=types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(aspect_ratio="16:9", image_size="2K"),
    ),
)
for part in resp.parts:
    if image := part.as_image():
        image.save("output.png")
```

## Image-to-Image (Reference-Based Edit)

Pass the source image alongside a prompt that locks composition and describes only the targeted change.

```python
from google import genai
from google.genai import types
from PIL import Image

client = genai.Client()
src = Image.open("source.png")

prompt = (
    "Redraw this image keeping the pose, composition, character, hair, face, "
    "expression, and the background absolutely identical. "
    "Preserve the original anime illustration style. "
    "Change ONLY the outfit to: a pure white short-sleeve linen dress, "
    "completely plain, no print, knee-length."
)

resp = client.models.generate_content(
    model="gemini-3.1-flash-image-preview",
    contents=[prompt, src],
    config=types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(aspect_ratio="1:1", image_size="1K"),
    ),
)
for part in resp.parts:
    if image := part.as_image():
        image.save("edited.png")
```

## Prompting Rules

1. **Lock first, change second.** Open with what must stay identical (pose, composition, character, background, art style), then state the single change.
2. **Use concrete visual mechanics** — linework weight, shadow depth, color palette, fabric type, cel-shaded vs painterly — instead of vague style words.
3. **Stay concise.** Long, multi-clause `IMPORTANT: must NOT ...` paragraphs reliably trigger `MALFORMED_FUNCTION_CALL` on Gemini 3 image models. Prefer one short positive instruction over an exhaustive list of negatives.
4. **One reference image per call** unless the task explicitly requires mixing — multiple refs cause content blending.
5. **Character consistency across turns:** feed previously generated images back into subsequent prompts as references.

## Removing Source Watermarks (Gemini Sparkle)

Images generated via Google AI Studio carry a small white four-point sparkle ✦ logo (typically bottom-right corner). In image-to-image, the model preserves the source background — **including this watermark**.

### Wrong approach: pre-patching the source

Pasting clean pixels over the watermark area in PIL:

```python
# ANTI-PATTERN — do not do this for watermark removal
patch = im.crop((50, 1820, 450, 2048)).transpose(Image.FLIP_LEFT_RIGHT)
im.paste(patch, (1648, 1820, 2048, 2048))
```

Why it fails:

- The hard seam is detectable to the model and breaks continuity.
- For some prompts the model rejects the modified input with `FinishReason.MALFORMED_FUNCTION_CALL` and never emits an image.
- AI-fill / outpaint over the patch shows the same instability.

### Correct approach: instruct the model to remove it

Keep the original image as input; add one short clause to the prompt:

```text
Also remove the small white four-point sparkle / star icon on the sand
in the bottom-right corner; repaint that area with the same clean
background so no icon, sparkle, logo, or watermark remains.
```

Be specific about **what** the icon is (white four-point sparkle / star, not "watermark") and **where** it sits (bottom-right corner, on the sand / sky / etc.). Vague "remove watermark" instructions are often ignored.

Note: the API output never adds a new visible watermark. Gemini still embeds a non-visible SynthID — that is expected and unrelated.

## Robust Call Pattern

Three transient failure modes occur regularly and must be handled:

| Symptom | Cause | Action |
| --- | --- | --- |
| `503 UNAVAILABLE` / `429 RESOURCE_EXHAUSTED` | Server load | Exponential back-off, 5–6 retries |
| `FinishReason.MALFORMED_FUNCTION_CALL` | Prompt or input confuses internal tool routing | Retry; if persistent, shorten/simplify the prompt and remove negative-list clauses |
| `resp.parts` is `None`, only text returned | Model decided to "describe" instead of render | Retry; tighten the lock clause |

`resp.text` may also be `None` — guard before slicing.

```python
for attempt in range(6):
    try:
        resp = client.models.generate_content(model=MODEL, contents=[prompt, src], config=cfg)
    except Exception as e:
        msg = str(e)
        if any(s in msg for s in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")) and attempt < 5:
            time.sleep(2 ** attempt * 5)
            continue
        raise

    parts = resp.parts or []
    for part in parts:
        if img := part.as_image():
            img.save(out_path)
            break
    else:
        cands = getattr(resp, "candidates", None) or []
        finish = [getattr(c, "finish_reason", None) for c in cands]
        txt = (getattr(resp, "text", None) or "")[:120]
        print(f"no image (attempt {attempt+1}); finish={finish} text={txt}")
        time.sleep(3)
        continue
    break
```

## Loading the API Key

```python
import os
from dotenv import load_dotenv
load_dotenv("/path/to/.env")  # or default cwd .env / .env.local
key = os.environ.get("GOOGLE_AI_STUDIO_API_KEY") or os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=key)
```

Never read a `.env` file by hand to print the key — load it into the environment via `python-dotenv` and reference the variable.

## Output Configuration

| Parameter | Supported values |
| --- | --- |
| `aspect_ratio` | `1:1`, `1:4`, `1:8`, `2:3`, `3:2`, `3:4`, `4:1`, `4:3`, `4:5`, `5:4`, `8:1`, `9:16`, `16:9`, `21:9` |
| `image_size` | `512`, `1K`, `2K`, `4K` |

`1K` is sufficient for most preview / iteration work; reserve `2K`/`4K` for finals.

## Verification

Before claiming completion:

- Confirm the API key loaded and at least one image part returned.
- Open each generated image to verify composition, character identity, and the targeted change.
- Inspect the bottom-right corner to confirm the sparkle is gone (when sourcing from a Gemini-generated image).
- If style drifted, tighten the lock clause and re-run; do not patch the source.
