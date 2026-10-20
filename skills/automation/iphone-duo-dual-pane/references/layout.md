# iPhone Duo — container nesting and layout

How `UINavigationController` and `UIArrangementViewController` behave when
nested: where every bar item goes, how panes are sized in each posture and
arrangement, where sheets, popovers and the keyboard land, how edge-swipe pop
resolves, and what shows on which display after fold and unfold.

Measured on the iPhone Duo simulator (iOS 27.1) on 2026-10-20/21 with a
dual-pane test harness (a native debug screen driven by deep links). Frames are
window points, `{x, y, width, height}`, from debug logs or the accessibility
tree. Display sizes and the safe-area column are in `device.md`. React Native
specifics (react-native-screens bars, RN presentations, locked library
versions) are in `react-native.md`.

Postures used below:

- **Half-open**: book posture, held landscape, 951 × 669, 40 pt division gap.
- **Flat**: fully open, landscape, 951 × 669, no gap.
- **Folded**: outer display, 466 × 678.
- **Portrait**: fully open, rotated 90°, 669 × 951.

## The verified hierarchy

```
UIWindow
└─ UINavigationController                       outer stack
   ├─ ArrangementPage (UIViewController)         outer root (also tested at depth 2)
   │  └─ UIArrangementViewController
   │     ├─ .primary   → UINavigationController   inner stack A
   │     └─ .secondary → UINavigationController   inner stack B
   └─ FullPage (UIViewController)                pushed on the outer stack
```

Both plain UIKit navigation controllers and react-native-screens stacks (in an
RN surface) were run in the placements. A `UISplitViewController` in
`.secondary` was also run (see Arrangements).

## Bar item placement

### Panes that touch the right column

This covers the secondary pane in landscape, an outer-stack page, and primary
on the outer display. UIKit moves bar items out of the bar and into the right
safe-area column as 38 × 38 buttons, stacked from the top:

| Slot | Inner (landscape) | Outer display |
| --- | --- | --- |
| Status (time, connectivity) | y ≈ 30–96 | y ≈ 86–150 |
| 1st collected item | `{884, 129, 38, 38}` | `{399, 179, 38, 38}` |
| 2nd collected item | `{884, 189, 38, 38}` | `{399, 239, 38, 38}` |

- Order: the back button first, then the `UIBarButtonItem` trailing items.
  With no back (stack root), the first trailing item takes slot 1.
- **Overflow:** when the pane's column segment is too short, the rest collapse
  into a `•••` button below the back. Seen in the folded default split: the
  top pane (339 pt tall) showed back + `•••`, with `★` and share inside the
  menu.
- **Custom-view items are not collected.** They stay in the bar, ending at the
  column edge (frames in `react-native.md`).
- The title moves to the leading edge of the bar (x ≈ 20 into the pane).
- **Large title**: because the bar row is now empty, the large title sits in
  the first row (`{515.7, 31, 158, 34}` in the secondary pane). The search bar
  goes below it (y 82–136), ending at the column edge. Pane
  `safeAreaInsets.top` is 136 at the root (82 after a push).
- **Bottom toolbar**: leading items stay leading (`{520.7, 602, …}`); the
  trailing item is aligned to the column's x (`{884, 602, 38, 38}`; outer
  display `{399, 611, 38, 38}`). Pane `safeAreaInsets.bottom` is 82.

### Panes that do not touch the column

This is the primary pane in landscape and any pane in portrait. The bar behaves
as on an iPhone:

- UIKit back is a 48 × 48 chevron at `{20, 24}` (react-native-screens keeps
  the back title; see `react-native.md`).
- Trailing `★` stays in the bar: `{391.7, 28, 40, 40}` half-open,
  `{411.7, 28, 40, 40}` flat, `{481, 28, 40, 40}` in portrait, where it ends
  next to the status glyphs in the same row.
- The title is centered when a back button is present.
- **Large title** gets its own row: `{20, 85.7, 146.7, 40.7}`, with the search
  bar below at y ≈ 134–188. Root `safeAreaInsets.top` is 188.
- **Search active**: the search field takes the bar row with a close button
  (`{391.7, 24, 44, 44}`), the large title disappears, and the trailing bar
  item **moves into the bottom toolbar's leading slot** (`★` at `{25, 602}`,
  pushing `Tool` to `{85, 602}`).

### Outer bar shown over the arrangement page (avoid)

| | Inner | Outer display |
| --- | --- | --- |
| Outer bar | full width, title leading at x 20 | same |
| Pane bars | pushed down to y 82 | pushed down to y ≈ 58–140 |
| Pane `safeAreaInsets.top` | 82 | 82 |
| Outer trailing item | column slot 1, `{884, 129}` | `{399, 179}` |
| Pane back the column collects | pushed lower, to `{884, 211}` | pushed lower, to `{399, 261}`, over content |

The outer bar costs 82 pt and pushes the pane's collected items over content.
Hide it while the arrangement page is on top.

## Pane geometry by arrangement and posture

`P` = primary, `S` = secondary.

| Arrangement | Half-open | Flat | Folded | Portrait |
| --- | --- | --- | --- | --- |
| `.split.axes(.horizontal)` | P `{0,0,456,669}`, S `{496,0,455,669}` | P `{0,0,476,669}`, S `{476,0,475,669}` | P only `{0,0,466,678}` | P only `{0,0,669,951}` |
| `.split` (default) | same as above | same as above | stacked: P `{0,0,466,339}`, S `{0,339,466,339}` | stacked: P `{0,0,669,476}`, S `{0,476,669,475}` |
| `.split`, P width `.fractional(0.35)`, `.axes(.horizontal)` | **ignored**: 456 / 455 | P `{0,0,333,669}`, S `{333,0,618,669}` | P only | P only |
| `.overlay`, `.overlay.axes(.horizontal)` | side by side, **swapped**: S `{0,0,456,669}`, P `{496,0,455,669}` | both `{0,0,951,669}`, P on top (`zIndex` 1) | both full, P on top | both full, P on top |
| `.overlay`, S `edge = .trailing` | both `{496,0,455,669}`, P on top, left half empty | both full, P on top | both full, P on top | not run |
| `UISplitViewController` in S | S shows the detail column only; sidebar collapsed | not run | P only | not run |

Notes:

- At half-open, the division region forces the split onto the hinge. Width
  preferences only take effect when flat.
- Overlay is a stacking layout. Panes only sit side by side when the hinge
  divides them, and then primary is on the trailing side.
- `state(for:)` reported `splitAxis` `h` for side-by-side, `v` for stacked,
  and `0` for overlay. `zIndex` was 1 for primary in overlay and 0 otherwise.

## Presentations from a pane

The presentation container is always **the whole window**. The source pane does
not scope the sheet, and the dimming covers both panes.

| Style | Half-open | Flat | Folded | Portrait |
| --- | --- | --- | --- | --- |
| `.pageSheet` | `{8,8,460,661}`, **left half**, from either pane | `{149,8,653,661}`, centered on the display | `{8,8,450,670}` | `{8,82,653,869}` |
| `.formSheet`, `.automatic` | `{78,205,320,260}`, centered in the **left half**, from either pane | `{316,205,320,260}`, centered on the display | `{8,8,450,670}` (same card as page) | `{175,346,320,260}` |
| `.popover` (from the `★` bar item) | anchored to the item: P `{136,24,320,240}`; S (item in the column) `{610,184,320,240}` | P `{271,24,…}`; S `{610,184,…}` | adapts to the `{8,8,450,670}` card | not run |
| `.fullScreen` | `{0,0,951,669}`, insets r84 | not run | `{0,0,466,678}` | not run |

- A sheet from the secondary pane at half-open lands **over the primary
  pane**.
- Folding with a sheet from the secondary open: the sheet stays presented and
  moves to the outer display as the `{8,8,450,670}` card over primary, while
  secondary itself is hidden.
- Sheet `safeAreaInsets`: page sheet half-open r0; folded cards r76.

## Keyboard

| | Frame | Notes |
| --- | --- | --- |
| Inner landscape | `{0,405,951,264}` | split keyboard (left and right halves), full width, under the column |
| Outer display | `{0,374,466,304}` | full width |

The bottom toolbar's trailing (column-aligned) item lifts above the keyboard
(inner `{884,354}`, outer `{399,323}`). Leading toolbar items stay where they
are, under the keyboard.

## Interactive pop (edge swipe)

| Swipe | Result |
| --- | --- |
| From the screen's left edge, primary at depth 2 | primary's inner stack pops (`interactive=true`) |
| From the screen's left edge again, primary at its root, outer stack at depth 2 | **nothing pops**. The outer bar is hidden on the arrangement page, which disables the outer interactive pop. |
| From the secondary pane's left edge (right of the hinge), secondary at depth 2 | secondary's inner stack pops (`interactive=true`) |

## Outer push and what shows on which display

The controller on top of the outer stack stays on top through fold and unfold;
only its geometry changes.

| Top of the outer stack | Unfolded | Folded |
| --- | --- | --- |
| Arrangement page | per the geometry table | per the geometry table |
| Full page | full width (951; content 867), back in column slot 1, insets 82/0/34/84 | full width (466; content 382), back in column slot 1 |

Transitions verified, each with the same process and no JS reload:

| Start | Action | Result |
| --- | --- | --- |
| Arrangement, both panes at depth 2 | fold → unfold | folded shows primary at depth 2; unfolded shows both at depth 2, no remount |
| Arrangement, folded | push full page → unfold | the full page stays on top and widens |
| Full page, unfolded | pop | both panes return at depth 2 |
| Full page, unfolded | fold | the full page stays on top and narrows |
| Full page, folded | pop | primary at depth 2; secondary hidden |
| Sheet from secondary, half-open | fold | the sheet stays, as a card over primary |

## Boundary rules

1. Hide the outer bar while the arrangement page is on top. Show it on
   full-width pages, which also keeps their edge-swipe back working.
2. Use `UIBarButtonItem`s for bar actions so UIKit can move them into the
   column. A custom-view item stays in the bar and narrows the title area.
3. Keep column-adjacent panes to at most one trailing bar item, plus the back
   button. More than that risks the `•••` overflow on short panes.
4. Do not assume a sheet stays over its pane. At half-open every page or form
   sheet lands on the left half; flat, it is centered across both panes.
   Content shown in a sheet from secondary must make sense over primary.
5. A sheet left open in secondary survives a fold and covers primary. Decide
   per flow whether to dismiss it when secondary hides; the current product
   rule is to follow the system.
6. Detect secondary visibility with `view.window == nil`, not
   `state(for:)?.isHidden` alone.
7. Do not rely on width preferences: half-open always splits at the hinge.
8. Use `.overlay` only for content that is meant to cover the other pane;
   it is full-screen stacking except at half-open.
9. Anything that must work while folded lives in primary or on the outer stack.
10. In portrait, the column is gone and bar items return to the bar; with
    `.axes(.horizontal)` only primary is shown.
11. Each pane's insets differ by placement and posture. Read them per pane;
    never reuse window insets.

## Unverified

- `.fullScreen` and `UISplitViewController` in flat and portrait;
  `overlay-edge` and popovers in portrait.
- The outer display rotated to landscape.
- Everything on hardware.
