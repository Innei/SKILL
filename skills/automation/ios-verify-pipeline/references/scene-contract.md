# The scene contract

The pipeline's determinism comes from the app, not from the driver. A scene is a
**Debug-only host that renders production views with injected state** — the same
views users see, with none of the dependencies that make real state unstable.

Everything downstream (a case that can fail on purpose, an error state on
demand, a re-runnable suite) follows from this file being honored.

## The four requirements

### 1. Scene entry

One launch argument or deep link opens a scene directly:

```swift
// LodyKit/verify/DebugSceneHost.swift — Debug only, compiled out of Release.
enum DebugScene: String {
    case list, chatEmpty, chatStreaming, composerGlass, sendFailure
}

func debugSceneArgument(_ arguments: [String]) -> DebugScene? {
    arguments.first { $0.hasPrefix("--scene=") }
        .map { String($0.dropFirst("--scene=".count)) }
        .flatMap(DebugScene.init(rawValue:))
}
```

```sh
xcrun simctl launch "$UDID" "$BUNDLE_ID" --scene=composerGlass
```

In React Native / Expo the same thing is a debug-only route plus a launch
argument that selects it; keep the selection in *native* launch arguments so the
runner never depends on JS timing to choose a scene.

Rules:

- The scene argument is **developer-only**: guarded by a build flag or a
  `#if DEBUG`-equivalent, and inert in a release binary.
- Scene ids are stable strings — they are referenced by cases and by CI logs.
- Selecting a scene must never require the network, an account, or a tap path.

### 2. Ready marker

The scene sets an accessibility identifier when content is laid out and stable:

```swift
view.accessibilityIdentifier = "ui-verify-ready"
```

The runner waits for it (with a generous first-load deadline, since a JS bundle
or a first render can take tens of seconds) and only then starts the case. The
marker means "the scene is measurable", not "everything has loaded" — a case
that needs a later state waits for its own identifier.

Never key the case start on a sleep, and never on a screenshot looking right.

### 3. Injection boundary

Data and services are injected where the feature already accepts them:

```swift
final class VerifyCatalogProvider: CatalogProvider { /* deterministic fixtures */ }

switch launchMode {
case .verify:   Environment.catalog = VerifyCatalogProvider()
case .production: Environment.catalog = CloudCatalogProvider()
}
```

Passing a launch argument that *overrides a service at its owning boundary* is
the whole mechanism. Two consequences worth stating explicitly, because both are
commonly violated:

- **Do not build a second, parallel UI for verification.** Reuse the production
  view; if the production view cannot express a state, the view needs a
  parameter — not a copy.
- **Do not mock past the seam you are testing.** Inject the *inputs* (data,
  clocks, transport), and let the production logic run.

### 4. In-process reset

Cases run back to back in one app process. Returning to the scene list must not
relaunch the app:

```swift
NotificationCenter.default.post(name: .debugSceneReset, object: nil)
```

```js
// RN: exposed by the Debug host only, invoked through the simulator inspector.
globalThis.__verifyReset = () => navigationRef.resetRoot({ routes: [{ name: 'debug' }] });
```

The runner asserts the pid is unchanged across the reset. A reset that
accidentally relaunches the app turns every case into a cold start and hides
lifecycle bugs — that is a failure of the suite, not a nicety.

If adopting a new scene requires changing the app's startup path, prefer a
relaunch for that case and record it in `results.json` (`appLifecycle:
"launch"`); do not bend the reset contract.

## Fixture content

- Text fixtures are fixed strings, deliberately mixed in length and script.
- Fixture rows have stable identifiers so a case can address them
  (`history-session:two`) without depending on order or on translated copy.
- Fixtures live behind the same boundary as their production counterpart; a
  fixture that bypasses persistence proves nothing about persistence.
- Fixture content is not localized. Product copy is: assert it through the
  app's own catalog so a case proves the language it was launched in.

## Checklist: adding a scene

1. Scene enumerable and reachable by launch argument (Debug only).
2. Production views only; no copy of a screen.
3. Services/data injected at the owning boundary; no network, no credentials.
4. `ui-verify-ready` set after first stable layout.
5. Reset returns to the scene list with the same pid.
6. At least one control has a stable accessibility identifier that a case will
   assert on — not a translated label.
7. The scene is registered in the case's `scene` field in the adapter config.

## What the contract buys you

| Without it | With it |
| --- | --- |
| Cases click through the product to reach a screen | A case opens the screen in one launch argument |
| Error states need a real failure | Any error state is injected on demand |
| Redesigns break every case | Redesigns break only the cases that assert on it |
| "It looked right in the video" | A declared assertion plus the video |
