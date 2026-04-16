---
name: chibi-sticker-sheet
description: Use when generating a LINE/WeChat-style chibi sticker sheet (4x4 grid, 16 expressions) from an anime character reference image via Gemini, including transparent PNG output and individual cell slicing.
---

# Chibi Sticker Sheet

Generate a 4×4 chibi sticker sheet from a character reference image with Gemini, then key out the white background and slice into 16 individual transparent PNGs.

## Scope

- Input: 1 character reference PNG + a list of 16 expressions
- Output: `sheet_white.png`, `sheet_transparent.png`, `cells/*.png` (512×512 each)
- Requires: `GOOGLE_AI_STUDIO_API_KEY`, Python + `uv`, model `gemini-3.1-flash-image-preview`
- Not covered: per-cell text overlays; use PIL `ImageDraw` post-hoc for captions

## Key Finding: Double-Matte Fails

The natural "white bg + black bg → α extraction" requires pixel-aligned foregrounds. **Gemini ignores bg-change instructions** in image-to-image edits and returns the same image. Use **edge flood-fill keying** instead (see scripts/key_alpha.py).

## Inputs

| Variable | Meaning |
|---|---|
| `CHAR_REF` | Absolute path to character reference PNG |
| `EXPRESSIONS` | List of 16 strings, action-first (e.g. `"waterfall tears streaming down both cheeks"`) |
| `OUT_DIR` | Output directory |

## Workflow

```text
[1] Generate white-bg 4×4 sheet
      -> gemini-3.1-flash-image-preview, image-to-image with CHAR_REF
      -> save sheet_white.png

[2] Key out background
      -> scripts/key_alpha.py: edge flood-fill via scipy.ndimage.label
      -> save sheet_transparent.png

[3] Slice 4×4 grid
      -> scripts/key_alpha.py: min(cw, ch) square crop, centered per cell
      -> save cells/01_*.png … cells/16_*.png (512×512)
```

## Prompt Structure

**One call, image-to-image with character reference.**

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

### Prompting Rules

- **Lock first, change second.** Open with "Character lock" before anything changes.
- **Action-first expressions.** `"waterfall tears streaming"` beats `"sad"`. Include a visible prop or gesture.
- **Be concise.** Overlong prompts (>300 words) trigger `MALFORMED_FUNCTION_CALL`. No negative-list clauses (`must NOT`).
- **No in-image text.** Gemini cannot reliably render Chinese/Japanese — add captions via PIL post-hoc.
- **Style vocabulary that works:** `super-deformed 2-head ratio` · `thick uniform bold black ink outline` · `flat cel shading` · `mochi chibi` · `large round pink cheek blush dots`
- **Character attributes to lock:** hair color, hair length/style, ALL accessories (花饰 must name species: `pink cherry blossom sakura flower hair ornament`), eye color, every garment piece.

### Expression Diversity Rules

Gemini tends to reuse the same pose for cells that share a column, especially **cells 9 and 13** (column-1 of rows 3–4). Prevent duplicates:

1. **Span all six emotional axes** across the 16 slots — no axis should appear more than 3 times:

   | Axis | Example actions |
   |---|---|
   | Joy / excitement | raised fist, jumping, sparkle eyes |
   | Sadness / crying | waterfall tears, wilting head, tissues |
   | Anger / frustration | puffed cheeks, steam from head, finger-point |
   | Surprise / shock | wide-O mouth, hands-on-cheeks, dropped jaw |
   | Shy / embarrassed | hands over red face, hiding behind sleeves |
   | Calm / smug | arms crossed, side-eye, tea-sipping |

2. **Assign a distinct body verb to every cell.** If two cells share the same verb (e.g., both "crying"), Gemini collapses them. Make verbs orthogonal: `waterfall-tears arms-spread` ≠ `single-teardrop hands-clasped`.

3. **Cells 9 and 13 must differ in both emotion axis AND body posture.** Write them side by side before finalising the list and check they are visually distinguishable.

4. **Vary facing direction and limb action across rows.** Cells in the same column naturally echo each other; counteract by alternating pose direction (facing left vs. right) or prop presence.

**Reference 16-slot layout (copy and customize):**

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

## Grid Slicing: Auto-Detect Boundaries

Gemini does **not** divide the canvas into equal 512×512 cells. Row/column heights vary (e.g., top row 550px vs. bottom row 480px). Hard `image_size / 4` cuts cause sticker overflow into adjacent cells.

**Fix:** compute per-row and per-column white-fraction profiles, find contiguous near-white runs (gap bands), take their midpoints as cut positions.

```python
dist = np.max(np.abs(rgb.astype(np.int16) - 255), axis=2)  # 0 = white
near_white = dist < WHITE_TOL
row_profile = near_white.mean(axis=1)   # fraction of white per row
col_profile = near_white.mean(axis=0)   # fraction of white per col
# find runs where profile >= 0.98 → midpoints = cut positions
```

If more gap bands than expected (thin intra-sticker white highlights), keep only the `n_cells-1` most spread-out midpoints. See `scripts/key_alpha.py: _find_cuts()`.

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

## Common Mistakes

| Mistake | Fix |
|---|---|
| Vague accessories (`red ribbon`) | Spell out species/shape (`pink sakura flower, 5 petals`) |
| Uniform expressions (all sad-variants) | Mix action verbs: raised fist, palm-push, tilted head, waterfall tears, thumbs-up |
| Cells 9 and 13 look identical | They share column-1; assign different emotion axis **and** body posture to each — see Expression Diversity Rules |
| Grid lines appear in output | Add `seamless pure white, no grid lines, no cell borders` to prompt |
| Hair color drifts across cells | Repeat exact color spec as first item in "character lock" |
| `image.size` AttributeError | `part.as_image()` returns genai Image, not PIL; convert via `Image.open(io.BytesIO(img.image_bytes))` |
| Adjacent sticker bleeds into cell | Gemini grid is uneven; use `_find_cuts()` white-profile detection, not `image_size // 4` |
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
