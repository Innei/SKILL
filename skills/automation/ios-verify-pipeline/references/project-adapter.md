# Project adapter

One JSON file describes how this app is built, run, and verified. The runner
never guesses a port, a scheme, or a launch argument; everything here is
explicit.

Default location: `.agents/ios-verify/ios-verify.config.json`
(alternative: `ios-verify.config.json` at the repo root). Copy
`assets/ios-verify.config.example.json`.

## Schema

```jsonc
{
  "version": 1,

  "app": {
    "workspace": "ios/App.xcworkspace",     // or "project": "ios/App.xcodeproj"
    "scheme": "App",
    "configuration": "Debug",
    "bundleId": "app.example.app",
    "derivedData": "/tmp/app-build",        // never inside the repo or .artifacts
    "buildCommand": ["xcodebuild", "-workspace", "ios/App.xcworkspace", "-scheme", "App",
                     "-configuration", "Debug", "-sdk", "iphonesimulator",
                     "-destination", "id={udid}", "-derivedDataPath", "/tmp/app-build", "build"],
    "productPath": "Build/Products/Debug-iphonesimulator/App.app"
  },

  "pool": {
    "namePattern": "App * Verify",          // reserve this pattern for disposable devices
    "deviceType": "iPhone-17-Pro",
    "runtime": "iOS-26-5",
    "reuse": true                           // shut down after a run, keep for the next one
  },

  "server": {                                // omit when the app has no dev server
    "command": ["pnpm", "start"],
    "port": 8097,
    "env": { "EXPO_PUBLIC_UI_VERIFY": "1" },
    "readyLog": "Metro waiting on",          // a log line, not merely "process started"
    "readyPort": 8097
  },

  "launch": {
    "args": ["--ui-verify"],                 // always-on verification launch arguments
    "sceneArg": "--scene={scene}",           // how a scene id is passed
    "url": "http://127.0.0.1:{port}",        // deep link, when the app is launched by URL
    "reset": "globalThis.__verifyReset()",   // evaluated in-process; must keep the pid
    "firstReadyTimeout": 180
  },

  "matrix": {
    "appearances": ["light", "dark"],
    "languages": ["en"],                     // run each separately; never claim both from one
    "contentSize": "large",
    "systemLanguage": "en_US"               // host/system controls stay in one language
  },

  "evidence": {
    "video": true,
    "screenshots": ["before", "after", "failure"],
    "axTree": true,
    "output": ".artifacts/verify"           // ignored by git
  },

  "cases": [
    {
      "id": "composer-glass",
      "batch": "send",
      "scene": "composerGlass",
      "ready": "create-session-input",
      "script": "cases/composer_glass.py",   // omit for declarative steps
      "steps": null,
      "requiredEvidence": ["screenshot", "video", "dom_snapshot"],
      "timeout": 180,
      "appLifecycle": "reset"                // or "launch" when the scene needs a relaunch
    }
  ]
}
```

### Field rules

- `{udid}` / `{port}` / `{scene}` / `{language}` / `{appearance}` are the only
  substitutions. There is no expression language.
- `requiredEvidence` uses the closed vocabulary in
  `evidence-and-rounds.md`. A type the case does not produce invalidates the
  case.
- `batches` group cases that can run on one device in one pass; a batch is the
  unit of CI parallelism, not a test hierarchy. Every id in `batches` and in
  every `cases[].batch` must exist in `cases` — a batch naming a missing case is
  how a suite silently stops covering something.
- **Assertions are never in this file.** Declarative `steps` express
  navigation and capture only; anything that has to *judge* a value is a script.

## Bootstrapping a new app

```text
[1] Land the scene contract                        -> references/scene-contract.md
      one scene, one ready marker, one reset entry

[2] Fill app / pool / server / launch              -> prove it by hand first:
      simctl boot, install, launch --scene=..., describe-ui contains the ready id

[3] Write one case with a deliberate failure
      break the behavior, watch the case fail, restore it

[4] Add the second appearance and the second language
      one run each; the config language must match the assertion catalog

[5] Wire the gate: results.json -> CI, per-batch artifact upload
      a failed batch never cancels its siblings

[6] Add the living logs to this repo
      common-mistakes.md and probe-mock-patterns.md, project layer only

[7] Only then scale the case count
```

Steps 1–3 are the ones worth being slow about. A suite built before the scene
contract exists is a click-bot that will be deleted within a quarter.

## Generic vs app-private

Getting this split wrong is how a "reusable" pipeline becomes unmaintainable.

| Belongs to the harness (generic) | Belongs to the app (private) |
| --- | --- |
| Device lease, boot, shutdown, rename | Bundle id, scheme, workspace, product path |
| Server ownership, port collision refusal | Server command, env flag, ready log line |
| Launch/terminate, appearance and content-size switching | Launch arguments and scene ids |
| AXe driver primitives, typed waits | Accessibility identifiers and their meaning |
| Video / screenshot / AX-tree capture, evidence typing | Which evidence a behavior needs |
| `results.json`, exit codes, blocked-vs-fail | Assertions, fixtures, injected services |
| Round export and coverage gate | Which behaviors a delivery claims |

If you find yourself adding an app-specific branch to the harness, the missing
piece is a config field — or the case belongs in the app's `cases/` directory.

## Reference implementation

The first implementation of this pipeline lives in `lody-ios`; use it as the
porting source, and keep the direction of the dependency one-way (the app
depends on the harness, never the reverse):

| Concern | Reference file |
| --- | --- |
| Device lease pool, rename, lock, shutdown | `apps/mobile/verification/simulator.py` |
| Server ownership, batch orchestration, Metro diagnostics | `apps/mobile/verification/ui/orchestrator.py` |
| AXe driver, typed waits, pasteboard fixtures | `apps/mobile/verification/ui/driver.py` |
| Case tables, per-case evidence, results.json | `apps/mobile/verification/ui/run.py` |
| Round export + coverage gate | `apps/mobile/verification/ui/acceptance-round.py` |
| Case scripts and Debug scenes | `apps/mobile/verification/ui/*.py`, `modules/lody-kit/verification/` |
| CI batches and artifacts | `.github/workflows/verify.yml` |

Those files also carry the project's case inventory and Debug scenes; the
portable parts are the left column, and the inventory stays behind.
