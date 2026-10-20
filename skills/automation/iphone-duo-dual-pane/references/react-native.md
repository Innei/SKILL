# iPhone Duo — React Native specifics

Behavior that depends on the React Native stack: hosting extra surfaces,
react-native-screens bars and presentations, safe-area and layout reporting.
UIKit-level behavior is in `layout.md`; display numbers are in `device.md`.

## Versions these results are locked to

Every result in this file was measured with exactly these versions
(2026-10-20/21, iPhone Duo simulator, iOS 27.1, Xcode 27.1 27A9275):

| Package | Installed | Declared spec |
| --- | --- | --- |
| `react-native` | **0.86.3** (New Architecture, bridgeless) | `0.86.3` |
| `react` | 19.2.3 | `19.2.3` |
| `react-native-screens` | **4.26.2** + a project patch | `~4.26.0` |
| `react-native-safe-area-context` | **5.7.0** | `~5.7.0` |
| `expo` | 57.0.30 | `~57.0.30` |
| `expo-router` | **57.0.28** (vendors react-navigation under `expo-router/build/react-navigation`) | `~57.0.28` |
| `expo-modules-core` | 57.0.23 | transitive |
| `expo-dev-client` / `expo-dev-launcher` | 57.0.20 / 57.0.21 | `~57.0.20` / transitive |
| `expo-splash-screen` | 57.0.10 | `~57.0.10` |

The screens patch touches the soft-scroll-edge code paths
(`ios/gamma/scroll-view-marker/*`,
`ios/gamma/stack/screen/RNSStackScreenComponentView.mm`). The classic
native-stack (`RNSScreenStack`) used below is not patched.

**Re-verify before trusting this file** when any of these change:
`react-native-screens` (any version, including a patch bump or a changed
patch), `react-native`, `expo-router`, `react-native-safe-area-context`,
`expo-dev-launcher`, or `expo-splash-screen`. `react-native-screens` is
specified with `~`, so a lockfile update can move it within 4.26.x; rerun the
test harness after any such update.

Compare the installed versions against the table:

```sh
# at the app package root
for p in react-native react-native-screens react-native-safe-area-context expo-router expo-splash-screen; do
  node -p "'$p ' + require(require.resolve('$p/package.json')).version"
done
node -p "'expo-dev-launcher ' + require(require.resolve('expo-dev-launcher/package.json', { paths: [require.resolve('expo-dev-client/package.json')] })).version"
```

## Hosting a React Native surface in a placement

- Create surfaces with
  `ExpoReactRootViewFactory.superView(withModuleName:initialProperties:launchOptions:bundleConfiguration:devMenuConfiguration:)`,
  passing `RCTBundleConfiguration.default()` and `factory.devMenuConfiguration`.
  The plain `rootViewFactory.view(withModuleName:)` goes through
  expo-dev-launcher in Debug, which restarts the launcher, clears `reactHost`,
  and boots a **second JS runtime** (`"<Module>" has not been registered`).
- expo-splash-screen attaches the launch storyboard as `loadingView` to every
  new root view and only removes it for the main root. On each extra
  `RCTSurfaceHostingProxyRootView`, call `disableActivityIndicatorAutoHide(false)`
  and set `loadingView` to an empty `UIView()` (the property is non-optional).
- In `AppDelegate.swift`, import the native module package as
  `internal import <KitModule>`. `ExpoModulesProvider` already imports it as
  `internal`, and a plain `import` fails with "ambiguous implicit access level".
- Each extra surface is its own React root, registered with
  `AppRegistry.registerComponent`. Never mount a second `ExpoRoot`: the
  expo-router store is a singleton.
- Pane stacks: `NavigationContainer` from
  `expo-router/build/react-navigation/native` (marked deprecated) plus
  `createNativeStackNavigator` from
  `expo-router/build/react-navigation/native-stack`. Drive it imperatively with
  `createNavigationContainerRef` from `expo-router/build/react-navigation/core`.
- Every surface root needs its own `SafeAreaProvider`. Insets differ per pane;
  the main root's provider does not reach other surfaces.
- `useWindowDimensions()` inside a pane returns the whole window (951 × 669),
  not the pane. Use the pane's own layout.
- State and stacks survive fold and unfold with no remount (same pid, no
  bundle reload).

## Bars with react-native-screens

| | react-native-screens native-stack | Plain UIKit for comparison |
| --- | --- | --- |
| Back next to the right column | collected into the column, `{884, 129, 38, 38}` | same |
| Back in a pane away from the column | keeps its title: `{20, 24, 132.7, 48}` | 48 × 48 chevron |
| `headerRight` (custom view) next to the column | **stays in the bar**, ending at the column edge: `{825, 30, 36, 36}`; outer display `{340, 30, 36, 36}` | `UIBarButtonItem` is collected into the column |

To have a trailing action follow the system placement into the column, use a
native bar item (`headerRight` renders a custom view). Do not hand-place
anything at the column's x.

## Presentations from a pane

Measured with native-stack screens in the pane's stack and with RN `<Modal>`
rendered at the pane surface root. Positions come from the accessibility tree;
sizes come from `measureInWindow` in the presented content. `measureInWindow`
reports coordinates **relative to the presented sheet**, so x and y read 0.

| Presentation | Half-open (either pane) | Folded |
| --- | --- | --- |
| native-stack `formSheet` (default detents) | `{8, 8, 460, 661}`, left half | `≈{8, 18, 450, 660}` |
| native-stack `formSheet`, `sheetAllowedDetents: [0.55, 0.95]`, grabber | `≈{8, 282, 460, 379}`, left half, bottom | `≈{8, 291, 450, 378}` |
| native-stack `pageSheet` / `modal` | `{8, 8, 460, 661}`, left half | `≈{8, 18, 450, 660}` |
| native-stack `fullScreenModal` / `transparentModal` | `{0, 0, 951, 669}` | `{0, 0, 466, 678}` |
| `<Modal presentationStyle="pageSheet">` / `"formSheet"` | `{8, 8, 460, 661}`, left half | `{8, 8, 450, 670}` |
| `<Modal presentationStyle="fullScreen">` / `"overFullScreen"` | `{0, 0, 951, 669}` | `{0, 0, 466, 678}` |

- This matches the UIKit results in `layout.md`: window-scoped, left half at
  half-open, from either pane. One difference: RN `<Modal formSheet>` is
  page-sized (460 × 661), whereas a UIKit `.formSheet` with
  `preferredContentSize` is a 320 × 260 centered card.
- Insets reported by a `SafeAreaProvider` inside the sheet, final values:
  sheets at half-open r0; folded cards r76 (native-stack) or r84
  (`<Modal>`); full screen r0 at half-open and r84 folded. Treat these as
  per-presentation and read them inside the sheet.
- `onLayout` fires first at the pane's size (for example 455 × 669 with r84),
  then again at the sheet's size. Use the last value.

## Fold, hidden secondary, and presentations

- A native-stack `formSheet` opened from secondary survives a fold. It shows on
  the outer display as a 450 × 384 card over primary.
- While secondary is hidden, `goBack()` on secondary's navigator does **not**
  dismiss that sheet. Dismiss it before folding, or from a component that is
  still mounted in a window.
- Navigating secondary to a sheet screen while it is hidden logs a pane-size
  layout, but **nothing appears**.
- An RN `<Modal>` in primary does not appear while another sheet (from
  secondary) is still presented on the outer display.

## Tooling notes for RN on the Duo simulator

- After editing JS, surfaces that were already open did not pick up Fast
  Refresh. Relaunching the app and reconnecting the dev client did.
- Console output from every surface goes to the same Metro log, which makes it
  a reliable channel for measurements (the test harness prefixes its lines).
- If another process holds `127.0.0.1:8081`, the dev client gets
  "Cannot GET …/entry.bundle". Run Metro on another port (`pnpm start --port
  8090`) and open the dev-client deep link with that URL
  (`<scheme>://expo-development-client/?url=http%3A%2F%2F127.0.0.1%3A8090`).

## Unverified (RN)

- expo-router `Stack` screens (as opposed to a bare native-stack) inside a
  pane surface. The app-specific presentation store path is not exercised.
- `Stack.Toolbar` bottom items and `headerLargeTitle` / `headerSearchBarOptions`
  in RN pane bars. The UIKit equivalents are in `layout.md`.
- Gesture-handler and Reanimated behavior across fold and unfold.
- Running the app's root module (expo-router root) as the primary placement.
