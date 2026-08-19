---
name: product-visuals
description: >
  Use when the user wants a product marketing image from real macOS or iOS
  screenshots — dual-device hero, device-framed mockup, 宣传图, 产品图, 机型边框,
  privacy-safe Safari or web presentation, App Store screenshots, OG card,
  changelog card, or to swap the background of an existing device mockup. Also
  when they run /product-visuals.
---

# Product Visuals

Compose product marketing stills from **real app screenshots** inside official Apple device bezels. Background is a separate layer and can be swapped without re-framing the screens.

## Capability contract

- **Outcome:** a 16:9 (or requested) PNG with iPhone / MacBook frames and pixel-accurate UI
- **Preconditions:** iPhone screenshot and/or real app/browser window screenshot; network access to fetch Apple resources and public wallpaper when needed
- **Boundaries:** do not invent or redraw UI; do not implement `app-store-set` / `og-card` / `changelog-card` in this version (route only)

## Iron rules

1. Never send product screenshots through an image model. Frames and composite are local code.
2. Never commit or vendor Apple Design Resource PNGs/DMGs. Fetch them under `~/.cache/product-visuals/`.
3. Clip the screenshot to the **interior screen mask**, not the hole's bounding box (bbox corners sit outside the rounded device).
4. Zero RGB on fully transparent bezel pixels and premultiply before LANCZOS resize.
5. Shadows are padded contact shadows under the chassis. Do not blur the full bezel canvas — that stamps a rectangular plate.
6. Never use the user's live desktop, personal wallpaper, notifications, bookmarks, or unrelated windows unless they explicitly request it.
7. For a web product on Mac, capture the real site in Safari. Do not redraw Safari chrome or simulate it with generic rounded rectangles.

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
[2] Collect --phone and --mac paths (uploads, Simulator PNG, or real window capture)
[3] If --mac is a web product, build the privacy-safe macOS desktop scene described below
[4] bash scripts/fetch-bezels.sh
[5] Choose background (see below)
[6] uv run scripts/compose.py dual-device-hero --phone … --mac … --out …
[7] Open the PNG. Confirm UI is readable, no corner overflow, no rectangular plates around devices
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

## macOS web presentation

When the Mac screen presents a website, read [references/macos-web-scene.md](references/macos-web-scene.md) before composing it. The `--mac` input must be the resulting privacy-safe desktop scene: public macOS wallpaper, official Menu Bar components, and a large centered real Safari window.

## Inputs

| Flag | Meaning |
| --- | --- |
| `--phone` | iPhone screenshot (prefer native simulator PNG, e.g. 1206×2622 for 17 Pro) |
| `--mac` | privacy-safe macOS scene or real app window; never default to the user's personal desktop capture |
| `--bg` | optional background image, any aspect; resized to the canvas |
| `--out` | destination PNG |

If a user-supplied Mac capture includes wallpaper, inspect it for private content before using it. Prefer rebuilding a clean desktop scene for public README or marketing output.

## Verification

Before claiming done:

- Open the PNG. Read actual UI text on both screens — it must match the source screenshots.
- Check iPhone top-left and both bottom corners: no screenshot rectangle leaking past the silver frame.
- Check around both devices: no darker rectangular plate, no second shadow card on the Mac.
- For a web product, confirm the browser is genuine Safari, fills roughly 84–90% of the desktop width, and contains no private browser or desktop data.
- Confirm the Menu Bar uses official component geometry and the requested light/dark template color; default to white glyphs and text for product visuals.
- If only the background should change, the framed screens must be identical to the previous export.

## Common mistakes

| Mistake | Fix |
| --- | --- |
| Image-model restyles the UI into the devices | Code composite only |
| `alpha < 16` inside the screen bbox as the hole | Use the interior flood-fill mask |
| Gaussian-blur the full bezel image for a drop shadow | Padded contact shadow under the base |
| Resize RGBA without premultiply | Dirty transparent RGB becomes a gray halo |
| Check Apple bezels into git | Cache only; `fetch-bezels.sh` |
| Use the current Mac desktop as convenient filler | Replace it with a public macOS wallpaper and a clean desktop scene |
| Hand-draw Safari or make it too small | Capture real Safari and center it at about 88% desktop width |
| Recreate the Menu Bar from memory | Start from Apple's macOS UI Kit component and tint its template pixels |
