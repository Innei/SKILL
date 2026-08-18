---
name: product-visuals
description: >
  Use when the user wants a product marketing image from real macOS or iOS
  screenshots — dual-device hero, device-framed mockup, 宣传图, 产品图, 机型边框,
  App Store screenshots, OG card, changelog card, or to swap the background of
  an existing device mockup. Also when they run /product-visuals.
---

# Product Visuals

Compose product marketing stills from **real app screenshots** inside official Apple device bezels. Background is a separate layer and can be swapped without re-framing the screens.

## Capability contract

- **Outcome:** a 16:9 (or requested) PNG with iPhone / MacBook frames and pixel-accurate UI
- **Preconditions:** iPhone screenshot and/or macOS window screenshot; network once to fetch Apple bezels
- **Boundaries:** do not invent or redraw UI; do not implement `app-store-set` / `og-card` / `changelog-card` in this version (route only)

## Iron rules

1. Never send product screenshots through an image model. Frames and composite are local code.
2. Never commit or vendor Apple Design Resource PNGs/DMGs. Fetch to `~/.cache/product-visuals/bezels/`.
3. Clip the screenshot to the **interior screen mask**, not the hole's bounding box (bbox corners sit outside the rounded device).
4. Zero RGB on fully transparent bezel pixels and premultiply before LANCZOS resize.
5. Shadows are padded contact shadows under the chassis. Do not blur the full bezel canvas — that stamps a rectangular plate.

## Recipes

| Recipe | When | Status |
| --- | --- | --- |
| `dual-device-hero` | iPhone + Mac window, site hero / 宣传图 | implement |
| `app-store-set` | App Store screenshot set | stub — say so, do not fake it |
| `og-card` | 1200×630 share card | stub |
| `changelog-card` | compact update visual | stub |

Default composition for `dual-device-hero`: 4800×2700, MacBook Pro 14 Space Black slightly left, iPhone 17 Pro Silver overlapping lower right.

## Workflow

```text
[1] Pick recipe from the request (default dual-device-hero)
[2] Collect --phone and --mac paths (uploads, Desktop simulator PNG, or window capture)
[3] bash scripts/fetch-bezels.sh
[4] Choose background (see below)
[5] uv run scripts/compose.py dual-device-hero --phone … --mac … --out …
[6] Open the PNG. Confirm UI is readable, no corner overflow, no rectangular plates around devices
```

```bash
HERE="<path-to-this-skill>"
bash "$HERE/scripts/fetch-bezels.sh"
uv run "$HERE/scripts/compose.py" dual-device-hero \
  --phone "$PHONE" --mac "$MAC" --out "$OUT"
```

Swap background only — same screenshots, new `--bg`:

```bash
uv run "$HERE/scripts/compose.py" dual-device-hero \
  --phone "$PHONE" --mac "$MAC" --bg "$BG" --out "$OUT"
```

`--iphone-color silver|deep-blue|cosmic-orange` and `--mac-color space-black|silver` select cached official bezels.

## Background

Treat background as its own input. Do not rebuild device frames to change it.

| User says | Do |
| --- | --- |
| nothing | omit `--bg` — script paints a dark studio fallback |
| cinematic / 更电影 / 换氛围 | `image_gen` or `gemini-image-generation`: empty 16:9 studio, **no devices, no screens, no text**; then `--bg` |
| here's a file / 用这张底 | `--bg` that file |
| 从截图抽色 | sample dominant colors, generate a quiet gradient, `--bg` |
| 换背景 on an existing hero | keep the same `--phone` / `--mac`, only change `--bg` |

Generated atmospheres must stay empty. If a model draws a laptop or phone, discard and regenerate.

`--bg-dim 0.88` darkens a too-bright plate. Default is `1.0` (unchanged).

## Inputs

| Flag | Meaning |
| --- | --- |
| `--phone` | iPhone screenshot (prefer native simulator PNG, e.g. 1206×2622 for 17 Pro) |
| `--mac` | macOS window or desktop capture; the full desktop+window shot is OK and looks like a real Mac |
| `--bg` | optional background image, any aspect; resized to the canvas |
| `--out` | destination PNG |

If the Mac capture includes wallpaper around a window, use it as-is. Do not crop unless the user wants the app to fill the display.

## Verification

Before claiming done:

- Open the PNG. Read actual UI text on both screens — it must match the source screenshots.
- Check iPhone top-left and both bottom corners: no screenshot rectangle leaking past the silver frame.
- Check around both devices: no darker rectangular plate, no second shadow card on the Mac.
- If only the background should change, the framed screens must be identical to the previous export.

## Common mistakes

| Mistake | Fix |
| --- | --- |
| Image-model restyles the UI into the devices | Code composite only |
| `alpha < 16` inside the screen bbox as the hole | Use the interior flood-fill mask |
| Gaussian-blur the full bezel image for a drop shadow | Padded contact shadow under the base |
| Resize RGBA without premultiply | Dirty transparent RGB becomes a gray halo |
| Check Apple bezels into git | Cache only; `fetch-bezels.sh` |
