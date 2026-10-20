---
name: iphone-duo-dual-pane
description: Build, lay out, or verify an iOS app on iPhone Duo (foldable, iOS 27.1+). Use when work touches the inner/outer displays, the dual-pane UIArrangementViewController container, the right status safe area and collected back button, hinge or fold/unfold behavior, hosting extra React Native surfaces, or driving the iPhone Duo simulator.
---

# iPhone Duo dual-pane

Measured facts live in two references. Read them before choosing a size, an
inset, or where a bar item goes; do not re-probe what they already record.
Facts marked **unverified** still need a run.

## Rules that hold everywhere

- Inner display is **951 × 669 pt landscape**; outer is **466 × 678 pt
  portrait**. A portrait lock in the app manifest does not apply to the inner
  display.
- Status lives in an **84 pt right safe-area column** on both displays. Lay
  content out inside `safeAreaInsets.right`: the secondary pane has 371 pt, an
  outer-stack page 867 pt, primary on the outer display 382 pt.
- Never draw a back button at the top-left of a page or pane that touches the
  right column. UIKit collects the back and `UIBarButtonItem` trailing items
  into the column (38 × 38, stacked below the status); custom-view items stay
  in the bar. Too many items overflow into `•••`.
- Sheets are window-scoped: at half-open they land on the left half from
  either pane; flat they center across both panes; a sheet left open in
  secondary survives a fold.
- Half-open leaves a 40 pt division gap between panes and overrides width
  preferences; flat leaves none. Let `UIArrangementViewController` handle it.
- Folded shows primary only (`.split.axes(.horizontal)`); secondary is hidden,
  not released. The top of the outer stack stays on top through fold and
  unfold.
- Hide the outer navigation bar while the arrangement page is on top; showing
  it stacks two bars and pushes collected back buttons over content.
- Inside a pane, `useWindowDimensions()` is the whole window. Use pane size.
- Each extra RN surface: created with `ExpoReactRootViewFactory.superView(…)`,
  splash `loadingView` replaced, its own `SafeAreaProvider`, its own
  `AppRegistry` root. Never a second `ExpoRoot`.

## Verifying on the simulator

1. Fold and unfold need a person; no CLI changes posture. Ask, then wait.
2. Find the display UUID with `xcrun simctl io <udid> enumerate` (inner
   `Default width: 2007`, outer `1398`) and screenshot with
   `--display=<UUID>`. UUIDs change on every boot.
3. Read frames with `axe describe-ui`; drive flows with deep links, not
   `axe tap`.
4. Record new measurements in `references/device.md`, replacing the
   **unverified** marker they resolve.

## References

- `references/device.md`: displays, the safe-area column, bar item rules,
  hinge and postures, RN surface hosting, simulator tooling.
- `references/layout.md`: navigation controller outside and inside
  `UIArrangementViewController`, outer pushes, which display shows what after
  fold and unfold, and the boundary rules for nesting.
