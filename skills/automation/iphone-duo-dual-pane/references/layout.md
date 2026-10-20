# iPhone Duo — container nesting and layout

How `UINavigationController` and `UIArrangementViewController` behave when
nested, where each bar and action ends up, and what shows on which display
after fold and unfold. Measured on the iPhone Duo simulator (iOS 27.1) with a
dual-pane test app on 2026-10-20 and 2026-10-21. Device numbers (display sizes,
safe-area column) are in `device.md`.

## The verified hierarchy

```
UIWindow
└─ UINavigationController                       outer stack
   ├─ ArrangementPage (UIViewController)         root of the outer stack
   │  └─ UIArrangementViewController             .split.axes(.horizontal)
   │     ├─ .primary   → host VC → UINavigationController   inner stack A
   │     └─ .secondary → host VC → UINavigationController   inner stack B
   └─ FullPage (UIViewController)                pushed on the outer stack
```

In the test app, each host VC's view is a React Native surface whose
react-native-screens native-stack provides the inner `UINavigationController`.
Plain UIKit navigation controllers in the placements are expected to behave the
same way, but that is **unverified**.

## 1. Navigation controller outside an arrangement

The outer controller treats the two panes as one page: pushing replaces both,
and popping brings both back.

### Outer bar hidden while the arrangement page is on top (use this)

- Each pane's own bar sits at the top of its pane (y 0). Every action on screen
  belongs to a pane.
- The arrangement page's `navigationItem` (title, bar items) is not shown.
- Hide the outer bar in `navigationController(_:willShow:animated:)` when the
  incoming controller is the arrangement page. Show it for full-width pages.

### Outer bar shown over the arrangement page (avoid)

The two bars stack vertically:

| | Inner display | Outer display (folded) |
| --- | --- | --- |
| Outer bar | full width, title leading at x 20 | full width, title leading at x 20 |
| Pane bars | pushed down to y 82 | pushed down to y ≈ 58–140 |
| Pane `safeAreaInsets.top` | 82 | 82 |
| Outer trailing item (`+`) | collected into the right column at `{{884, 129}, {38, 38}}` | collected into the right column at `{{399, 179}, {38, 38}}` |
| Pane back that the column collects | pushed lower, to `{{884, 211}, …}` | pushed lower, to `{{399, 261}, …}`, **over content** |

Results:

- 82 pt of height goes to a bar that carries no pane-specific actions.
- The right column becomes a vertical queue. The outer bar's items take the
  first slot and push the pane's back button down until it overlaps content.
- Trailing items of the pane bars stay in their bars, ending at the column's
  edge (secondary `★` at x 825–861, primary `★` at x 393–429 when half open).

## 2. Navigation controller inside an arrangement placement

Each placement gets its own push stack and its own bar.

| | Primary pane (inner) | Secondary pane (inner) | Primary on the outer display |
| --- | --- | --- | --- |
| Back action | stays in the bar, leading, with its title (`{{20, 24}, {132.7, 48}}`) | collected into the right column (`{{884, 129}, {38, 38}}`) | collected into the right column (`{{399, 179}, {38, 38}}`) |
| Title | centered while the back stays in the bar | leading (x ≈ 20 into the pane) | leading |
| Trailing items | in the bar | in the bar, ending at the column edge (861) | in the bar, ending at the column edge (376) |
| `safeAreaInsets` (t / l / b / r) | 0 / 0 / 34 / 0 | 0 / 0 / 34 / 84 | 0 / 0 / 34 / 84 |

- Push and pop in one pane never touch the other pane's stack.
- Bars respect the right inset by themselves; content does not. Apply
  `safeAreaInsets.right` in each pane's content.
- With the default `.split` (no axis limit), folded, the panes stack top and
  bottom (≈ 325 pt each). The top pane's collected back button then lands over
  its content (≈ `{{416, 194}}`). This is another reason to limit the axis to
  `.horizontal`.

## 3. Outer push over the panes

- A page pushed on the outer stack covers both panes on the inner display
  (951 pt wide, content 867) or the whole outer display (466 pt, content 382).
- Its back action is collected into the right column, and its title is
  leading. The outer bar is shown; the page's `safeAreaInsets` are
  82 / 0 / 34 / 84.
- Popping returns to the arrangement page with both inner stacks exactly as
  they were (verified at depth 2 with no remount).

## 4. What shows on which display

The display only decides geometry. The controller on top of the outer stack
stays on top through fold and unfold.

| Top of the outer stack | Unfolded (inner, 951 × 669) | Folded (outer, 466 × 678) |
| --- | --- | --- |
| Arrangement page, `.split.axes(.horizontal)` | primary and secondary side by side; 40 pt gap when half open, none when flat | **primary only**; secondary hidden but alive |
| Arrangement page, `.split` (default) | side by side | stacked top and bottom |
| Full page on the outer stack | full inner width | full outer width |

Transitions verified, each with the same process and no JS reload:

| Start | Action | Result |
| --- | --- | --- |
| Arrangement, unfolded, both panes at depth 2 | fold → unfold | folded shows primary at depth 2; unfolded shows both at depth 2, `mounts: 1` |
| Arrangement, folded | push full page → unfold | the full page stays on top and widens to 951 pt |
| Full page, unfolded | pop | both panes return at depth 2 |
| Full page, unfolded | fold | the full page stays on top and narrows to 466 pt |
| Full page, folded | pop | primary at depth 2, `mounts: 1`; secondary hidden |

## Boundary rules

1. Hide the outer bar whenever the arrangement page is on top. Never show the
   outer bar and the pane bars together.
2. Put an action in the pane it acts on. There is no shared bar for the pair.
3. Push inside a pane for drill-down within that pane. Push on the outer stack
   only for destinations that need the full width.
4. Folded, only primary and the outer stack are reachable. Anything that must
   work while folded lives in primary or in an outer page.
5. Secondary keeps its stack while hidden. Check
   `arrangement.state(for: .secondary)?.isHidden` before doing work that only
   matters while it is visible (polling, streams, animations).
6. Read safe-area insets inside each pane and each outer page; they differ by
   placement and by display. Never hard-code a full-window inset.
7. Never place a manual back button at the top-left of a secondary pane or an
   outer page. The system puts it in the right column.

## Unverified

- Interactive pop (edge swipe) when an inner stack and the outer stack can
  both pop: which one wins in each pane.
- Sheets and popovers presented from an inner navigation controller: their
  width, and their behavior on fold. (Product decision: follow the system.)
- Large titles, search controllers and bottom toolbars in pane bars.
- Plain UIKit `UINavigationController` in a placement (only react-native-screens
  stacks were run).
- `UIOverlayArrangement`, and placing the arrangement somewhere other than the
  outer stack's root.
- Nesting a split view controller inside a placement. Secondary sources relay
  Apple's advice against it.
