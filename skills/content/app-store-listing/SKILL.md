---
name: app-store-listing
description: >
  Use when preparing an iOS app for a first App Store listing or a listing
  refresh — App Store Connect questionnaires (age rating, App Privacy,
  encryption, content rights, review notes), zh/ja/en store copy, or framed
  screenshot decks from a real simulator. Also use for /app-store-listing,
  上架, 截图, 营养标签, 年龄分级.
---

# App Store listing

Generate a complete first-listing pack in one run: store copy, official-bezel screenshots, and answered Connect checklists. Do not stop after pretty slides.

## Capability contract

- **Outcome:** a directory the user can paste into App Store Connect (copy + PNGs + questionnaire answers). Optional: push via `asc` after they confirm.
- **Preconditions:** macOS, a runnable iOS build or simulator app, ImageMagick (`magick`), `axe` or `simctl`, and a way to render local HTML (`agent-browser` or equivalent).
- **Boundaries:** does not invent privacy/age answers. Does not submit to Apple until the user confirms. Does not redistribute Apple bezel files.

## Hard rules

- Capture the real app. Never `image_gen` / `image_edit` a fake UI.
- Frame with Apple's Product Bezels only. Never CSS-draw a phone.
- Render slide headlines in HTML/CSS. Image models garble CJK and exact type.
- One locale per deck. Chrome, body content, and headline language must match.
- Do not ship an empty signed-out Settings / Me screen as a marketing slide.
- Do not infer App Privacy answers from the app name or store copy. Read the binary, SDKs, and network calls.

## One-shot workflow

Copy this list and check it off:

```
- [ ] 1. Discover
- [ ] 2. Write listing.md
- [ ] 3. Answer questionnaires
- [ ] 4. Capture simulator screens
- [ ] 5. Compose official-bezel slides
- [ ] 6. Validate
- [ ] 7. Stop (or push after confirm)
```

Output root: `<app>/tmp-asc/` (or the path the user names).

### 1. Discover

Read the app until these are known. Ask only for what the repo cannot answer.

| Need | Where to look |
| --- | --- |
| Display name, bundle id, scheme | `app.config.ts`, `Info.plist`, overlay |
| Who downloads it | locked to one site → write as that author's reader; generic client → say so |
| Privacy / support URLs | overlay, site config |
| Tabs / hero screens | router, official previews, running app |
| Tokens | design system (paper bg, accent, serif) |
| Locales | default `zh-Hans`; add `ja` / `en-US` when asked |
| How to boot iOS | Expo overlay, Metro port, `xcrun simctl`, `axe` |

Default slide set (4): list, long-read, signature screen, secondary feed. Drop any screen that is mock, broken, or empty.

### 2. Write listing.md

Follow [references/listing-fields.md](references/listing-fields.md). Write every locale in one file.

Buyer-facing copy describes what a stranger sees after install. If the binary is locked to one site, do not sell it as a generic CMS client.

### 3. Answer questionnaires

Follow [references/checklists.md](references/checklists.md). Write answers into `tmp-asc/questionnaires.md`. Mark any item `UNKNOWN` instead of guessing.

### 4. Capture

1. Boot the matching simulator. Override the status bar to `9:41`, charged, not showing a lightning bolt if `simctl status_bar` allows it.
2. Force dark or light to match the deck.
3. Point the dev client at **this** app's Metro. Simulator `localhost` is not the Mac; use the LAN IP. `--localhost` binds IPv6-only and will fail.
4. Switch in-app locale, wait for content sync, then shoot. Deep-link with the app scheme when possible.
5. Save `tmp-asc/captures/<locale>/<id>.png` at the device's native pixels (iPhone 17 = `1206x2622`).

### 5. Compose

```bash
bash scripts/ensure-bezel.sh
python3 scripts/measure-bezel.py "$BEZEL_PNG"
python3 scripts/render-slides.py tmp-asc/deck.json
```

`deck.json` lists per-slide title, subtitle, capture path, and locale. The renderer overlays the capture into the official bezel hole, then paints headlines in HTML at `1290x2796`.

### 6. Validate

```bash
python3 scripts/validate-listing.py tmp-asc/listing.md
```

Then visually open every `tmp-asc/out/<locale>/*.png`:

- official metal frame, island, and side buttons present
- no locale mix
- no leftover markdown / mock labels
- no alpha (App Store rejects transparency)

### 7. Push (optional)

Only after the user says to upload:

- copy → `asc metadata`
- slides → `asc screenshots`
- age / encryption / content rights → `asc` public API
- App Privacy → `asc web privacy` (needs an Apple web session)

Dry-run first. Never `asc review submit` without an explicit confirm.

## Companion tools

Install if missing, do not reimplement:

| Job | Tool |
| --- | --- |
| Questionnaire brain | `charleswiltgen/axiom@axiom-app-store-submission` + `@axiom-app-store-ref` |
| Write to Connect | `rorkai/app-store-connect-cli-skills` |
| Pre-submit scan | `truongduy2611/app-store-preflight-skills` |
| Expo build/upload | `expo/skills@eas-app-stores` |

## Red flags

| Excuse | Reality |
| --- | --- |
| "I'll generate the UI with Imagine" | Fake UI is a 2.3.3 rejection. Recapture. |
| "A CSS phone is close enough" | Use Apple bezels. |
| "Privacy labels can wait" | First submit blocks without a published App Privacy record. |
| "Me screen shows the product" | Signed-out settings is not a benefit slide. |
| "English chrome + Chinese body is fine" | Reshoot that locale. |

## Verification

- [ ] `listing.md` exists for every requested locale; `validate-listing.py` exits 0
- [ ] `questionnaires.md` has no silent blanks (only answers or `UNKNOWN`)
- [ ] `out/<locale>/` has 4 PNGs at `1290x2796`, no alpha
- [ ] Each slide uses the official bezel and matching-locale capture
