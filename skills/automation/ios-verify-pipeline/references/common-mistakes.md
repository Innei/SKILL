# Common mistakes

The project layer of this log is the one that grows. Fix a mechanism in a script
default or a config field, delete its entry in the same change — an entry that
survives its mechanism teaches the next agent to skip the log.

## Checklist — read before marking any case `pass`

1. Have I opened the screenshots and the video myself, at full resolution?
2. Can this case fail? Have I seen it fail with the behavior broken?
3. Is the assertion about the product's behavior, or about the harness agreeing
   with itself?
4. Is the asserted state the one the claim needs, at the moment the claim is
   about — not one frame later?
5. Are the expected strings read from the app's own resource catalog?
6. Is every declared evidence type actually present in this case's directory?
7. If a video or a probe JSON is cited, did I look at it rather than its file
   size?
8. Would a reviewer accept or reject this specific item on this evidence alone?

## C1 — A green exit code with unreadable frames

**Trap:** the case passed, the artifacts exist, so the evidence is assumed good.
A black frame, a modal covering the screen, or a screenshot taken before layout
all pass a file-existence check.

**Rule:** open every artifact you cite. File existence and a caption are not
visual verification.

`since:` first suite review · `holds-while:` artifacts are cited by humans

## C2 — A case that cannot fail

**Trap:** written against the working build, asserting something already true
(for example, that a list is non-empty after loading a fixture that always
loads). It has never been observed failing.

**Rule:** before keeping a case, break the behavior under test, watch the case
fail, restore it. A run that cannot fail proves nothing.

`since:` first regression week · `holds-while:` assertions are authored after the
implementation

## C3 — HID dispatch is not a processed event

**Trap:** `axe tap` exits 0, so the case continues as if the tap landed. It did
not: most AXe commands are fire-and-forget.

**Rule:** every interaction has a postcondition the case asserts — an identifier
appears, a value changes, a row count moves. Never treat a dispatched gesture as
an observed one.

`since:` first gesture-driven case · `holds-while:` the driver is AXe/simctl

## C4 — Offscreen rows are not in the accessibility tree

**Trap:** the assertion waits for a row that exists in the data and is rendered
in a collection view but has never been scrolled into the tree — the wait times
out and gets blamed on the product.

**Rule:** scroll the container until the target is addressable, then assert. For
large datasets, also assert the data count through a non-visual surface.

`since:` long-history case · `holds-while:` list content is virtualized

## C5 — The "reset" that reloaded the app

**Trap:** an in-process reset accidentally restarts the app (a full JS reload, a
root replacement that drops the native host). Every later case then measures a
cold start, and lifecycle bugs disappear from the suite.

**Rule:** assert the pid is unchanged across a reset, and record the lifecycle
per case in `results.json`.

`since:` batch runner · `holds-while:` cases share one app process

## C6 — The suite attached to someone else's server

**Trap:** the dev server was already running on the configured port, so the run
silently used another task's bundle — or worse, its environment.

**Rule:** the runner owns its server; an occupied port is an error, not an
invitation. Never stop or reuse a server this run did not start.

`since:` parallel batches · `holds-while:` a dev server is a shared local resource

## C7 — Coordinate taps that survive a redesign

**Trap:** a case taps at a device coordinate because no identifier existed. After
a redesign the tap still lands on *something*, the assertion still passes, and
the case now measures an unrelated control.

**Rule:** element-relative geometry and identifiers only. A coordinate is
acceptable only as a documented one-off with a comment saying which control it
targets and why it has no identifier.

`since:` first redesign after the suite landed · `holds-while:` the app exposes
accessibility identifiers

## C8 — The recording that started after the interaction

**Trap:** the video file exists but the recorder had not produced its first frame
when the flow began, so the interesting 300 ms are simply absent.

**Rule:** wait for the recorder's readiness line before the first interaction and
treat a zero-byte movie as a failed case.

`since:` first animation case · `holds-while:` capture uses `simctl recordVideo`

## C9 — Simulator numbers presented as performance

**Trap:** an FPS or timing number from a Simulator Debug build is quoted as user-
facing performance, or a threshold is invented for a number that only has value
as a regression baseline.

**Rule:** report Simulator Debug numbers as baselines, state the measurement
limits (callback delivery, not presented frames; whole-process footprint, not
allocations), and never fail a build on an arbitrary threshold.

`since:` first performance case · `holds-while:` the suite runs on Simulator
Debug builds

## C10 — Asserting on translated copy

**Trap:** the case hardcodes a sentence the app renders. Changing the copy fails
an unrelated case, and running in a second language fails everything.

**Rule:** read expected strings from the app's own resource catalog, and keep
fixture content unlocalized so it never participates in a copy assertion.

`since:` first non-English pass · `holds-while:` the app ships resource catalogs

## C11 — Evidence captured after the behavior ended

**Trap:** the screenshot for "message is in flight" is taken after the landing
animation settled, because the capture happens after the assertion.

**Rule:** capture at the moment the claim describes. A case that asserts a
transition needs frames or video *during* the transition.

`since:` send-animation case · `holds-while:` screenshots are taken by driver
steps, not by the app

## C12 — `blocked` used as a soft failure

**Trap:** a real product regression is reclassified as an environment problem
because the failure surfaced as a timeout.

**Rule:** `blocked` is only for the harness being unable to execute or observe —
a server that never started, a ready marker that never appeared, a recorder that
failed. When unsure, keep it `fail`.

`since:` first flaky week · `holds-while:` failure classification is manual

## Routing a new finding

| Kind of feedback | Where it goes |
| --- | --- |
| Product behavior, taste, wording | The product's spec or the component |
| A UI value (radius, inset, duration) | The component, not this log |
| A regression worth preventing | A case in the suite |
| A durable harness rule | An entry here, with `since` and `holds-while` |
| A one-off incident narrative | Field notes, not the checklist |
