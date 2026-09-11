# Forcing state on an iOS app

Index — read the heading, then the entry you need. Every recipe here replaces a
temptation to "test the happy path and note the error state as untested".

## A. Scene-level injection (the default)

**When:** any state you can describe.

Add a scene whose host injects the intended services and data, then reach it by
launch argument. This is the only recipe that scales; the rest are variations.

**Trap:** injection must happen at the boundary the feature already takes its
input from. Injecting below it (a fake view, a stubbed store the view does not
read) proves nothing.

## B. Error and offline states

**When:** a failure path is the behavior under test.

Inject a transport/provider that fails deterministically — immediately, on the
first call, or after N successes — and assert the UI's recovery affordance (the
retained draft, the retry control, the error copy read from the catalog).

**Trap:** do not produce failures by taking the network down. That couples the
case to the host network and cannot express "succeeds on the second attempt".

## C. Held request (assert the busy state before it resolves)

**When:** loading, sending, or streaming states.

Make the injected request stay pending until the driver taps a control in the
scene ("complete request"). This removes timing luck from the assertion.

**Trap:** a request that resolves on its own schedule hides the busy state, and
the case passes for the wrong reason when the machine is fast.

## D. Empty, partial, and oversized data

**When:** list, history, or catalog behavior.

Inject providers that return zero rows, a single row, and a page larger than the
viewport. Assert the empty state, the single-row layout, and that the list is
still addressable after scrolling.

**Trap:** assuming offscreen rows are in the accessibility tree — they usually
are not. Scroll, then assert.

## E. Pasteboard fixtures (file, image, video)

**When:** paste, drag-in, or attachment flows.

Set the clipboard to a real file URL with a small host-side helper, then paste
through the app's own path.

**Trap:** injecting the attachment into the process bypasses the paste path
entirely. Also note that a video file can register a poster image; assert the
filename the chip shows, not just that a thumbnail appeared.

## F. Deterministic time

**When:** durations, relative timestamps, debounce.

Inject the clock, or assert on structure that does not depend on wall time
(elapsed counter monotonic during streaming, frozen after completion).

**Trap:** a case that asserts "the duration row exists" while the clock advances
is a flake waiting for a slow machine.

## G. Switching a scene family

**When:** the next case needs a different provider set or app mode.

Relaunch the app with the other launch arguments and record `appLifecycle:
launch` in the result.

**Trap:** trying to switch families with the in-process reset leaves the old
providers alive, and the case silently measures the wrong configuration.

## H. System permission dialogs

**When:** notifications, camera, live activities.

Never drive the system dialog. Inject the permission state the scene should see,
and assert the app's own rendering for granted/denied. When the real dialog is
unavoidable, expect it exactly once per device and make the case tolerant of
both outcomes.

**Trap:** a case that taps a system alert depends on the device's prior state and
fails on the first run of a fresh device.

## I. Reaching a screen by URL

**When:** deep links, universal links, navigation restoration.

Launch with the URL argument and assert the resulting route, the back behavior,
and the returned state. Unknown URLs must leave the current screen alone.

**Trap:** asserting on a URL launch while a JS reload is still in flight; wait
for the ready marker, not for the URL to be read.

## J. Debug-only probes for geometry, timing, and frames

**When:** the claim is about animation, scroll smoothness, or frame timing.

Compile the probe only in Debug, sample on display-link callbacks, write raw
samples to JSON, and stop sampling when the view leaves the window. The case
asserts on the JSON; the reviewer watches the video.

**Trap:** a probe that keeps running after its view is gone attributes another
screen's frames to this case. Also: state the sampling limits in the report
rather than implying the numbers describe the whole run.
