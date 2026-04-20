---
name: acg-character-settei
description: Use when generating an ACG (anime/manga) character settei sheet (キャラ設定資料) — multi-view full-body lineup, expression list, detail callouts, color palette — from a template settei image plus a single character reference image. Built on top of gemini-image-generation; this skill encodes the layout-locking + identity-locking prompt pattern that reliably produces settei-style output.
---

# ACG Character Settei Generation

## Overview

Produce a horizontal anime character design sheet by feeding the model two reference images at once:

1. **Template image** — supplies layout, composition, line weight, palette aesthetic, and white background.
2. **Character image** — supplies identity (hair, eyes, face, outfit, expression).

The skill is a thin wrapper over `gemini-image-generation`. Read that skill first for client setup, retry pattern, and watermark handling.

## When to Use

- User has a settei template (any artist's character sheet) and wants to restyle a different character into the same sheet format.
- User wants a clean three-view + expression-sheet + detail-callout layout for an OC, VTuber, or avatar character.

Skip when:

- Only one full-body pose is needed → use plain `gemini-image-generation` instead.
- The template requires legible Japanese annotations as real text (Gemini cannot render exact text reliably; treat the script labels as decorative).

## Inputs

| Variable | Meaning |
|---|---|
| `TEMPLATE_PATH` | Path to the settei template image (defines layout). |
| `CHARACTER_PATH` | Path to the character reference image (defines identity). |
| `OUTFIT_DESC` | One-sentence outfit description, locked across all three full-body views. |
| `OUT_PATH` | Output PNG path. |

## Workflow

```text
[1] Inspect both inputs
      -> read template to identify panels (full-body count, expression count, callouts, palette)
      -> read character to extract identity tokens (hair, eyes, blush, accessories, outfit)

[2] Compose the prompt with two locked blocks
      -> LAYOUT block: lock template's composition, line style, background, panel arrangement
      -> IDENTITY block: lock character's hair / eyes / accessories / outfit, applied to every panel

[3] Call gemini-3.1-flash-image-preview
      -> contents = [prompt, template_image, character_image]
      -> aspect_ratio = "16:9", image_size = "2K"

[4] Verify
      -> three full-body views all wear the same outfit
      -> expression row matches template count
      -> character identity matches reference (hair color, eye color, accessories)
      -> if drift, tighten the locked block that drifted and retry; do not patch the output
```

## Prompt Pattern

Two blocks, positive instructions, ≤ ~200 words total. Long negative-list prompts trigger `MALFORMED_FUNCTION_CALL`.

```text
Create a horizontal anime character settei sheet matching the EXACT layout,
composition, line weight, soft watercolor shading, and pure white background
of the FIRST reference image:
- left: three full-body standing views (front, side, back)
- upper right: row of small head-and-shoulder expression variations
  (gentle smile, blush, surprised, sleepy, pout, happy)
- lower right: close-up detail callouts (eye, <key outfit detail>) and small
  color-palette swatch dots
- thin pencil-style annotation lines and tiny handwritten-style note marks
  (decorative, no need to read)

The character must be the girl from the SECOND reference image:
<2–4 short identity sentences: hair, bangs, eye color, accessories, expression>.
She wears <OUTFIT_DESC>. Keep the same outfit consistent across all three
full-body views.

Art style: soft anime cel-shading with light watercolor highlights, clean
thin linework, bright airy palette, white paper background — match the first
reference's aesthetic exactly.
```

## Rules

- **Always pass exactly two reference images**: template first, character second. Order matters — the model treats the first image as the structural template.
- **Lock the outfit explicitly** with `Keep the same outfit consistent across all three full-body views.` Without this, side and back views drift to different outfits.
- **Do not include negative lists** (`do NOT add ...`). Use positive substitutes.
- **Treat label text as decorative.** Never request specific Japanese strings; the model will produce plausible-looking marks but not real readable text.
- **Aspect ratio 16:9, size 2K** matches the typical settei canvas. Use `1K` for fast iteration. On Vertex (`VERTEX_AI_KEY` or `GOOGLE_GENAI_USE_VERTEXAI=true`), `image_size` is dropped automatically — the model uses its default resolution.
- **Identity drift fix**: re-extract identity tokens from the character reference and compress to ≤ 4 sentences; do not over-describe.
- Auth: any one of `GOOGLE_AI_STUDIO_API_KEY` / `GEMINI_API_KEY` / `GOOGLE_API_KEY` (AI Studio), **or** `VERTEX_AI_KEY` (Vertex Express), **or** `GOOGLE_GENAI_USE_VERTEXAI=true` + `GOOGLE_CLOUD_PROJECT`/`LOCATION` (Vertex ADC). Never read `.env` directly.

## Script

`scripts/gen_settei.py` — copy, edit the four constants at the top, run with `uv run`. Inline `uv` deps declared at the top of the file.

```bash
uv run skills/content/acg-character-settei/scripts/gen_settei.py
```

## Verification

- Open the output PNG; confirm three distinct full-body views with the SAME outfit.
- Confirm expression row count matches template.
- Confirm character hair color / eye color / accessory placement matches the character reference.
- If a Gemini sparkle ✦ leaked in (from a Gemini-sourced template), add the watermark-removal clause from `gemini-image-generation` and retry.
