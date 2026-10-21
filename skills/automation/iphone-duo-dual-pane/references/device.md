# iPhone Duo — device reference

Measured on the iPhone Duo simulator while building a dual-pane iOS app
(2026-10-20). Use these numbers instead of re-probing. Anything marked
**unverified** was not measured; anything marked **SDK** comes from the iOS
27.1 headers, not from a run.

Environment: Xcode 27.1 (27A9275), simulator runtime iOS 27.1 (24A94232 and
24A94425), device type `com.apple.CoreSimulator.SimDeviceType.iPhone-Duo`, scale
@3x.

## Displays

| | Outer (folded) | Inner (unfolded) |
| --- | --- | --- |
| Panel pixels (native orientation) | 1398 × 2034 | 2007 × 2853 |
| App window in points | **466 × 678**, portrait | **951 × 669**, landscape |
| Orientation the app gets | portrait | landscape, even with a portrait-only orientation setting in the app manifest |

- The inner panel is portrait-native; UIKit rotates it so the app is laid out
  landscape. The accessibility tree reports the app element as `669 × 951`
  while every child frame is in landscape (`951 × 669`) coordinates.
- Third-party spec sheets list 5.4″ / 7.6″ and 1878 × 2670 for the inner
  display. The simulator does not match those; trust the table above.
- `simctl io <udid> enumerate` also lists two 720 × 480 ports and a
  7680 × 4320 port. They are not the device's screens.

## Status region and safe area

There is no status bar across the top. Time and connectivity sit in a column
on the **right edge** of whichever display is active, and that column is the
right safe area.

| | Inner, secondary pane | Inner, primary pane | Inner, outer-stack page | Outer display (primary) |
| --- | --- | --- | --- | --- |
| `safeAreaInsets` (t / l / b / r) | 0 / 0 / 34 / **84** | 0 / 0 / 34 / 0 | 82 / 0 / 34 / **84** | 0 / 0 / 34 / **84** |
| Usable content width | **371 pt** (pane ≈ 455) | ≈ 455 pt | **867 pt** | **382 pt** |

The page row's top inset of 82 is the native navigation bar it sits under. The
pane rows read 0 because they lay out under their own bars.

Held portrait while unfolded (669 × 951), the status region moves to the
top-right of the first bar row and the right column disappears: page
`safeAreaInsets` 82 / 0 / 34 / 0.

Right column contents (all in window points):

| | Inner | Outer |
| --- | --- | --- |
| Column | x 867–951, full height | x 382–466, full height |
| Time | y ≈ 30–50 | y ≈ 86–100 (below the navigation bar row) |
| Connectivity glyph | y ≈ 56–96 | y ≈ 108–150 |
| Collected back button | frame `{{884, 125–129}, {38, 38}}` | frame `{{399, 179}, {38, 38}}` |

## Navigation bars

Full rules, frames and nesting cases are in `layout.md`. In short:

- Bar items that would sit next to the right column (the secondary pane, an
  outer-stack page, primary on the outer display) are collected into the
  column as 38 × 38 buttons, stacked top to bottom: back first, then
  `UIBarButtonItem` trailing items. When the column segment runs out of room,
  the rest go into a `•••` overflow button.
- Custom-view bar items are not collected; they stay in the bar and end at
  the column's edge. React Native specifics are in `react-native.md`.
- Bars respect the inset; **content does not unless asked**. Every RN surface
  root needs its own `SafeAreaProvider` and must apply the right inset.

## Hinge and postures

| Posture | Inner layout | Gap between panes |
| --- | --- | --- |
| Half-open book, held landscape | two panes, ≈ 455.7 + 455.3 pt | **40 pt** at the center (x 455.7–495.7) |
| Flat | two panes, ≈ 475.5 pt each | none |
| Closed | outer display only | n/a |

- The 40 pt gap is the active **division** reserved region; it disappears when
  flat. `UIArrangementViewController` handles it with no app code.
- The hinge angle was not measured. **SDK:** `UIHingeInteraction(updateHandler:)`
  delivers `UIHingeInteractionUpdate.hinge` (`nil` on devices without a hinge)
  with `status` (`unknown`, `closed`, `partiallyOpen`, `fullyOpen`) and `angle`
  in radians. Apple's guidance is to use it for effects, not layout.
- **SDK:** `UIView.reservedRegions(kind:options:)` with kinds `.division`
  (the fold, active only when partially open) and `.occlusion` (camera, active
  only while it is in use); `.includeInactive` returns the fold even when
  flat. Each region has `frame`, `margins` and `isActive`. Not called during
  the measurement run, so its values are **unverified**.

## Fold and unfold behavior

- The app process survives both directions (same pid). There is no JS reload.
  UIKit logs `Disconnecting screen` two or three times per transition.
- Folding while unfolded content is on screen moves the app to the outer
  display. Unfolding moves it back to the inner display.
- `UIArrangementViewController` with the default `.split`: split left/right on
  the inner display; **stacked top/bottom** on the outer display (each half
  ≈ 325 pt tall).
- With `.split.axes(.horizontal)`: the outer display shows **primary only**.
  The secondary view controller is hidden, not released, and returns unchanged
  on unfold. `state(for: .secondary)?.isHidden` reads `true` after a fold, but
  read `false` when the page was first presented while already folded (its
  view was not in a window). Check `view.window == nil` instead.
- Verified across unfold → fold → unfold: both panes' navigation stacks (depth
  2) and React state survived, with no remount.

## UIArrangementViewController (SDK, iOS / tvOS / visionOS 27.1)

```swift
let arrangement = UIArrangementViewController()
arrangement.setViewController(primaryVC, for: .primary)
arrangement.setViewController(secondaryVC, for: .secondary)
arrangement.updateArrangement(.split.axes(.horizontal))
```

- `setViewController(_:for:animated:)`, `viewController(for:)`,
  `placement(for:)`, `state(for:) -> ViewState?` (`zIndex`, `splitAxis`,
  `isHidden`), `updateArrangement(_:animated:)`.
- Placements: `.primary`, `.secondary` (ObjC also has `None`).
- `UISplitArrangement` (`.split`): `axes`, and per-placement view properties —
  `width` / `height` as `DimensionRange` (`minimum`, `preferred`, `maximum`,
  each `.automatic`, `.intrinsic`, `.fractional(_)`, `.absolute(_)`) plus
  `layoutPriority`.
- `UISplitArrangement` and `UIOverlayArrangement` (`.overlay`) both take
  `axes(_:)` and `setViewProperties(_:for:)`. Measured behavior of both is in
  `layout.md`.
- `UIViewController.arrangementViewController` finds the enclosing container.
- Apple places a navigation container *outside* the arrangement. Two
  independent push stacks work by putting a navigation controller inside each
  placement and keeping the outer one for full-width pages; the measurement
  run verified this.

## Hosting React Native panes

React Native hosting, react-native-screens behavior, RN presentations and the
library versions they were measured with are in `react-native.md`.

## Tooling on the Duo simulator

- Change posture with `sim-use` (0.16.0+; it drives devicectl like Device
  Hub's posture buttons): `sim-use ios fold closed|open|half|<0-180> --device
  <udid>` (`half` = 130°), `sim-use ios fold --device <udid>` to report the
  active display and orientation, and `sim-use ios rotate
  landscape-left|landscape-right|portrait|portrait-upside-down`. `simctl` and
  `axe` have no fold or hinge control, and the Xcode 27.1 bundle contains no
  `Simulator.app`.
- A booted Duo may come up unfolded **portrait-upside-down** (669 × 951). Rotate
  to `landscape-left` before measuring landscape numbers.
- Screenshots need the display: `xcrun simctl io <udid> screenshot
  --display=<UUID> out.png`. Look up the UUID with `simctl io <udid> enumerate`
  (inner: `Default width: 2007`, outer: `Default width: 1398`). The UUIDs
  change on every simulator boot.
- `axe describe-ui` works and gives reliable frames. `axe tap` was unreliable:
  taps on system alerts and on sheets in landscape often reported success
  without landing. Drive flows with deep links instead
  (`<scheme>://…` or the dev-client URL).

## Unverified

Open for a production dual-pane build:

1. Custom chrome under the right column: custom docks, custom headers, and
   screens using `contentInsetAdjustmentBehavior="never"` on the outer display
   (looked right in the main run; not measured screen by screen).
2. A floating chart/workspace presenter and a chat presenter under the new
   root (both need a signed-in session).

The root module as the primary placement with the window root replaced is
verified; see `react-native.md`.

Later:

- Hinge `angle` and `status` values from `UIHingeInteraction`.
- `reservedRegions(kind:options:)` frames and margins for `.division` and
  `.occlusion`.
- `UISplitArrangement` `.absolute`, `.intrinsic`, minimum/maximum and
  `layoutPriority` (only `.fractional(0.35)` was run).
- Postures other than closed, half-open book and flat; the outer display
  rotated to landscape.
- Multiple windows (`UIWindowScene.ActivationAction`), Live Activities and
  push presentation on the outer display.
- Exact outer-display status glyph positions: the values above were read from a
  screenshot, not from a frame.
- Everything on hardware. All numbers here are from the simulator.
