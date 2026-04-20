---
name: chibi-sticker-sheet
description: Use when generating a LINE/WeChat-style chibi sticker sheet (4x8 grid, 32 expressions) from an anime character reference image via Gemini, including transparent PNG output and individual cell slicing.
---

# Chibi Sticker Sheet

Generate a 4×8 chibi sticker sheet from a character reference image with Gemini, then key out the white background and slice into 32 individual transparent PNGs.

## Scope

- Input: 1 character reference PNG + a list of 32 expressions
- Output: `sheet_white.png`, `sheet_transparent.png`, `cells/*.png` (512×512 each)
- Requires: any one of `GOOGLE_AI_STUDIO_API_KEY` / `GEMINI_API_KEY` / `GOOGLE_API_KEY` (AI Studio) **or** `VERTEX_AI_KEY` (Vertex Express) **or** `GOOGLE_GENAI_USE_VERTEXAI=true` + `GOOGLE_CLOUD_PROJECT`/`LOCATION` (Vertex ADC); Python + `uv`; model `gemini-3.1-flash-image-preview`
- Not covered: per-cell text overlays; use PIL `ImageDraw` post-hoc for captions

## Key Finding: Double-Matte Fails

The natural "white bg + black bg → α extraction" requires pixel-aligned foregrounds. **Gemini ignores bg-change instructions** in image-to-image edits and returns the same image. Use **edge flood-fill keying** instead (see scripts/key_alpha.py).

## Inputs

| Variable | Meaning |
|---|---|
| `CHAR_REF` | Absolute path to character reference PNG |
| `EXPRESSIONS` | List of 32 strings, action-first (e.g. `"waterfall tears streaming down both cheeks"`) |
| `OUT_DIR` | Output directory |

## Workflow

```text
[1] Generate white-bg 4×8 sheet (two Gemini calls, each 4×4)
      -> gemini-3.1-flash-image-preview, image-to-image with CHAR_REF
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

Gemini's image output resolution caps around 1024×1024. A single 4×8 canvas would squash each cell to ~128×256px — too small for clean chibi art. Generating two 4×4 sheets and stitching keeps per-cell resolution at the same quality as 16-sticker sets.

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
# Resize b to match a's width if they differ (Gemini output dims can vary)
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
- **Be concise.** Overlong prompts (>300 words) trigger `MALFORMED_FUNCTION_CALL`. No negative-list clauses (`must NOT`).
- **No in-image text.** Gemini cannot reliably render Chinese/Japanese — add captions via PIL post-hoc.
- **Style vocabulary that works:** `super-deformed 2-head ratio` · `thick uniform bold black ink outline` · `flat cel shading` · `mochi chibi` · `large round pink cheek blush dots`
- **Character attributes to lock:** hair color, hair length/style, ALL accessories (花饰 must name species: `pink cherry blossom sakura flower hair ornament`), eye color, every garment piece.

### Expression Diversity Rules

Gemini tends to reuse the same pose for cells that share a column, especially **cells 9 and 13** (column-1 of rows 3–4) and the equivalent pairs in the second sheet (**25 and 29**). Prevent duplicates:

1. **Span all six emotional axes** across the 32 slots — no axis should appear more than 6 times:

   | Axis | Example actions |
   |---|---|
   | Joy / excitement | raised fist, jumping, sparkle eyes |
   | Sadness / crying | waterfall tears, wilting head, tissues |
   | Anger / frustration | puffed cheeks, steam from head, finger-point |
   | Surprise / shock | wide-O mouth, hands-on-cheeks, dropped jaw |
   | Shy / embarrassed | hands over red face, hiding behind sleeves |
   | Calm / smug | arms crossed, side-eye, tea-sipping |

2. **Assign a distinct body verb to every cell.** If two cells share the same verb (e.g., both "crying"), Gemini collapses them. Make verbs orthogonal: `waterfall-tears arms-spread` ≠ `single-teardrop hands-clasped`.

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

Gemini does **not** divide the canvas into equal cells. Row/column heights vary (e.g., top row 550px vs. bottom row 480px). Hard `image_size / 4` cuts cause sticker overflow into adjacent cells.

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

Gemini 3 image models have three transient failure modes:

| Symptom | Action |
|---|---|
| `503 UNAVAILABLE` / `429 RESOURCE_EXHAUSTED` | Exponential back-off (`2^attempt * 5s`), 6 retries |
| `FinishReason.MALFORMED_FUNCTION_CALL` | Shorten/simplify prompt; remove negative clauses |
| `resp.parts` is `None`, only text returned | Retry; tighten the lock clause |

See `scripts/generate.py` for the full retry wrapper.

## Cross-Sheet Consistency (32-sticker specific)

Two separate Gemini calls will often produce slightly different rendering — brightness, line weight, palette temperature, or shading style may drift. Control it with the following steps:

### 1. Lock the style prompt byte-for-byte

Copy the exact art-style paragraph and character-lock paragraph from Call A into Call B without any edits. Even synonym substitutions (`circular` vs `round`) can shift Gemini's style.

### 2. Submit Call B with the sheet_white_a.png as additional reference

Pass `sheet_white_a.png` alongside `CHAR_REF` as the image input for Call B. Gemini will use it as a visual anchor. Example (google-generativeai SDK):

```python
parts = [
    PIL_to_part(char_ref_img),
    PIL_to_part(sheet_a_img),  # style anchor
    types.Part(text=prompt_b),
]
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

If drift is visible, re-run Call B with a slightly adjusted prompt (e.g., add `"same warm creamy pastel palette as reference sheet"`) and a fresh seed. Repeat QC.

### 5. Common cross-sheet failure modes

| Symptom | Cause | Fix |
|---|---|---|
| Sheet B looks sketch-like, less shaded | Gemini skipped cel-shading | Add `"flat cel shading, no sketch lines"` to Call B prompt |
| Hair color changes between row 4 and row 5 | Character lock didn't persist | Repeat exact hex color code in Call B character lock |
| Sheet B overall darker | Different generation context | Apply brightness correction (step 3) |
| Outline weight visibly thinner in sheet B | Gemini style variance | Add `"thick uniform bold black ink outline, same line weight as reference"` |

## Common Mistakes

| Mistake | Fix |
|---|---|
| Vague accessories (`red ribbon`) | Spell out species/shape (`pink sakura flower, 5 petals`) |
| Uniform expressions (all sad-variants) | Mix action verbs: raised fist, palm-push, tilted head, waterfall tears, thumbs-up |
| Cells 9 and 13 look identical | They share column-1; assign different emotion axis **and** body posture to each — see Expression Diversity Rules |
| Grid lines appear in output | Add `seamless pure white, no grid lines, no cell borders` to prompt |
| Hair color drifts across cells | Repeat exact color spec as first item in "character lock" |
| `image.size` AttributeError | `part.as_image()` returns genai Image, not PIL; convert via `Image.open(io.BytesIO(img.image_bytes))` |
| Adjacent sticker bleeds into cell | Gemini grid is uneven; use `_find_cuts()` dark-profile detection, not `image_size // 4` |
| White clothing becomes transparent | Outline gaps let flood reach fabric; set `OUTLINE_DILATE=2` to dilate outline before flood-fill |

## WeChat Submission Extras

Each sticker set needs three additional assets. Generate with `scripts/generate_extras.py`:

```bash
uv run generate_extras.py <sticker_dir> <char_ref_image> "<theme hint>"
```

| Asset | Spec | How produced |
|---|---|---|
| `banner.png` | 750×400 PNG, colorful bg, no text | Gemini image-to-image, 16:9 → center-crop |
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
