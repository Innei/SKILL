# macOS Web Scene

Use this procedure when a website must appear inside a MacBook product visual.

## Layer contract

Compose the Mac screen locally in this order:

```text
public macOS wallpaper
└── official macOS Menu Bar component
    └── real Safari window capture
```

Do not use a screenshot of the user's live desktop as the base layer.

## Source selection

| Layer | Required source | Reject |
| --- | --- | --- |
| Wallpaper | Public, generic macOS wallpaper matching the requested release | Personal wallpaper, current desktop capture, AI-generated imitation when an official/public image exists |
| Menu Bar | Apple macOS UI Kit component exported as transparent PNG | Hand-drawn Apple glyph, guessed status icons, fake menu geometry |
| Safari | Real Safari screenshot of the product URL | Browser mockup, synthetic chrome, a screenshot containing personal tabs or bookmarks |

Keep downloaded Apple Design Resources in `~/.cache/product-visuals/`; never commit them to the project or skill repository.

## Official Menu Bar retrieval

1. Open Apple's macOS Design Resources and obtain the current macOS UI Kit for Sketch.
2. Export the Menu Bar component over wallpaper as a transparent PNG at 4× into `~/.cache/product-visuals/macos-ui/`.
3. Reuse the official Apple glyph and trailing status group. Render the active Safari menu labels with SF Pro/SFNS while preserving the component's spacing.
4. Treat the exported pixels as an alpha template. Tint every Menu Bar element to the selected color so Apple, text, status icons, and date/time never mix black and white states.

Do not commit the Sketch document or exported PNG. Do not approximate the component when the official UI Kit is obtainable.

## Composition defaults

- Use the wallpaper as a full-bleed cover crop.
- Place the Menu Bar flush to the top edge at its native relative height.
- Treat Apple UI Kit icons as template images: preserve alpha and tint the opaque pixels. Use white glyphs and text by default for marketing visuals; use black only when requested or required for contrast.
- Render the active application name and standard Safari menus with SF Pro/SFNS, aligned to the official Menu Bar geometry.
- Center the Safari window below the Menu Bar at approximately 88% of desktop width; 84–90% is acceptable.
- Keep the Safari window large enough that the product, rather than the wallpaper, dominates the display.
- Preserve authentic Safari controls, corner radius, and window shadow.
- Remove the pointer from the capture or park it outside the visible product region before capture.

## Capture hygiene

Before capture, close or hide unrelated tabs, favorites, bookmarks, downloads, notifications, account names, local paths, and other windows. Use the public product URL when available. Do not expose the user's desktop wallpaper merely because a full-screen capture is convenient.

## Verification

Open the desktop scene before placing it in the MacBook bezel and confirm:

- the Apple glyph, menu labels, status icons, and date/time form one coherent Menu Bar;
- the requested Menu Bar color is applied to all template elements, with no mixed black/white remnants;
- Safari is visibly genuine and occupies most of the usable desktop;
- the wallpaper is generic and contains no user-specific content;
- no cursor, notification, unrelated app, or browser identity data remains.
