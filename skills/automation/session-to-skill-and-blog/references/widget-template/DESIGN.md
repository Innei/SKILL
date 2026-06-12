# Dynamic widget design guide — Yohaku article language

A `<dynamic>` widget renders inside a shadow root embedded in a Yohaku
article. It must read as a native article block — same restraint as the
alert/banner/details/code-card treatments — not as a third-party iframe.
`template.mjs` in this directory is a working skeleton that already follows
every rule below; start from it.

## Token strategy: self-contained, snapshot-not-subscription

**Widgets must not read host CSS variables.** Although custom properties
pierce shadow roots, depending on `--color-neutral-*` / `--color-accent` /
`--rc-*` makes every deployed widget a silent subscriber to the host's
token names — rename a token on the site and widgets in the wild break.
Widgets are immutable versioned assets; their styling must be equally
immutable.

Instead, **snapshot** the Yohaku article language into internal `--w-*`
tokens with literal values, and switch dark values via `data-theme`
(driven by `host.theme` from the mount protocol — the only theming
contract a widget may rely on):

```css
.widget {
  --w-text: #24231f;      /* neutral-9 */
  --w-text-2nd: #787670;  /* neutral-6 */
  --w-border: #e3e1db;    /* neutral-3 */
  --w-surface: #f9f8f5;   /* neutral-1 */
  --w-accent: #c56473;    /* rose */
}
.widget[data-theme='dark'] {
  --w-text: #e8e8e8;
  --w-text-2nd: #8f8f8f;
  --w-border: #404040;
  --w-surface: #141414;
  --w-accent: #e095a4;
}
```

Use only `--w-*` inside component rules; never hardcode a color twice. If
the site's visual language evolves, publish a new widget version with a
fresh snapshot — old articles keep their old, coherent look.

## Visual rules

| Aspect | Rule | Value |
| --- | --- | --- |
| Card | hairline border, generous radius, **no drop shadow** | `1px solid --w-border`; radius `12px`; background `--w-surface` at most (often transparent) |
| Eyebrow label | uppercase micro-caption identifies the widget | `10px`, weight 500, `letter-spacing: 0.08em`, `text-transform: uppercase`, color `--w-text-2nd` |
| Body text | article base scale | `14px / 1.57`, color `--w-text` |
| Numbers | tabular | `font-variant-numeric: tabular-nums`, mono stack for readouts |
| Accent | one accent only — state/result/focus, never decoration | `--w-accent` (rose); semantic green/red only for correct/wrong feedback |
| Buttons / fields | bordered, transparent bg, radius 8px | hover: border darkens one tier (`--w-text-2nd`); active: `translateY(1px)`; no scale/rotate |
| Depth | flat | tint via `color-mix(in srgb, --w-accent 8%, transparent)` for selected states; no blur/glass |

## Motion rules

- Hover/state transitions: `200ms ease` on `border-color`, `background-color`, `color`.
- Content reveal (result rows, expanding feedback): `250–350ms cubic-bezier(0.4, 0, 0.2, 1)`.
- No bounce/overshoot inside article widgets.
- Honor `prefers-reduced-motion: reduce` — collapse transitions to none.

## UX rules (protocol-coupled)

1. **Height contract.** `initialHeight` in the catalog is the box's
   permanent floor. Design the resting state to exactly that height; grow
   only downward and only in response to user action (input-driven growth
   is CLS-exempt). Never shrink.
2. **Theme is pushed.** `update({ props, host })` re-fires on theme switch.
   Re-apply `data-theme`; do not reset user interaction state on a pure
   theme change (compare props JSON before resetting — see template).
3. **Self-contained.** Inject one `<style>` into `container.getRootNode()`.
   No external fonts, no network requests, no document.head access.
4. **Interaction-first.** The widget exists because the reader's action
   carries the lesson (see `../node-usage.md`). The primary control must be
   visible in the resting state — no "click to start" curtains.
5. **Recoverable.** Any terminal state offers an inline reset
   ("Try again" — 12px, dashed-underline link style, `--w-text-2nd`).
6. **Keyboard + touch.** Controls are real `<button>`/`<input>` elements;
   visible `:focus-visible` ring (`2px solid --w-accent`, offset 2px);
   touch targets ≥ 32px.
7. **Degrade loudly, not blankly.** If props are malformed, render the
   eyebrow + a one-line message in `--w-text-2nd`, not an empty box.

## Anatomy (the template's skeleton)

```text
┌─ .widget ──────────────────────────────── 1px --w-border, r12, p20 ─┐
│  .eyebrow      PARAMETER EXPLORER          10px caps, --w-text-2nd  │
│  .title        <props.title>               14px/500, --w-text       │
│  .stage        (the interactive surface)   the lesson lives here    │
│  .controls     buttons / slider            8px radius, bordered     │
│  .meta         readout · hint              12px, --w-text-2nd,      │
│                                            tabular numbers          │
└──────────────────────────────────────────────────────────────────────┘
```

Spacing: outer padding `20px`; vertical gap between zones `12px`;
control gap `8px`. Stick to the 4px grid.

## Checklist before cataloging a new widget

- [ ] All colors via internal `--w-*` tokens with literal values — zero
      `var(--color-*)` / `var(--rc-*)` references; dark verified by toggling
      `data-theme`.
- [ ] Resting height equals the `initialHeight` you will write in the catalog.
- [ ] `update()` preserves interaction state on theme-only changes.
- [ ] Focus ring, reduced-motion, ≥32px touch targets.
- [ ] Malformed-props fallback renders a message, not a blank.
- [ ] `propsSchema` in the catalog matches what `apply()` actually reads.
