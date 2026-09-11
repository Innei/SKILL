---
name: ios-verify-pipeline
description: >
  Use when an iOS app repository needs a repeatable visual/functional
  verification suite rather than one-off simulator poking: deterministic Debug
  scenes, AXe-driven cases, and per-case evidence (video, screenshots, AX tree,
  probe JSON) produced by one run that feeds both a CI gate and a reviewable
  round. Triggers on "add a UI verification case", "verify this screen on the
  simulator", "why did this screen regress", "set up iOS visual verification",
  "the UI regression suite", "AXe pipeline", "screenshot every case". Not App
  Store marketing screenshots (asc-shots-pipeline), not one-off delivery proof
  (acceptance).
metadata:
  author: innei
  version: "0.1.0"
---

# ios-verify-pipeline

A UI suite that people still trust after a year rests on one decision: **the
app declares deterministic scenes, and the pipeline drives those scenes.**
Everything else — device leasing, the driver, the video, the report — is
plumbing around that decision.

The failure mode this skill exists to prevent: scripts that click through the
real product until they happen to reach a screen, then screenshot it. Those
break on every redesign, cannot reproduce an error state on demand, and assert
nothing a reviewer would accept.

## Scope

Build and maintain this suite **inside one iOS app repository**.

This skill owns the *contract*: what a case, a run, and a round are; what
evidence a case must produce; which failures belong to the harness rather than
the product. The harness belongs to the project — vendored from a reference
implementation or written against `references/harness.md`.

**Non-goals.** App Store screenshots and framing (`asc-shots-pipeline`,
`app-store-listing`); one-off delivery proof and reviewer accept/reject
(`acceptance` — this suite feeds it, it does not replace it); unit or data-layer
tests; Android; any cross-platform abstraction layer; physical-device
performance, thermal, or haptics claims.

## Three layers, and why they stay separate

```text
scene contract (app)      vs  harness (repo)          vs  judgment (human/LLM)
------------------------      ----------------------     ---------------------
Debug-only scene host         device lease               per-delivery review
production views              build / install / launch   accept / reject
injected services             AXe driver + capture       immutable round
<scene>-ready marker          results.json               required evidence
in-process reset entry        exit codes                 blocked vs fail
```

A run produces `results.json` for the CI gate and, unchanged, the raw material
for a reviewable round. **Never re-capture for the round** and never let the
suite's aggregate ("all cases green") become a review item — that is a gate,
not a claim a person judges. See `references/evidence-and-rounds.md`.

## Prerequisite: the scene contract

Do not start writing cases until the app exposes all four:

1. **Scene entry** — a launch argument or deep link that opens a specific
   scene directly (`--scene composer-glass`, `app://verify/composer-glass`).
2. **Ready marker** — an accessibility identifier the scene sets when its
   content is laid out and stable (`ui-verify-ready`).
3. **Injection boundary** — the scene is built from production views, with
   data and services injected at the owning boundary. No account, no network,
   no cloud, no connected machine.
4. **In-process reset** — return to the scene list without restarting the
   process, so the bundle and app lifecycle survive across cases.

Missing any of them: the affected cases are reported `blocked`, not faked with
a coordinate hunt. Full pattern, Swift/UIKit and React Native variants, and the
"never build a second UI" rule: `references/scene-contract.md`.

## Workflow

```text
[1] Read the adapter
      -> ios-verify.config.json: app, pool, server, launch, matrix, cases
      -> never invent a build command, port, or launch argument

[2] Add or update one case
      -> one user-visible behavior, one scene, one observable assertion
      -> declare requiredEvidence for that behavior
      -> run it alone first; a case that cannot fail proves nothing

[3] Run the batch
      -> isolated server the runner owns; leased device; both appearances
      -> video + screenshots + AX tree per case, results.json at the end

[4] Judge
      -> pass / fail / blocked; a harness timeout is blocked, not fail
      -> reproduce the failure precondition before fixing the product

[5] Export a round only for a visual/interaction requirement alignment
      -> claims file -> round directory -> publish; regression runs never publish
```

## Evidence

Every case emits, for every appearance:

| Type            | Source                                        | Why                          |
| --------------- | --------------------------------------------- | ---------------------------- |
| `video`         | `simctl io recordVideo` for the whole case    | transitions, gestures, keyboard |
| `screenshot`    | before / after / failure frames               | settled visual state         |
| `dom_snapshot`  | `axe describe-ui` next to each screenshot     | assertions a reviewer audits |
| `text`          | the case log and any probe JSON               | geometry, timing, fps        |

A declared evidence type that the case did not produce **invalidates the case**
— it is not a pass with a missing attachment. Capture happens while the case
runs; screenshots are evidence, never a substitute for an assertion.

## Harness

The harness is a plain CLI in the project (Python 3 stdlib is enough; no
third-party dependencies — that is what makes it installable and long-lived).
Required surface, artifact layout, exit codes, and the reference
implementation's file map: `references/harness.md`.

Platform mechanics — AXe primitives, launch arguments for language and
appearance, keyboard and IME traps, the video recorder handshake:
`references/driver-axe.md`.

## Rules

- **Idempotent by construction.** A scene shows the same thing on every run;
  any randomness or clock dependence is a bug in the scene, not a flake.
- **Element-relative geometry only.** Assert against a sibling's frame or the
  window, never hardcoded device coordinates.
- **The pipeline owns its own server and device.** Refuse to attach to a Metro
  or a Simulator another task owns; refuse an occupied port instead of reusing
  it.
- **Preserve the app's build path.** Build with the project's canonical command
  and an explicit destination; never let a tool select a personal device.
- **One case, one behavior.** If a case needs a paragraph to describe what it
  checks, split it. A case a reviewer cannot accept or reject on its own is
  already too big.
- **Assertions live in the case.** The config declares *what evidence* and
  *what readiness*; it never grows a DSL for assertions.
- **Copy is read from the app's own catalog.** Assert localized strings through
  the shipped resource files, so a case proves the language it ran in.

## Verification

Before reporting a case as working:

1. Run it alone, in both appearances, from a clean scene — not after another
   case's leftovers.
2. Confirm the case can fail: break the behavior under test, watch it fail,
   restore it.
3. Open the produced screenshots and the video; a passing exit code with an
   unreadable frame is not evidence.
4. Confirm `results.json` marks exactly the intended case as the change, and
   that the CI gate reads it (not a hand-copied summary).

## References

| File | Read when |
| ---- | --------- |
| `references/scene-contract.md` | Building the Debug scene host or adding a scene |
| `references/project-adapter.md` | Bootstrapping the suite in a new app; the config schema |
| `references/harness.md` | Writing or vendoring the engine; the required CLI surface |
| `references/driver-axe.md` | Any simulator/AXe behavior question, or a weird driver failure |
| `references/evidence-and-rounds.md` | Deciding evidence types, round export, gate vs review |
| `references/probe-mock-patterns.md` | Forcing an error state, offline mode, or a slow path |
| `references/common-mistakes.md` | Before marking any case `pass` |
| `assets/ios-verify.config.example.json` | Copying the adapter shape |
| `assets/claims.example.json` | Exporting a visual alignment round |
