---
name: gemini-image-generation
description: Use when a task requires Gemini text-to-image or image-to-image generation, including style transfer, character consistency, and reference-image workflows.
---

# Gemini Image Generation

## Overview

Generate and edit images with Gemini 3 native image models (Nano Banana). Supports both text-to-image and image-to-image (reference-based) generation.

Core rule: **describe style with precise visual vocabulary; do not rely on Gemini for exact text or typography in generated images**.

## When to Use

- Generate images from text prompts.
- Transfer a reference image into a new style (image-to-image / style transfer).
- Maintain character consistency across multiple generated images.
- Use reference images for poses, objects, or stylistic guidance.

Do not use this skill when:

- The output requires exact rendered text inside the image.
- The task is only about cropping, resizing, or compressing existing local assets (no generation needed).
- The source image contains sensitive or copyrighted material that should not be sent to an external API.

## Prerequisites

- `GOOGLE_AI_STUDIO_API_KEY` in `.env.local` or `.env`.
- Python environment with `google-genai` and `Pillow` installed.
- Default model: `gemini-3.1-flash-image-preview`.

## Model Capabilities

| Model | Object refs (high-fidelity) | Character refs | Max total refs |
| --- | --- | --- | --- |
| `gemini-3.1-flash-image-preview` | Up to 10 | Up to 4 | 14 |
| `gemini-3-pro-image-preview` | Up to 6 | Up to 5 | 14 |

## Text-to-Image

Minimal request shape:

```python
from google import genai
from google.genai import types

client = genai.Client()
response = client.models.generate_content(
    model="gemini-3.1-flash-image-preview",
    contents=["A serene mountain landscape at dawn, watercolor style."],
    config=types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(
            aspect_ratio="16:9",
            image_size="2K"
        ),
    ),
)
for part in response.parts:
    if image := part.as_image():
        image.save("output.png")
```

## Image-to-Image (Style Transfer)

Pass the source image in `contents` alongside a prompt that explicitly describes the desired style change while locking the composition.

```python
from google import genai
from google.genai import types
from PIL import Image

client = genai.Client()
source = Image.open("source.png")

prompt = (
    "Redraw this image in exactly the same pose, composition, and subject. "
    "Change only the art style to: solid defined linework, rich light-and-shadow "
    "layering, strong volume, thick textured colors, modern cel-shaded digital painting."
)

response = client.models.generate_content(
    model="gemini-3.1-flash-image-preview",
    contents=[prompt, source],
    config=types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        image_config=types.ImageConfig(aspect_ratio="1:1", image_size="2K"),
    ),
)
for part in response.parts:
    if image := part.as_image():
        image.save("styled_output.png")
```

## Prompting Rules for Style Transfer

1. **Lock composition first**: open with "keep the pose, composition, and subject identical".
2. **Describe style with visual mechanics**: linework weight, shadow depth, color thickness, rendering method (e.g., cel-shaded, painterly, flat watercolor).
3. **Reference a single image only** unless the task explicitly requires mixing multiple refs (to avoid content blending).
4. **If character consistency is needed across turns**, feed previously generated images back into subsequent prompts.

## Output Configuration

| Parameter | Supported values |
| --- | --- |
| `aspect_ratio` | `1:1`, `1:4`, `1:8`, `2:3`, `3:2`, `3:4`, `4:1`, `4:3`, `4:5`, `5:4`, `8:1`, `9:16`, `16:9`, `21:9` |
| `image_size` | `512`, `1K`, `2K`, `4K` |

## Verification

Before claiming completion:

- Confirm the API key loaded correctly and the request returned image data.
- Open the generated image to verify style and composition match the prompt intent.
- If the style drifted, tighten the "keep X identical" clause and re-run.
