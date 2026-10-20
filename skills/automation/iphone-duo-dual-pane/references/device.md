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

Right column contents (all in window points):

| | Inner | Outer |
| --- | --- | --- |
| Column | x 867–951, full height | x 382–466, full height |
| Time | y ≈ 30–50 | y ≈ 86–100 (below the navigation bar row) |
| Connectivity glyph | y ≈ 56–96 | y ≈ 108–150 |
| Collected back button | frame `{{884, 125–129}, {38, 38}}` | frame `{{399, 179}, {38, 38}}` |

## Navigation bars

Rules observed from UIKit, with react-native-screens native-stack bars inside
each pane:

1. **The back action is collected into the right safe area.** When a bar's
   leading back item would sit next to the status column (the secondary pane,
   any outer-stack page, primary on the outer display), UIKit removes it from
   the bar and shows it as a 38 × 38 circular button inside the column, below
   the status glyphs.
2. **Trailing items stay in the bar** and end at the column's left edge.
   Measured: secondary pane `★` at `{{825, 30}, {36, 36}}` (ends at 861); outer
   display `★` at `{{340, 30}, {36, 36}}` (ends at 376).
3. **The title moves to the leading edge** when the back item has been
   collected. With the back item still in the bar (primary pane, flat), the
   back button keeps its title (`{{20, 24}, {132.7, 48}}`) and the title is
   centered in the pane.
4. **Half-open (book posture)**, the primary pane's back item also collapses
   to a 38 × 38 button, at the pane's trailing edge next to the hinge
   (`{{388.7, 29}, {38, 38}}`).
5. Bars respect the inset; **content does not unless asked**. RN content in the
   test ran under the right column until it read `useSafeAreaInsets()`. Every
   surface root needs its own `SafeAreaProvider` and must apply the right
   inset.

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
  on unfold.
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
  `axes(_:)` and `setViewProperties(_:for:)`. Overlay was **not exercised**.
- `UIViewController.arrangementViewController` finds the enclosing container.
- Apple places a navigation container *outside* the arrangement. Two
  independent push stacks work by putting a navigation controller inside each
  placement and keeping the outer one for full-width pages; the measurement
  run verified this.

## Hosting React Native panes

What it took so that each placement can host its own RN surface on the app's
single React host (Expo SDK 57, RN 0.86 New Architecture):

- Create surfaces with
  `ExpoReactRootViewFactory.superView(withModuleName:initialProperties:launchOptions:bundleConfiguration:devMenuConfiguration:)`,
  passing `RCTBundleConfiguration.default()` and `factory.devMenuConfiguration`.
  The plain `rootViewFactory.view(withModuleName:)` goes through
  expo-dev-launcher in Debug, which restarts the launcher, clears `reactHost`
  and boots a **second JS runtime** (`"<Module>" has not been registered`).
- expo-splash-screen attaches the launch storyboard as `loadingView` to every
  new root view and only removes it for the main root. On each extra
  `RCTSurfaceHostingProxyRootView`, call `disableActivityIndicatorAutoHide(false)`
  and replace `loadingView` (it is non-optional) with an empty `UIView()`.
- In `AppDelegate.swift`, import the native module package as
  `internal import <KitModule>`. `ExpoModulesProvider` already imports it as
  `internal`, and a plain `import` fails with "ambiguous implicit access level".
- `useWindowDimensions()` inside a pane returns the whole window (951 × 669),
  not the pane. Read pane size from layout.
- Each extra surface is its own React root: register it with
  `AppRegistry.registerComponent`, and do not use a second `ExpoRoot`. Pane
  stacks can use `NavigationContainer` from
  `expo-router/build/react-navigation/native` with `createNativeStackNavigator`
  (the export is marked deprecated).

## Tooling on the Duo simulator

- No CLI changes posture. `simctl` and `axe` have no fold or hinge control, and
  the Xcode 27.1 bundle at `/Applications/Xcode-27.1.0.app` contains no
  `Simulator.app`. A person has to fold and unfold.
- Screenshots need the display: `xcrun simctl io <udid> screenshot
  --display=<UUID> out.png`. Look up the UUID with `simctl io <udid> enumerate`
  (inner: `Default width: 2007`, outer: `Default width: 1398`). The UUIDs
  change on every simulator boot.
- `axe describe-ui` works and gives reliable frames. `axe tap` was unreliable:
  taps on system alerts and on sheets in landscape often reported success
  without landing. Drive flows with deep links instead
  (`<scheme>://…` or the dev-client URL).
- After editing JS, surfaces that were already open did not pick up Fast
  Refresh. Relaunching the app and reconnecting the dev client did.

## Unverified

Open for a production dual-pane build:

1. The app's real root module (expo-router, NativeTabs, custom docks, splash)
   running as the primary placement with the window root replaced. Only test
   panes in a modal were hosted.
2. Native presenters that walk `keyWindow.rootViewController` under the new
   root.
3. Sheets and modals presented from a pane: their width, and what the system
   does with them on fold and unfold.
4. Custom chrome under the right column: custom docks, custom headers, and
   screens using `contentInsetAdjustmentBehavior="never"` on the outer
   display.
5. Keyboard placement and size on both displays, for example a chat composer
   or a form.

Later:

- Hinge `angle` and `status` values from `UIHingeInteraction`.
- `reservedRegions(kind:options:)` frames and margins for `.division` and
  `.occlusion`.
- `UIOverlayArrangement`, and `UISplitArrangement` view properties (fixed or
  fractional pane widths).
- The inner display held portrait (rotated 90° while unfolded), and postures
  other than half-open book and flat.
- Multiple windows (`UIWindowScene.ActivationAction`), Live Activities and
  push presentation on the outer display.
- Exact outer-display status glyph positions: the values above were read from a
  screenshot, not from a frame.
- Everything on hardware. All numbers here are from the simulator.
