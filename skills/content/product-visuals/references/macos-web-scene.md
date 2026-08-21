# macOS Web Scene

Use this procedure when a website must appear inside a MacBook product visual.

## Layer contract

Compose the Mac screen locally in this order:

```text
public or privacy-safe macOS wallpaper
└── official macOS UI Kit Menu Bar layer
    └── real Safari window capture
```

Do not use a screenshot of the user's live desktop as the base layer.

## Source selection

| Layer | Required source | Reject |
| --- | --- | --- |
| Wallpaper | Public, generic macOS wallpaper matching the requested release | Personal wallpaper, current desktop capture, AI-generated imitation when an official/public image exists |
| Menu Bar | Apple macOS UI Kit component exported as transparent SVG and cached as PNG | Programmatic text, hand-drawn icons, live personal Menu Bar capture, mixed-color template |
| Safari | Real local Safari **window** via `screencapture -l <CGWindowID>` of the product URL. Resize the live window so the page reflows; then capture chrome, page, rounded border, and native shadow together | Full desktop screenshot; browser mockup; synthetic chrome; a page screenshot pasted into another Safari window; a capture containing personal tabs or bookmarks |

Keep downloaded Apple Design Resources in `~/.cache/product-visuals/`; never commit them to the project or skill repository.

## Official Menu Bar retrieval

1. Open Apple's official [macOS 27 UI Kit in Figma](https://www.figma.com/community/file/1651309434229735362/macos-27), linked from [Apple Design Resources](https://developer.apple.com/design/resources/).
2. Select the complete `Menu Bar` component and export it as a transparent SVG. Preserve the outlined Apple glyph, labels, status icons, spacing, and date/time.
3. Cache the export with `bash scripts/cache-macos-menu-bar.sh <MenuBar.svg>`. The script stores the source and a 2× transparent PNG under `~/.cache/product-visuals/macos-ui/`.
4. Run the compositor normally. The cached official PNG is the default; `--mac-menu-bar` is only for another official transparent PNG override.

Do not commit the Figma document, exported SVG, or cached PNG. Do not replace outlined labels with local-font text; that recreates the typography mismatch this workflow is intended to prevent.

## Composition defaults

- Use the wallpaper as a full-bleed cover crop.
- Place the Menu Bar flush to the top edge at its native relative height.
- Preserve the official component as a single transparent layer. Do not independently redraw, recolor, or reposition its typography and icons.
- Center the Safari window below the Menu Bar at approximately 88% of desktop width; 84–90% is acceptable.
- Keep the Safari window large enough that the product, rather than the wallpaper, dominates the display.
- Preserve authentic Safari controls, corner radius, border, and native system shadow.
- Capture with `screencapture -l <CGWindowID>` after setting the live window's bounds. Do not pass `-o`: the window PNG is responsible for its own shadow. Resize its RGBA pixels with premultiplication and composite it exactly once. Never flatten the window into a rectangle, draw replacement chrome, add a drop shadow, or paste a page-only PNG into a different window's traffic lights and toolbar.
- Remove the pointer from the capture or park it outside the visible product region before capture.

## Capture hygiene

Before capture, close or hide unrelated tabs, favorites, bookmarks, downloads, notifications, account names, local paths, and other windows. Use the public product URL when available. Do not expose the user's desktop wallpaper merely because a full-screen capture is convenient.

## Verification

Open the desktop scene before placing it in the MacBook bezel and confirm:

- the Apple glyph, menu labels, status icons, and date/time form one coherent Menu Bar;
- the requested Menu Bar color is applied to all template elements, with no mixed black/white remnants;
- Safari is visibly genuine and occupies most of the usable desktop;
- Safari has one rounded border and one soft native shadow. A second hard or concentric arc means a shadow was synthesized or composited twice;
- all four desktop corners are wallpaper pixels before the official MacBook interior mask is applied; no source screenshot owns the display corners;
- the wallpaper is generic and contains no user-specific content;
- no cursor, notification, unrelated app, or browser identity data remains.
