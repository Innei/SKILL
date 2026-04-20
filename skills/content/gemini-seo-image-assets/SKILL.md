---
name: gemini-seo-image-assets
description: Use when a web project needs Google AI Studio or Gemini-generated favicon and Open Graph images, exported icon variants, and matching SEO metadata wiring.
---

# Gemini SEO Image Assets

## Overview

Generate image-first SEO assets with Gemini 3.1, then finish the exact typography, icon sizes, manifest, and metadata locally.

Core rule: **let Gemini generate composition and texture; do not rely on Gemini for exact text rendering**.

## When to Use

- A site has missing or generic `favicon.ico`, `apple-touch-icon`, or `og-image`.
- A web app needs route-level `title`, `description`, `og:*`, `twitter:*`, and `canonical` wiring.
- The user explicitly wants Gemini or Google AI Studio involved in the asset creation flow.

Do not use this skill when:

- The project already has a strict vector logo or brand system that should be edited directly.
- The task is only to tweak existing metadata strings without generating new raster assets.
- Exact logotypes or multilingual text must come directly from the model output.

## Workflow

### 1. Inspect the project surface

Confirm these before generating anything:

| Check | Why it matters |
| --- | --- |
| Root layout / head entry | Needed for icons, manifest, theme-color, global meta |
| Route metadata API | Determines where `title`, `description`, `robots`, and `canonical` belong |
| `public/` assets | Prevents accidental overwrite and reveals existing filenames |
| Build command | Required for verification after wiring |

### 2. Load credentials and choose the model

- Read `.env.local` first, then `.env`.
- Accept any one of these auth paths (see `gemini-image-generation` skill for the full `_make_client()` helper):
  - AI Studio: `GOOGLE_AI_STUDIO_API_KEY` / `GEMINI_API_KEY` / `GOOGLE_API_KEY`
  - Vertex Express: `VERTEX_AI_KEY`
  - Vertex ADC: `GOOGLE_GENAI_USE_VERTEXAI=true` + `GOOGLE_CLOUD_PROJECT`/`LOCATION`
- Default model: `gemini-3.1-flash-image-preview` (same name on both surfaces).
- If the user asks for a newer or latest Gemini image model, verify the current official name before use.

Minimal request shape:

```json
{
  "contents": [{ "parts": [{ "text": "..." }] }],
  "generationConfig": {
    "responseModalities": ["IMAGE"],
    "imageConfig": {
      "aspectRatio": "1:1",
      "imageSize": "2K"
    }
  }
}
```

> **Vertex caveat**: `imageSize` is not accepted on Vertex endpoints (raises `ValidationError: Extra inputs are not permitted`). Omit `imageSize` when routing through `VERTEX_AI_KEY` / Vertex ADC; the model returns its default resolution and you post-process to the target exports.

### 3. Generate two base images

Always generate **background/base artwork**, not final text-complete share cards.

| Asset | Aspect ratio | Purpose | Rule |
| --- | --- | --- | --- |
| Favicon source | `1:1` | Master square artwork for all icon exports | No text, strong silhouette, readable at `16px` |
| OG background | `16:9` | Base for `1200x630` social preview | Reserve calm negative space for local title overlay |

Use the prompt templates in [references/prompts.md](./references/prompts.md). Adapt the palette, mood, and product nouns to the project.

### 4. Post-process locally

Do the deterministic steps on the local machine:

- Crop/fit the favicon master to a square source such as `1024x1024`.
- Export:
  - `favicon.ico`
  - `favicon-16x16.png`
  - `favicon-32x32.png`
  - `apple-touch-icon.png`
  - `android-chrome-192x192.png`
  - `android-chrome-512x512.png`
- Fit the OG base to `1200x630`.
- Add title, subtitle, tagline, or other exact copy with local drawing tools or code.
- Prefer local fonts and color tokens from the project instead of asking Gemini to render exact text.

### 5. Wire SEO metadata

Preferred structure:

| Layer | Responsibility |
| --- | --- |
| Root layout | icons, manifest, `theme-color`, `color-scheme`, app name |
| Shared SEO helper | builds `title`, `description`, `robots`, `og:*`, `twitter:*`, `canonical` |
| Route modules | call the helper with route-specific values |

Recommended rules:

- Home or marketing entry pages may be `index,follow`.
- Quiz, shell, preview, and result routes are usually `noindex,nofollow`.
- If the deployment origin is known, use `VITE_SITE_URL` to produce absolute `canonical`, `og:url`, and `og:image`.
- If the origin is unknown, keep paths root-relative and let the runtime origin resolve them.

### 6. Validate before claiming completion

Run all of the following:

| Verification | Purpose |
| --- | --- |
| Visual self-check or model-based image inspection | Confirms icon has no stray text and OG text is legible |
| Typecheck | Confirms metadata helper and route integration compile |
| Production build | Confirms asset links and route modules build successfully |

## Guardrails

| Rule | Reason |
| --- | --- |
| Do not trust Gemini for exact Chinese or brand text | Text rendering is the least reliable part of the model output |
| Keep favicon imagery simple | Browser icons collapse under detail very quickly |
| Keep OG imagery quieter than the UI | Social previews need text contrast and scanability |
| Do not hardcode a production domain in source | Canonical origin often differs by environment |
| Do not overwrite user-owned assets blindly | Existing branding may already be in use |

## Reference Files

- [references/prompts.md](./references/prompts.md): prompt templates for favicon and OG background generation.
