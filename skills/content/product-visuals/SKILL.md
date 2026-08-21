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
7. For a web product on Mac, screenshot a real local Safari **window** with its native shadow (`screencapture -l <CGWindowID>`). `--mac` accepts that window only; the compositor supplies the wallpaper and Menu Bar and never adds a second window shadow. Do not paste a webpage screenshot into someone else's Safari chrome. Do not redraw Safari.
8. For iPhone, capture the simulator **framebuffer** with `xcrun simctl io <udid> screenshot`. Never screenshot the Simulator.app window. Never crop a screen out of an already-framed mockup.

## Recipes

| Recipe | When | Status |
| --- | --- | --- |
| `dual-device-hero` | iPhone + Mac window, site hero / 宣传图 | implement |
| `app-store-set` | App Store screenshot set | stub — say so, do not fake it |
| `og-card` | 1200×630 share card | stub |
| `changelog-card` | compact update visual | stub |

Default composition for `dual-device-hero`: 4800×2700, opaque device group centered on the canvas, MacBook Pro 14 Space Black slightly left of that group, iPhone 17 Pro Silver overlapping lower right.

## Workflow

```text
[1] Pick recipe from the request (default dual-device-hero)
[2] Collect --phone (simctl framebuffer PNG) and --mac (real Mac window PNG with native shadow)
[3] Export the official Menu Bar SVG from Apple's macOS UI Kit and cache it with scripts/cache-macos-menu-bar.sh
[4] Let compose.py build the Mac screen as wallpaper -> official Menu Bar -> --mac window
[5] bash scripts/fetch-bezels.sh
[6] Derive background from the app's 调性 (see Background)
[7] uv run scripts/compose.py dual-device-hero --phone … --mac … --bg … --out …
[8] Open the PNG. Confirm UI is readable, no corner overflow, no rectangular plates around devices, background reads as the same product
```

```bash
HERE="<path-to-this-skill>"
bash "$HERE/scripts/fetch-bezels.sh"
bash "$HERE/scripts/cache-macos-menu-bar.sh" "$MENU_BAR_SVG"
uv run "$HERE/scripts/compose.py" dual-device-hero \
  --phone "$PHONE" --mac "$MAC" --bg "$BG" --out "$OUT"
```

Swap background only — same screenshots, new `--bg`:

```bash
uv run "$HERE/scripts/compose.py" dual-device-hero \
  --phone "$PHONE" --mac "$MAC" --bg "$BG" --out "$OUT"
```

`--iphone-color silver|deep-blue|cosmic-orange` and `--mac-color space-black|silver` select cached official bezels.

## Background

The plate is the product's 调性, not a stock cinematic studio. Derive it from the screens (and `DESIGN.md` / tokens if the app repo is known). Do not rebuild device frames to change it.

Yohaku example: 余白, warm parchment `#f9f8f5` / dark desk `#141414`, 梅 `#c56473` ≤5% — paper and ink, not blue volumetric cinema.

| User says | Do |
| --- | --- |
| nothing / default | name the app's palette + material from the screenshots (and DESIGN.md). `image_gen` / `gemini-image-generation`: empty 16:9 plate in that 调性, **no devices, no screens, no text**; then `--bg` |
| cinematic / 更电影 | generic empty studio only when they asked for it |
| here's a file / 用这张底 | `--bg` that file |
| omit `--bg` / generation unavailable | compose.py samples the screenshots into a quiet gradient |
| 换背景 on an existing hero | keep the same `--phone` / `--mac`; new `--bg` still from that app's 调性 |

Generated atmospheres must stay empty. If a model draws a laptop or phone, discard and regenerate.

`--bg-dim 0.88` darkens a too-bright plate. Default is `1.0` (unchanged).

## macOS web presentation

When the Mac screen presents a website, read [references/macos-web-scene.md](references/macos-web-scene.md) before composing it. The `--mac` input is only the real Safari window capture. The compositor builds the privacy-safe desktop scene from separate wallpaper, Menu Bar, and window layers.

## iPhone capture

`--phone` is the device **framebuffer**, not a photo of Simulator.app.

```bash
UDID=$(xcrun simctl list devices booted | awk -F '[()]' '/Booted/{print $2; exit}')
xcrun simctl io "$UDID" screenshot phone.png
```

Accept: a rectangle at the device's native screenshot size (iPhone 17 Pro: **1206×2622**). The status bar and iOS's black island pill are framebuffer pixels; the official bezel supplies the hardware island and camera.

Reject and recapture:

- Simulator.app window (`screencapture`, axe of the window, a display screenshot that includes chassis chrome)
- A crop from an already-framed mockup (camera already in the island, rounded device corners in the PNG)
- Any size other than the booted device's native screenshot pixels

The workflow's "real window capture" is **Mac only**.

## Inputs

| Flag | Meaning |
| --- | --- |
| `--phone` | Simulator framebuffer PNG from `simctl io screenshot` (iPhone 17 Pro: 1206×2622) |
| `--mac` | real app/Safari window PNG with native window shadow; never a full desktop capture |
| `--mac-wallpaper` | optional public wallpaper override; otherwise use the built-in privacy-safe wallpaper layer |
| `--mac-menu-bar` | optional transparent official Menu Bar PNG override; otherwise use the cached macOS 27 UI Kit layer |
| `--bg` | optional background image, any aspect; resized to the canvas |
| `--out` | destination PNG |

Reject a `--mac` capture that includes wallpaper, a desktop corner, the display notch, Dock, notifications, or unrelated windows. Recapture only the target window.

## Verification

Before claiming done:

- Open `--phone` before composing: rectangle at native size, no silver chassis, no camera lens in the island.
- Open the PNG. Read actual UI text on both screens — it must match the source screenshots.
- Check iPhone top-left and both bottom corners: no screenshot rectangle leaking past the silver frame.
- Check the Dynamic Island: one hardware island with the camera. A second black pill beside or below it means `--phone` was not a framebuffer shot, or the island was not covered by the bezel.
- Check around both devices: no darker rectangular plate, no second shadow card on the Mac.
- Check the MacBook display corner against the official bezel: the screen content reaches the official interior mask and has no second inset rounded corner from a desktop screenshot.
- Check the pair as a group: left/right gaps around the **opaque chassis** should match. A left-heavy Mac with empty canvas on the right means the layout used PNG origin instead of the opaque union.
- Background shares the product's palette and material. A blue cinematic void behind a parchment/ink app is wrong.
- For a web product, confirm the browser is genuine Safari, fills roughly 84–90% of the desktop width, and contains no private browser or desktop data.
- Confirm Safari has one native rounded border and one native soft shadow. A second hard or concentric arc means the compositor added or reconstructed a shadow; it must not do so.
- Confirm the Menu Bar is the unmodified official UI Kit export: Apple glyph, outlined typography, status icons, spacing, and date/time must remain coherent.
- If only the background should change, the framed screens must be identical to the previous export.

## Common mistakes

| Mistake | Fix |
| --- | --- |
| Image-model restyles the UI into the devices | Code composite only |
| `alpha < 16` inside the screen bbox as the hole | Use the interior flood-fill mask |
| Gaussian-blur the full bezel image for a drop shadow | Padded contact shadow under the base |
| Resize RGBA without premultiply | Dirty transparent RGB becomes a gray halo |
| Check Apple bezels into git | Cache only; `fetch-bezels.sh` |
| Pin Mac at `(150,150)` / center the bezel PNG canvas | Center the opaque-union; 14" Mac mockups have ~230px empty top pad |
| Default to cinematic blue-rose studio | Read the screens (and DESIGN.md). Generate or sample from the app |
| Pass a full desktop screenshot as `--mac` | Pass only the target window; let the compositor own wallpaper and Menu Bar layers |
| Hand-draw Safari or paste a site shot into another window's chrome | Resize the live Safari window, capture that real window, and composite its PNG with alpha |
| Add a drop shadow around the Safari PNG | Keep the native `screencapture -l` shadow; the compositor adds no window shadow |
| Repair rounded corners from a desktop screenshot | Remove that code path; a wallpaper-first rectangular scene has no baked display corners |
| Recreate the Menu Bar with local fonts or hand-drawn icons | Export the official component from Apple's macOS UI Kit and cache it with `cache-macos-menu-bar.sh` |
| Screenshot of Simulator.app, or a crop from a framed mockup | `xcrun simctl io <udid> screenshot` at native size |
| Two Dynamic Islands / camera floating next to a black pill | Recapture with simctl; do not feed an already-framed PNG as `--phone` |
