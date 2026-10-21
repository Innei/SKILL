# iPhone Duo — React Native specifics

Behavior that depends on the React Native stack: hosting extra surfaces,
react-native-screens bars and presentations, safe-area and layout reporting.
UIKit-level behavior is in `layout.md`; display numbers are in `device.md`.

## Versions these results are locked to

Two stacks were measured on the iPhone Duo simulator (iOS 27.1, Xcode 27.1
27A9275). Each finding below says which stack it was measured on; **58** is the
current one.

| Package | Stack 57 (2026-10-20/21) | Stack 58 (2026-10-21) |
| --- | --- | --- |
| `react-native` | 0.86.3 (New Architecture, bridgeless) | **0.88.0** (New Architecture, bridgeless) |
| `react` | 19.2.3 | 19.3.1 |
| `react-native-screens` | 4.26.2 + a patch on the gamma soft-scroll-edge paths | **4.30.0** + a patch on `RNSScreen.mm` scroll-edge re-apply and `RNSScrollViewFinder` |
| `react-native-safe-area-context` | 5.7.0 | **5.10.1** |
| `expo` | 57.0.30 | 58.0.16 |
| `expo-router` | 57.0.28 | **58.0.24** (+ a patch on link preview) |
| `expo-modules-core` | 57.0.23 | 58.0.23 |
| `expo-dev-client` / `expo-dev-launcher` | 57.0.20 / 57.0.21 | 58.0.14 / 58.0.14 |
| `expo-splash-screen` | 57.0.10 | 58.0.10 |
| App lifecycle | AppDelegate window | **UIScene** (`ExpoAppSceneDelegate` subclass) |

Neither screens patch touches `RNSScreenStack` or the header config.

**Re-verify before trusting this file** when any of these change:
`react-native-screens` (any version, including a patch bump or a changed
patch), `react-native`, `expo-router`, `react-native-safe-area-context`,
`expo-dev-launcher`, or `expo-splash-screen`. A `~` spec lets a lockfile update
move a package within its minor; rerun the test harness after any such update.

Compare the installed versions against the table:

```sh
# at the app package root
for p in react-native react-native-screens react-native-safe-area-context expo-router expo-splash-screen; do
  node -p "'$p ' + require(require.resolve('$p/package.json')).version"
done
node -p "'expo-dev-launcher ' + require(require.resolve('expo-dev-launcher/package.json', { paths: [require.resolve('expo-dev-client/package.json')] })).version"
```

## Hosting a React Native surface in a placement

Verified on 57 and 58.

- Create surfaces with
  `ExpoReactRootViewFactory.superView(withModuleName:initialProperties:launchOptions:bundleConfiguration:devMenuConfiguration:)`,
  passing `RCTBundleConfiguration.default()` and `factory.devMenuConfiguration`.
  The plain `rootViewFactory.view(withModuleName:)` goes through
  expo-dev-launcher in Debug, which restarts the launcher, clears `reactHost`,
  and boots a **second JS runtime** (`"<Module>" has not been registered`).
- Install the factory closure in `AppDelegate.application(_:didFinishLaunchingWithOptions:)`
  right after `reactNativeFactory = factory`. The SDK 58 template keeps that
  line even though `SceneDelegate` creates the window and starts React Native,
  so a config plugin that anchors on it works on both SDKs.
- expo-splash-screen attaches the launch storyboard as `loadingView` to every
  new root view and only removes it for the main root. On each extra
  `RCTSurfaceHostingProxyRootView`, call `disableActivityIndicatorAutoHide(false)`
  and set `loadingView` to an empty `UIView()` (the property is non-optional).
- In `AppDelegate.swift`, import the native module package as
  `internal import <KitModule>`. `ExpoModulesProvider` already imports it as
  `internal`, and a plain `import` fails with "ambiguous implicit access level".
- Expo module functions that touch UIKit: a sync `Function` has no
  `.runOnQueue(.main)` (compile error on SDK 58); use
  `AsyncFunction(...).runOnQueue(.main)`, or hop to main yourself.
- Each extra surface is its own React root, registered with
  `AppRegistry.registerComponent` at the bundle entry, before
  `expo-router/entry`. Never mount a second `ExpoRoot`: the expo-router store is
  a singleton.
- Every surface root needs its own `SafeAreaProvider`. Insets differ per pane;
  the main root's provider does not reach other surfaces.
- `useWindowDimensions()` inside a pane returns the whole window (951 × 669),
  not the pane. Use the pane's own layout.
- State and stacks survive unfold → fold → unfold with no remount (same pid, no
  bundle reload; mount counters stayed at 1 on 58).

## Pane stacks

**Stack 58: expo-router's vendored react-navigation cannot host a pane stack.**
`expo-router/build/react-navigation/native` no longer exports
`NavigationContainer`, and `core/BaseNavigationContainer` throws outside
`ExpoRoot`: "The navigation container requires the shared routing state provided
by `ExpoRoot`". `expo-router/build/fork/NavigationContainer` is wired to the
router's linking and routing queue, so it is not a pane container either. The
package `exports` map also resolves `expo-router/build/x/y` to `build/x/y.js`,
so directory imports need an explicit `/index`.

Two working options:

1. **Raw react-native-screens** (verified on 58): `ScreenStack` with one
   `ScreenStackItem` per route, `headerConfig` for the bar, and
   `stackPresentation` for sheets. Keep the route list in React state and remove
   a route in `onDismissed` so native back and swipe stay in sync.
2. `@react-navigation/native` + `@react-navigation/native-stack` as real
   dependencies (7.5.1 / 7.21.0 at the time; the throw message recommends it).
   **Not measured** on Duo.

Stack 57 used `NavigationContainer` from
`expo-router/build/react-navigation/native` with `createNativeStackNavigator`
from `.../native-stack`. These findings are from that stack and were **not**
re-run on 58:

- `unstable_headerRightItems` / `unstable_headerLeftItems` with `type: 'button'`
  are real `UIBarButtonItem`s and are collected into the column.
- `Stack.Toolbar` (and `NavigationHeader`) throws `useCompositionOption must be
  used within a RouterCompositionOptionsProvider` under the vendored
  native-stack; expo-router's fork
  (`expo-router/build/fork/native-stack/createNativeStackNavigator`) plus
  `LinkPreviewContextProvider` worked.
- `<Stack.Screen options>` inside a component calls `navigation.setOptions` on
  whatever screen hosts it; isolate a section with a no-op `NavigationContext`
  and a detached `CompositionContext` (`{ set() {}, unset() {} }`).
- expo-router's `useFocusEffect` worked in a pane.
- `useHeaderHeight()` reports the real bar height (82 pt when column-adjacent).

On both stacks, screen content does not avoid the right column by itself.
Give the pane's content `paddingRight` equal to the right inset; the header stays
column-adjacent so its items are still collected.

## Bars with react-native-screens

Stack 58, raw `ScreenStack` (frames in window points):

| | Half-open | Flat | Folded | Portrait (unfolded) |
| --- | --- | --- | --- | --- |
| Back in primary | keeps its title, `{20, 24, 133, 48}` | same | collected, column slot 1 `{399, 179, 38, 38}` | `{20, 24, 133, 48}` |
| Back in secondary | collected, column slot 1 `{884, 129, 38, 38}` | same | hidden | hidden |
| `headerRightBarButtonItems` (native `UIBarButtonItem`) in primary | in the bar `{392, 28, 40, 40}` | `{412, 28, 40, 40}` | column slot 2 `{399, 239, 38, 38}` | `{481, 28, 40, 40}` |
| same, in secondary | column slot 2 `{884, 189, 38, 38}` | same | hidden | hidden |
| `ScreenStackHeaderRightView` (custom view) in primary | in the bar `{394, 30, 36, 36}` | `{414, 30, 36, 36}` | **stays in the bar** `{340, 30, 36, 36}` | `{483, 30, 36, 36}` |
| same, in secondary | **stays in the bar** `{825, 30, 36, 36}` | same | hidden | hidden |
| Title next to the column | leading, `{516, 38, …}` (secondary) / `{20, 38, …}` (folded) | `{496, 38, …}` | leading | centered |

These match stack 57 (`headerRight` there rendered the same custom view) and
the UIKit results in `layout.md`. To have a trailing action follow the system
placement into the column, use a native bar item; a custom view stays in the
bar. Do not hand-place anything at the column's x.

## The root module (expo-router) as the primary placement

Verified on 57 and 58 by replacing the window root from JS after the router root
started: outer `UINavigationController` (bar hidden) → arrangement page →
`.primary` = the existing root view controller, `.secondary` = an extra surface.
On 58 the root came from the scene's key window and was a plain
`UIViewController`.

- Swap from JS. In Debug, expo-dev-launcher sets the window root after it
  connects, so a swap done in `startReactNative` is overwritten (57).
- Refuse to install while the root has a presented controller; the swap would
  orphan it.
- A JS reload keeps the native arrangement and window root (57).
- A render error that unmounts the root module leaves the secondary surface
  running (57).
- LogBox covers the whole window (951 × 669), not the pane (57).
- Deep links (`RCTLinkingManager`) reach the root module unchanged (57).
- A native presenter that walks `keyWindow.rootViewController` presents from
  the outer navigation controller: left half at half-open, a card on the outer
  display after a fold (57).
- **Native tab bar (58, expo-router native tabs on `UITabBarController`):** in
  primary at half-open it stays a bottom bar, `{0, 586, 456, 83}`, and the
  trailing search item stays in the bar `{392, 28, 40, 40}`. Wherever the tab bar
  touches the right column (folded, or the inner display without the
  arrangement) it becomes a **vertical rail in the column**; see `layout.md`.
- Stack 57 app (custom chrome): header title `{20, 12}`, header buttons end at
  x 431.7, custom tab dock `{79.8, 595, 296, 52}` centered in the pane; folded,
  header buttons end at x 378 and the dock sits at `{85, 604, …}`.

## Safe areas reported to JavaScript

Pane probes on 58 (`useSafeAreaInsets` under the surface's own provider):

| | Half-open | Flat | Folded | Portrait (unfolded) |
| --- | --- | --- | --- | --- |
| Primary | t0 l0 b34 r0, pane 456 wide | t0 b34 r0, 476 wide | t0 b34 **r84**, 466 wide | **t82** b34 r0 |
| Secondary | t0 b34 **r84**, 455 wide | t0 b34 r84, 475 wide | hidden | hidden |

- Primary at half-open, the full inner window and the outer display all report
  `top: 0`; the status sits in the right column. UIKit still places bar items at
  y 24–28. Custom chrome that positions itself from `insets.top` hugs the top
  edge unless it treats 0 as 24 (a shared `useChromeInsets()` helper).
- Do not raise the top inset app-wide: sheets report `top: 0` on every iPhone.
  Apply it only to full-screen chrome (the tab roots).
- A `SafeAreaInsetsContext` override placed under the root `SafeAreaProvider`
  does not reach tab content; nested providers inside the navigators measure
  again (57).
- Native chrome that pins to the view's edges ignores the column; pin it to
  `safeAreaLayoutGuide` leading/trailing.

## Shared state across roots (57)

- Every root needs auth: the root module's `AuthProvider` publishes its context
  value; extra roots render a shared proxy provider, which waits for the first
  published value.
- A hook that owns network state must run in one root only. The owner must not
  subscribe to the state it publishes: such a hook returns a new object every
  render, so a self-subscribed owner re-renders forever ("Maximum update depth
  exceeded").
- A JS reload restores the last opened deep link as the initial route. A debug
  deep link that triggers `DevSettings.reload()` therefore reloads in a loop.

## Presentations from a pane

Stack 58: raw `ScreenStackItem` `stackPresentation` values, and RN `<Modal>`
rendered at the pane surface root. Sheet frames come from the accessibility
tree; `measureInWindow` inside the presented content reports coordinates
**relative to the sheet**, so x and y read 0.

| Presentation | Half-open (either pane) | Flat (either pane) | Folded (primary) |
| --- | --- | --- | --- |
| `formSheet` (no detents) | `{8, 8, 460, 661}`, left half | `{149, 8, 653, 661}`, centered | `{8, 8, 450, 670}` |
| `formSheet`, `sheetAllowedDetents: [0.55, 0.95]`, grabber | `{8, 282, 460, 379}`, left half, bottom | `{149, 282, 653, 379}` | `{8, 286, 450, 384}` |
| `pageSheet` / `modal` | `{8, 8, 460, 661}`, left half | `{149, 8, 653, 661}` | `{8, 8, 450, 670}` |
| `fullScreenModal` / `transparentModal` | `{0, 0, 951, 669}` | same | `{0, 0, 466, 678}` |
| `<Modal presentationStyle="pageSheet">` / `"formSheet"` | `{8, 8, 460, 661}`, left half | `{149, 8, 653, 661}` | `{8, 8, 450, 670}` |
| `<Modal presentationStyle="fullScreen">` / `"overFullScreen"` | `{0, 0, 951, 669}` | same | `{0, 0, 466, 678}` |

- Window-scoped, matching `layout.md`: left half at half-open from either pane,
  centered across both panes when flat. RN `<Modal formSheet>` is page-sized;
  a UIKit `.formSheet` with `preferredContentSize` is a 320 × 260 card.
- Stack 57's native-stack folded cards were ≈ 10 pt shorter (`≈{8, 18, 450,
  660}`, detents `≈{8, 291, 450, 378}`); the other frames match.
- **Insets inside a presentation are unreliable.** The sheet's own
  `SafeAreaProvider` starts with the presenting pane's insets and often never
  updates. At half-open, `ScreenStackItem` sheets from secondary all kept r84
  and those from primary r0, including full-screen ones that do cover the
  column. Folded, page and form sheets settled at r76 b34, `fullScreenModal`
  at r76 b0, and `transparentModal` stayed r84 b0. `<Modal>` updates more often
  (from secondary at half-open: r84 → r0; folded: r84 → r76, `overFullScreen`
  stays r84). Lay sheet content out from the sheet's own geometry, not from the
  reported right inset.
- `onLayout` / `measureInWindow` fires first at a stale size, then at the
  sheet's size: `ScreenStackItem` content first reports the pane width × 32,
  `<Modal>` content first reports **669 × 951** (the portrait window). Use the
  last value.

## Fold, hidden secondary, and presentations

- A sheet opened from secondary survives a fold. On 58 a `formSheet` shows on
  the outer display as a full `{8, 8, 450, 670}` card over primary (57's
  native-stack: a 450 × 384 card).
- Navigating secondary to a sheet while it is hidden shows **nothing** (57 and
  58).
- An RN `<Modal>` in primary does not appear while a sheet from secondary is
  presented on the outer display (57 and 58).
- **Dismissing a secondary sheet while secondary is hidden leaves a ghost (58,
  raw `ScreenStack`).** Removing the route takes the content off screen, but an
  `RNSScreen` stays presented on the outer navigation controller (presentation
  chain `… > UINavigationController > RNSScreen`). Afterwards every RN `<Modal>`
  from either pane fails to appear, even after unfolding; a new sheet from
  secondary appears 20 pt lower, stacked on the ghost; and dismissing the
  container only dismisses the top presentation. On 57, `goBack()` on the hidden
  secondary did not dismiss the sheet at all. Either way: **dismiss sheets from
  secondary before the fold completes**, from a component still in a window.

## Tooling notes for RN on the Duo simulator

- After editing JS, surfaces that were already open did not pick up Fast
  Refresh. Relaunching the app and reconnecting the dev client did.
- Console output from every surface goes to the same Metro log, which makes it
  a reliable channel for measurements (the harness prefixes its lines). Native
  `NSLog` goes to `xcrun simctl spawn <udid> log show --predicate
  'eventMessage CONTAINS "[Tag]"'`.
- Drive the harness over Hermes CDP instead of deep links: Metro
  `/json/list` → WebSocket (send `origin: http://127.0.0.1:<port>`) →
  `Runtime.evaluate`, find the harness module in `__r.getModules()` and call its
  exports. `awaitPromise` does not resolve Hermes promises; write the result to
  a global and read it with a second evaluate. A deep-link route that renders
  `null` is itself pushed as a blank sheet and races a native fullscreen
  present, which then never shows.
- If another process holds `127.0.0.1:8081`, run Metro on another port
  (`expo start --dev-client --port 8090`) and launch the dev client with
  `xcrun simctl launch <udid> <bundle-id> --initialUrl http://localhost:8090`.

## Unverified (RN)

- `@react-navigation/native` pane stacks on 58 (bars, sheets, insets).
- `present()` from a pane routing through the root module's stack with a
  signed-in session.
- `Stack.Toolbar` bottom items and `headerLargeTitle` / search bar options in RN
  pane bars. The UIKit equivalents are in `layout.md`.
- Gesture-handler and Reanimated behavior across fold and unfold.
- On 58: JS reload with the arrangement installed, LogBox, deep links into the
  root module, and the stack-57 items marked above.
