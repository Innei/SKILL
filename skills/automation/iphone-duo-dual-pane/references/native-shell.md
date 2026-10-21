# iPhone Duo — native navigation shell and posture switching

Pitfalls hit while replacing react-native-screens / expo-router stacks with
app-owned UIKit containers (`UITabBarController`, `UINavigationController`,
`UIArrangementViewController`) whose children are React views, and while
switching layout on fold, unfold and hinge changes. Measured on stack **58**
(see `react-native.md`) with Fabric, on the iPhone Duo simulator.

## Shell architecture that held up

- One React tree. Each container is an Expo `ExpoView` that overrides
  `mountChildComponentView` / `unmountChildComponentView` and moves the child
  React views into view controllers it owns. expo-router still drives state
  through `createStandardRouterNavigator(Content, StackRouter | TabRouter)`;
  the content component maps routes to native screens. Nothing remounts on
  push, pop, tab switch, fold or unfold.
- Branch on the device, not on size: the Duo's model identifier is
  `iPhone19,4` (read `SIMULATOR_MODEL_IDENTIFIER` on the simulator, `uname`
  `machine` on hardware) and expose it to JS as a module constant. "App-owned
  on Duo" below means the app's own containers replace the react-native-screens
  stack only when that constant is true.
- Register every view with an explicit `ViewName`; a module with several
  views otherwise collides.
- New Swift / ObjC files in a local Expo module need `pod install` before the
  build sees them.

## Interaction pitfalls

| Symptom | Cause | Fix |
| --- | --- | --- |
| Tab bar lays out horizontally while a root stack pops | The window's vertical bar follows the **top** view controller chain; a react-native-screens root stack owns it during the pop | Make the root `UINavigationController` app-owned on Duo, override `childForPreferredVerticalBarBehavior` (return the last child) on hosting controllers, and call `setNeedsUpdateOfVerticalBarConfiguration()` after embedding |
| `Stack.Toolbar` throws "must be used within…" | It needs the native-stack composition context | Branch: under the app stack, publish `UIBarButtonItem`s from the screen controller instead; only render `Stack.Toolbar` under a react-native-screens stack |
| Taps inside a presented sheet never reach JS | The sheet's view is outside the React root view, so no touch handler sees it | Attach an `RCTSurfaceTouchHandler` (ObjC++ wrapper) to the presented navigation controller's view; detach on dismiss |
| Sheet content lays out at the full window width and overflows | Yoga still holds the frame from the React parent; the sheet is narrower | Push the container's size back with `setStyleSize(width, height)` from the hosted view's `layoutSubviews` (compare against the superview's bounds) |
| Edge / content swipe-back never begins | `interactivePopGestureRecognizer` and iOS 26's `interactiveContentPopGestureRecognizer` are created lazily; a delegate set before they exist is lost, and UIKit's default delegate refuses on Duo | After `loadViewIfNeeded()`, set your own delegate on both. Allow when `viewControllers.count > 1`, no transition is running, and a content pan moves rightward-dominant (translation can be zero at `shouldBegin` for synthetic swipes) and no horizontal scroll view under the touch can scroll left |
| A `UIColor` prop arrives as a string | Expo converts hex strings for `UIColor` props | Type the prop as `UIColor`, not `String` |
| Unselected rail icons ignore `unselectedItemTintColor` | The vertical rail ignores appearance tint for unselected items | Pre-tint the unselected image with `withTintColor(_:renderingMode: .alwaysOriginal)` |
| Duo menu shows empty items | Items marked hidden for the phone menu were still mapped into the `UIMenu` | Filter hidden items before building the native menu |

## Moving React views: never with a transform alone

A native `transform` (or reparenting into a translated container) moves the
pixels but not Yoga's layout. `Pressable` measures its hit region from the
shadow tree, so a tap that moves even slightly is judged to have left the
button and `onPress` never fires. Simulator taps with zero movement still
work, which hides the bug.

- Reproduce with a 2–3 pt drag tap (`sim-use ios swipe --from x,y --to
  x+3,y+3 --duration 0.2`); a plain tap passes either way.
- Put positions and widths into Yoga: native reports the target frame through
  an event, JS sets `left` / `width` in **one** commit. Expo views can only
  write size (`setStyleSize`), not position.
- Animate by FLIP on the native side: when the view's resting frame changes
  (observe `center` and resolve in `layoutSubviews`), set the transform to the
  old-minus-new offset and spring it to identity. Arm the glide only for a
  short window after a posture change, so later relayouts never animate.
- A view that changes shape between modes (a sidebar becoming a left page)
  should cross-fade, delayed until the sliding content settles, or it overlaps
  the content mid-slide.
- Give full-height overlay slots `pointerEvents="box-none"` and size inner
  scroll views to their content (`flexGrow: 0, flexShrink: 1`), or the empty
  area swallows drags meant for the content underneath.

## Posture switching without jumps

Lay out by posture (book = anything short of `fullyOpen` on the inner
display, flat, single), switch discretely, and keep the reading column stable.

1. **No synchronous hinge state.** `UIHingeInteraction` only calls back; the
   first layout on the inner display lands ≈ 90 ms before the first callback.
   Keep the last status in shared (static) state so new views start from it,
   and treat `closed` / `unknown` / `partiallyOpen` as book: unfolding always
   passes through a partial opening. "Book" only takes effect where a division
   exists (the inner display held landscape); on the outer display the same
   status still lays out the single column.
2. **Transitional layouts.** Unfolding: the outer display first drops its
   84 pt column (insets become top 82, right 0) while the view keeps 466 pt;
   then the window becomes 951 while the view is still 466. Folding: the
   window becomes 466 while the view is still 951 and no division exists, so
   the layout computes as flat. Hold the last settled layout while (a) the
   hinge has just left `closed` and the view has not resized, or (b) the
   window size changed but the view's has not. Record sizes only while the
   view is in a window; a nil window recorded at first layout holds every
   later report forever.
3. **Same width on both sides of the fold.** The book's right page is
   371.5 pt (951 − 84 − 495.5); the outer display's safe width is 382 pt. Fold the column
   to the book page width (learned from the inner display) so the right page
   and the folded screen wrap text identically and the scroll offset maps to
   the same lines.
4. **Content that sizes from the window.** Blocks that compute height from
   `useWindowDimensions()` (image grids, diagram snapshots) lay out for 951 pt
   on the inner display and 466 pt outside, so the same scroll offset shows
   different text after a fold even at an identical column width. Feed the
   column width through context and size from it.
5. **Measure before fixing.** Log each reported layout (mode, widths) and the
   view's bounds, insets, window bounds and hinge status natively
   (`xcrun simctl spawn <udid> log stream --predicate 'eventMessage CONTAINS
   "TAG"'`); scroll metrics in JS only update on scroll, so nudge or read them
   natively.

## Tooling

- Run each app on its own simulator and Metro port; two Expo apps on one
  simulator and port load each other's bundles ("Cannot find native module").
- A fresh simulator shows the dev-menu onboarding over the app: `xcrun simctl
  spawn <udid> defaults write <bundle-id> EXDevMenuIsOnboardingFinished -bool
  YES`.
- `sim-use ios tap -x -y` lands reliably; `--label` taps often miss on Duo.
- `sim-use` cannot synthesize a screen-edge pan; verify edge swipe-back by
  hand in Device Hub.
- `sim-use ios fold closed` from half-open passes through `fullyOpen` on the
  simulator; a real fold from half-open does not. Do not tune for that frame.
