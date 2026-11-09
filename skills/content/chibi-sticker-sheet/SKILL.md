---
name: chibi-sticker-sheet
description: Use when generating LINE/WeChat-style chibi stickers (4x8 grid, 32 expressions), transparent PNG cells, or matching submission banners from an anime character reference, using Codex CLI or Gemini.
---

# Chibi Sticker Sheet

Generate a 4×8 chibi sticker sheet from a character reference image with **Codex CLI by default**, then key out the white background and slice into 32 individual transparent PNGs. Gemini remains available via `--provider gemini`.

## Scope

- Input: 1 character reference PNG + a list of 32 expressions
- Output: `sheet_white.png`, `sheet_transparent.png`, `cells/*.png` (512×512 each)
- Requires: Python + `uv`, plus the selected provider's setup below.
- Not covered: per-cell text overlays; use PIL `ImageDraw` post-hoc for captions

## Provider Selection

All three generation entrypoints (`generate.py`, `generate_banner.py`, `generate_extras.py`) accept `--provider codex|gemini`; omitting it selects **codex**.

| Provider | Setup | Generation |
|---|---|---|
| `codex` (default) | Install a current Codex CLI, run `codex login`, and use an account/provider with native image generation available | `codex exec` with `image_generation` enabled and reference images attached using `--image`; inherits the CLI's configured agent model |
| `gemini` | Any one of `GOOGLE_AI_STUDIO_API_KEY` / `GEMINI_API_KEY` / `GOOGLE_API_KEY` (AI Studio), `VERTEX_AI_KEY` (Vertex Express), or `GOOGLE_GENAI_USE_VERTEXAI=true` + `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION` (Vertex ADC; location defaults to `us-central1`) | `gemini-3.1-flash-image-preview` via Google GenAI SDK |

Codex uses its CLI login/configuration; Google credentials are only read for `--provider gemini`. The wrapper requests native image generation explicitly, attaches the character first and optional style anchor second, and validates an actual image file before saving the requested output. Each call runs in a temporary `workspace-write` sandbox, cleaned up after the call. It does not bypass the sandbox or silently fall back to Gemini. If native image generation is unavailable, report the error and select Gemini explicitly when appropriate.

See [official Codex image generation documentation](https://learn.chatgpt.com/docs/image-generation) for availability and native CLI usage. Do not treat an agent's `--model` as the image model, or replace this route with an OpenAI Images API call.

### Generation Commands

Run these commands from this skill's directory; use absolute `CHAR_REF` and `OUT_DIR` paths. Create `prompt_a.txt` and `prompt_b.txt` using the prompt structure below, with 16 expressions each.

```bash
mkdir -p "$OUT_DIR"
# Default: Codex CLI, with the same character and style across both sheets
uv run scripts/generate.py "$CHAR_REF" prompt_a.txt "$OUT_DIR/sheet_white_a.png"
uv run scripts/generate.py "$CHAR_REF" prompt_b.txt "$OUT_DIR/sheet_white_b.png" \
  --anchor "$OUT_DIR/sheet_white_a.png"

# Alternative: append --provider gemini to both calls
uv run scripts/generate.py "$CHAR_REF" prompt_a.txt "$OUT_DIR/sheet_white_a.png" --provider gemini
```

Use the **same provider for both sheets**. After stitching, key and slice with:

```bash
uv run scripts/key_alpha.py "$OUT_DIR/sheet_white.png" "$OUT_DIR" --rows 8 --cols 4
```

## Key Finding: Double-Matte Fails with Gemini

The natural "white bg + black bg → α extraction" requires pixel-aligned foregrounds. In the tested Gemini flow, bg-change edits returned the same image. Use **edge flood-fill keying** for both providers (see scripts/key_alpha.py).

## Inputs

| Variable | Meaning |
|---|---|
| `CHAR_REF` | Absolute path to character reference PNG |
| `EXPRESSIONS` | List of 32 strings, action-first (e.g. `"waterfall tears streaming down both cheeks"`) |
| `OUT_DIR` | Output directory |

## Workflow

```text
[1] Generate white-bg 4×8 sheet (two calls, each 4×4)
      -> Codex CLI (default) or Gemini, with CHAR_REF
      -> Call A: expressions 1–16  -> sheet_white_a.png
      -> Call B: expressions 17–32 -> sheet_white_b.png
      -> Stitch A and B vertically -> sheet_white.png

[2] Key out background
      -> scripts/key_alpha.py: edge flood-fill via scipy.ndimage.label
      -> save sheet_transparent.png

[3] Slice 4×8 grid
      -> scripts/key_alpha.py: min(cw, ch) square crop, centered per cell
      -> save cells/01_*.png … cells/32_*.png (512×512)
```

### Why Two Calls

Two 4×4 sheets keep the 16-expression prompts manageable and give each sticker more canvas space than one dense 4×8 sheet. Use this layout for either provider; actual output dimensions depend on the provider. Do not assume a fixed Gemini resolution cap applies to Codex.

## Prompt Structure

**Two calls (Call A: expressions 1–16, Call B: expressions 17–32), each image-to-image with the same character reference.**

Use identical art-style and character-lock text for both calls to ensure visual consistency.

```
Generate a 4x4 grid sticker sheet of 16 chibi stickers of the same character
from the reference image. Seamless pure white (#ffffff) background; no grid
lines, no cell borders, no text, no captions. Stickers evenly spaced.

Art style: LINE / WeChat Japanese chibi sticker, extreme super-deformed
2-head body ratio, oversized round head, tiny stubby body, thick uniform
bold black ink outline, flat cel shading, warm creamy pastel palette, two
large round pink cheek blush dots on every face, large round eyes with a
single bright white highlight, mochi chibi aesthetic.

Character lock (must match in every single cell):
[list each attribute: hair color/style, accessories, eye color, outfit details]

16 expressions, left-to-right top-to-bottom:
1. <action-first description>
...
16. <action-first description>
```

Run the same prompt template a second time with expressions 17–32 substituted in. Then stitch:

```python
from PIL import Image

a = Image.open("sheet_white_a.png")
b = Image.open("sheet_white_b.png")
# Resize b to match a's width if they differ (output dimensions can vary)
if b.width != a.width:
    b = b.resize((a.width, int(b.height * a.width / b.width)), Image.LANCZOS)
combined = Image.new("RGB", (a.width, a.height + b.height), (255, 255, 255))
combined.paste(a, (0, 0))
combined.paste(b, (0, a.height))
combined.save("sheet_white.png")
```

### Prompting Rules

- **Lock first, change second.** Open with "Character lock" before anything changes.
- **Action-first expressions.** `"waterfall tears streaming"` beats `"sad"`. Include a visible prop or gesture.
- **Be concise.** For Gemini, overlong prompts (>300 words) and negative-list clauses have triggered `MALFORMED_FUNCTION_CALL`; shorten/simplify on that error. This is not a Codex prompt limit.
- **No in-image text for this workflow.** Add captions via PIL post-hoc for consistent wording and typography across providers.
- **Style vocabulary that works:** `super-deformed 2-head ratio` · `thick uniform bold black ink outline` · `flat cel shading` · `mochi chibi` · `large round pink cheek blush dots`
- **Character attributes to lock:** hair color, hair length/style, ALL accessories (花饰 must name species: `pink cherry blossom sakura flower hair ornament`), eye color, every garment piece.

### Expression Diversity Rules

In Gemini runs, cells sharing a column tended to reuse the same pose, especially **cells 9 and 13** (column-1 of rows 3–4) and the equivalent pairs in the second sheet (**25 and 29**). Apply the same diversity checks to Codex output:

1. **Span all six emotional axes** across the 32 slots — no axis should appear more than 6 times:

   | Axis | Example actions |
   |---|---|
   | Joy / excitement | raised fist, jumping, sparkle eyes |
   | Sadness / crying | waterfall tears, wilting head, tissues |
   | Anger / frustration | puffed cheeks, steam from head, finger-point |
   | Surprise / shock | wide-O mouth, hands-on-cheeks, dropped jaw |
   | Shy / embarrassed | hands over red face, hiding behind sleeves |
   | Calm / smug | arms crossed, side-eye, tea-sipping |

2. **Assign a distinct body verb to every cell.** Similar verbs (e.g., both "crying") can collapse into duplicate poses. Make verbs orthogonal: `waterfall-tears arms-spread` ≠ `single-teardrop hands-clasped`.

3. **Critical column-1 pairs: 9 & 13, and 25 & 29 must each differ in both emotion axis AND body posture.** Write each pair side by side before finalising and check they are visually distinguishable.

4. **Vary facing direction and limb action across rows.** Cells in the same column naturally echo each other; counteract by alternating pose direction (facing left vs. right) or prop presence.

5. **No expression from Call A (1–16) should be repeated in Call B (17–32).** Cross-check verbs before submitting the second prompt.

**Reference 32-slot layout (copy and customize):**

Call A (sheet 1, expressions 1–16):
```
1.  arms raised, jumping for joy, sparkle eyes
2.  waterfall tears streaming, arms limp at sides
3.  puffed cheeks, steam wisps from head, fists clenched
4.  wide-O mouth shock, both hands on cheeks Home-Alone pose
5.  smug smile, arms crossed, eyes half-lidded
6.  shy embarrassment, hands pressed together, deep blush
7.  thumbs-up grin, winking one eye
8.  single teardrop rolling, trembling lip, hands clasped
9.  hyper-excited wave, leaning forward, mouth wide open    ← must differ from #13
10. exhausted slumped, sweat drop, drooping eyes
11. index finger raised, lecture pose, tiny smile
12. heart eyes, both hands framing face, rosy cheeks
13. angry stomp, foot raised, fist shaking at sky           ← must differ from #9
14. sleeping ZZZ, head tilted, eyes closed
15. nervous laugh, hand behind head, eye twitch
16. victory peace-sign, tongue out, confetti burst
```

Call B (sheet 2, expressions 17–32):
```
17. cheering both fists raised, eyes glittering, mouth wide
18. sobbing face buried in hands, shoulders shaking
19. furious vein-pop, pointing finger, leaning in
20. startled leap, arms flailing outward, pupils tiny
21. lovesick float, dreamy spiral eyes, hearts around head
22. pouty sulk, arms crossed, cheeks puffed, eyes averted
23. excited run, legs spinning wheel, sweat drops flying
24. relieved sigh, hand on chest, eyes closed in relief
25. cheerful skip, one leg up, waving hello              ← must differ from #29
26. defeated head-desk slump, tiny sweat rivers
27. determined fist-pump, one eye closed, cape flutter
28. panicked sprint, eyes wide, papers scattering
29. grumpy arms-crossed side-eye, tapping foot impatiently ← must differ from #25
30. yawning stretch, arms out, eyes teary from yawn
31. embarrassed covering ears, blushing furiously, hunched
32. triumphant pose, foot on imaginary podium, sparkle burst
```

## Grid Slicing: Auto-Detect Boundaries

Generated grids may have uneven cells. Row/column heights vary (e.g., top row 550px vs. bottom row 480px in Gemini runs). Hard `image_size / 4` cuts cause sticker overflow into adjacent cells; inspect this for both providers.

After stitching the two 4×4 sheets into one 4×8 canvas, run `_find_cuts()` on the combined image. Pass `n_rows=8, n_cols=4`.

**Fix:** compute per-row and per-column **dark-outline occupancy** profiles instead of white-fraction profiles. True inter-cell gaps have zero or near-zero dark pixels because the black outline disappears entirely in the white gutter, while white hair or clothing inside a sticker still leaves some outline pixels somewhere on that same row/column.

```python
dist = np.max(np.abs(rgb.astype(np.int16) - 255), axis=2)  # 0 = white
dark = binary_dilation(dist > OUTLINE_THRESH, iterations=1)
row_profile = dark.sum(axis=1)          # dark outline count per row
col_profile = dark.sum(axis=0)          # dark outline count per col
# find contiguous near-zero-dark runs, then select the deepest valleys
# under broad cell-size sanity bounds instead of equal-spacing fallback
```

If a gutter is noisy and no exact zero-dark run survives, fall back to the lowest dark-count valleys in the smoothed profile. Cells are saved as `cells/01_*.png … cells/32_*.png` (512×512). See `scripts/key_alpha.py: _find_cuts()`.

## Alpha Keying: Edge Flood-Fill

See `scripts/key_alpha.py`. Core algorithm:

```python
# dist[y,x] = max channel delta from pure white (0 = white, 255 = farthest)
dist = np.max(np.abs(rgb.astype(np.int16) - 255), axis=2)
near_white = dist < WHITE_TOL          # WHITE_TOL = 28

lbl, _ = label(near_white)            # connected components
edge_ids = {lbl[0,:], lbl[-1,:], lbl[:,0], lbl[:,-1]} - {0}  # border-touching
bg_mask = np.isin(lbl, list(edge_ids))

alpha = np.where(bg_mask, 0, 255).astype(np.uint8)
# feather boundary: GaussianBlur(radius=1.2) on alpha channel
```

Interior white pixels (shirt, skin highlights) are enclosed by foreground and never reach the border — they stay opaque.

**White clothing leak:** if the outline has 1–2 px gaps, the flood leaks through into white fabric. Fix: dilate dark outline pixels (`dist > OUTLINE_THRESH=150`) by `OUTLINE_DILATE=2` iterations before flood-fill to plug gaps.

## Retry Pattern

**Codex:** each invocation has a 900-second timeout. A failed CLI exit, text-only response, missing output file, or unreadable image is an error. Check `codex login status` and native image-generation availability before retrying. No automatic retries or provider switching are performed by the wrapper.

**Gemini:** the SDK wrapper retains the following retry behavior:

| Symptom | Action |
|---|---|
| `503 UNAVAILABLE` / `429 RESOURCE_EXHAUSTED` | Exponential back-off (`2^attempt * 5s`), up to 6 attempts |
| `FinishReason.MALFORMED_FUNCTION_CALL` | Shorten/simplify prompt; remove negative clauses |
| `resp.parts` is `None`, only text returned | Retry; tighten the lock clause |

See `scripts/generate.py` for the full retry wrapper.

## Cross-Sheet Consistency (32-sticker specific)

Two separate calls can produce slightly different rendering — brightness, line weight, palette temperature, or shading style may drift. Keep the provider fixed and control it with the following steps:

### 1. Lock the style prompt byte-for-byte

Copy the exact art-style paragraph and character-lock paragraph from Call A into Call B without any edits. Even synonym substitutions (`circular` vs `round`) can shift the rendering style.

### 2. Submit Call B with the sheet_white_a.png as additional reference

Pass `sheet_white_a.png` alongside `CHAR_REF` for Call B. Both providers support this through the same CLI:

```bash
uv run scripts/generate.py "$CHAR_REF" prompt_b.txt "$OUT_DIR/sheet_white_b.png" \
  --anchor "$OUT_DIR/sheet_white_a.png"
# Append --provider gemini if Call A used Gemini.
```

### 3. Post-process for brightness/contrast parity

After stitching, compute the mean luminance of the top half (sheet A cells) and bottom half (sheet B cells). If they differ by more than 8 luma units, apply a `PIL.ImageEnhance.Brightness` correction to the dimmer half before writing `sheet_white.png`.

```python
from PIL import Image, ImageEnhance
import numpy as np

def mean_luma(img_crop):
    arr = np.asarray(img_crop.convert("L")).astype(float)
    return arr.mean()

combined = Image.open("sheet_white.png")
h = combined.height // 2
luma_a = mean_luma(combined.crop((0, 0, combined.width, h)))
luma_b = mean_luma(combined.crop((0, h, combined.width, combined.height)))
if abs(luma_a - luma_b) > 8:
    # brighten or darken the bottom half
    factor = luma_a / luma_b
    bottom = combined.crop((0, h, combined.width, combined.height))
    bottom = ImageEnhance.Brightness(bottom).enhance(factor)
    combined.paste(bottom, (0, h))
    combined.save("sheet_white.png")
```

### 4. Visual QC before alpha keying

Open `sheet_white.png` and scan for:
- Line weight mismatch (bottom half lines thinner/thicker)
- Palette temperature shift (warmer/cooler tones)
- Hair color drift across the boundary row

If drift is visible, re-run Call B with a slightly adjusted prompt (e.g., add `"same warm creamy pastel palette as reference sheet"`). Repeat QC.

### 5. Common cross-sheet failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Sheet B looks sketch-like, less shaded | Model skipped cel-shading | Add `"flat cel shading, no sketch lines"` to Call B prompt |
| Hair color changes between row 4 and row 5 | Character lock didn't persist | Repeat exact hex color code in Call B character lock |
| Sheet B overall darker | Different generation context | Apply brightness correction (step 3) |
| Outline weight visibly thinner in sheet B | Cross-call style variance | Add `"thick uniform bold black ink outline, same line weight as reference"` |

## Common Mistakes

| Mistake | Fix |
|---|---|
| Vague accessories (`red ribbon`) | Spell out species/shape (`pink sakura flower, 5 petals`) |
| Uniform expressions (all sad-variants) | Mix action verbs: raised fist, palm-push, tilted head, waterfall tears, thumbs-up |
| Cells 9 and 13 look identical | They share column-1; assign different emotion axis **and** body posture to each — see Expression Diversity Rules |
| Grid lines appear in output | Add `seamless pure white, no grid lines, no cell borders` to prompt |
| Hair color drifts across cells | Repeat exact color spec as first item in "character lock" |
| `image.size` AttributeError | `part.as_image()` returns genai Image, not PIL; convert via `Image.open(io.BytesIO(img.image_bytes))` |
| Adjacent sticker bleeds into cell | Generated grid is uneven; use `_find_cuts()` dark-profile detection, not `image_size // 4` |
| Codex exits successfully but only returns prose | Require a readable generated image; inspect the error and retry or explicitly select Gemini |
| White clothing becomes transparent | Outline gaps let flood reach fabric; set `OUTLINE_DILATE=2` to dilate outline before flood-fill |

## WeChat Submission Extras

Each sticker set needs three additional assets. Generate with `scripts/generate_extras.py`:

```bash
uv run scripts/generate_extras.py <sticker_dir> <char_ref_image> "<theme hint>"
# Append --provider gemini to generate the banner with Gemini instead.
```

| Asset | Spec | How produced |
|---|---|---|
| `banner.png` | 750×400 PNG, colorful bg, no text | Codex CLI (default) or Gemini, 16:9 → center-crop |
| `cover.png` | 240×240 transparent PNG, half/full body | Cell 07 (thumbs-up) resized with PIL |
| `icon.png` | 50×50 transparent PNG, head shot | Cell 07 full cell resized (no crop — chibi proportions fit naturally) |

**Theme hints by set:**
- Snow/winter → `"snowy winter wonderland"`
- Autumn ginkgo → `"golden autumn ginkgo forest"`
- Summer sailor → `"sunny summer beach ocean waves"`
- Spring school → `"cherry blossom spring school campus"`
- Kimono/plum → `"red plum blossom Japanese garden"`

**WeChat rules:**
- Banner: colorful background only — no white, no transparent; no text; story-rich scene
- Cover: transparent bg; no white outline; avoid over-cropping (half/full body preferred)
- Icon: transparent bg; head-only, no square border; must differ across sets

## Multi-Platform Banner

`scripts/generate_banner.py` produces a standalone banner for any registered platform — independent of the WeChat extras flow. WeChat itself is one preset; Twitter/X is another. New platforms are added by appending to the `PLATFORMS` dict.

```bash
uv run scripts/generate_banner.py <char_ref> "<theme>" <out_path> --platform twitter
# Append --provider gemini for the alternative provider.
```

| Platform | Size | Source AR (both providers) | Crop |
|---|---|---|---|
| `wechat` | 750×400 | `16:9` | minimal (~6% vertical trim) |
| `twitter` | 1500×500 | `16:9` | aggressive (middle 56% only) |

Each preset is a `Platform(width, height, aspect_ratio, composition_hint)`. The hint is appended to the prompt and is the place to encode platform-specific safe-zone layout (avatar overlay, mobile crop, letterbox bars). WeChat needs no hint; Twitter needs explicit letterbox awareness — see below.

### Letterbox Lesson (Extreme Aspect Ratios)

The existing presets request a 16:9 source canvas from either provider, then center-crop to the platform size. This retains the Gemini-tested composition strategy without assuming Codex shares Gemini's aspect-ratio limits. For Twitter 3:1, the middle 56% of a 16:9 source survives. The naive prompt strategy failed in two opposite ways in Gemini runs:

| Prompt told Gemini | Failure mode |
|---|---|
| "Subjects must fit inside the 22%–78% band" | Gemini adds safety margin → chibis end up at ~35%–65% → tiny in final frame |
| "Subjects must fill the canvas vertically" | Gemini puts hair at 5% of source canvas → heads land in the cropped-off top 22% → decapitation |

The fix is to tell Gemini that the top/bottom 22% are off-screen letterbox bars (showing only background overflow), and place subjects in the middle 25%–75% band of the source canvas. This produces full vertical fill in the final visible frame plus a 3% safety margin against the crop line on each side.

The Twitter preset's `composition_hint` encodes this verbatim. When adding a new extreme-aspect platform (e.g. LinkedIn 4:1 → middle 44% of 16:9 source), compute the letterbox percentages from the math and follow the same structure.

## Verification

```bash
# α channel: expect ~30-40% transparent pixels for a sticker sheet
python -c "
from PIL import Image; import numpy as np
a = np.asarray(Image.open('sheet_transparent.png').convert('RGBA'))[...,3]
print('min', a.min(), 'max', a.max(), 'transparent%', (a<10).mean()*100)
"

# Cell sizes must all be square
ls -la cells/*.png | awk '{print $5, $9}' | head
```
