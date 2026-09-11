# Driver: AXe + simctl

Probe the host before trusting any of this; flags differ across versions.

```sh
command -v axe && axe --version
xcrun simctl help io
command -v ffprobe
```

| Tool | Owns |
| --- | --- |
| `axe` | Accessibility queries, selector/coordinate taps, touch/swipe/drag, describe-ui, screenshots |
| `simctl` | Device lifecycle, install/launch/terminate, appearance, content size, device-defaults, logs, authoritative framebuffer recording |
| `ffprobe` | Proving a recorded clip is readable; observed duration/rate/frame count |

`axe` is preferred over `idb` over host-window clicks. Host-window clicking does
not prove native touch semantics and depends on Simulator window geometry.

## Launch and matrix

```sh
DEVICE=$LODY_VERIFY_UDID   # or your leased udid

xcrun simctl boot "$DEVICE" || true
xcrun simctl install "$DEVICE" "$APP"
xcrun simctl ui "$DEVICE" appearance light          # light | dark — switch before each pass
xcrun simctl ui "$DEVICE" content_size large
xcrun simctl terminate "$DEVICE" "$BUNDLE_ID" || true

xcrun simctl launch "$DEVICE" "$BUNDLE_ID" \
  --scene=composerGlass \
  --ui-verify \
  -AppleLanguages '(en)' -AppleLocale en_US \
  -AppleKeyboards '(en_US@sw=QWERTY)'
```

- Language and locale are **launch arguments**, not `defaults write` on the
  device: defaults are global and leak into other tasks.
- `-AppleKeyboards` matters. A non-Latin app language activates an IME that
  holds typed Latin text as composition instead of committing it — always pin a
  Latin keyboard for fixture typing.
- Keep *product* language and *system* language separate: the app runs in the
  matrix language, system controls (keyboard, permission dialogs) stay in one
  language so labels you match on do not move.
- A mode change (different scene family, different providers) requires a
  relaunch. Use the in-process reset for ordinary case-to-case movement, and
  record which one happened in `results.json`.

## Inspect before acting

```sh
axe describe-ui --udid "$DEVICE" > before.json
axe tap --id 'create-session-input' --udid "$DEVICE" --post-delay 0.5
axe describe-ui --udid "$DEVICE" > after.json
```

- Prefer `--id` (accessibility identifier), then `--label` with `--element-type`.
  Use coordinates only when the UI exposes no unambiguous selector.
- If a selector is ambiguous or resolves to a zero-size frame, inspect the
  intended control with `--point` and act on its device coordinates.
- HID commands are fire-and-forget: **dispatch never proves the app processed
  the event.** Always re-read state or capture the postcondition.
- Use `axe batch` for a fixed flow in one session; use discrete commands when
  the next target depends on inspecting the previous state.

## Typing

```sh
axe type 'hello'      # then re-read the field and assert its value
```

- Verify committed text every time; a swallowed keystroke looks like a passing
  step otherwise.
- Non-Latin app language: switch the keyboard (tap the globe label, then key
  `42` to send backspace for held composition) and re-verify. Both steps are
  ugly and both are necessary; keep them in one driver helper rather than
  scattered through cases.
- Pasteboard fixtures come from a tiny host-side Swift helper that sets the
  clipboard to a real file URL, so the app's paste path runs for real. Never
  fake an attachment by injecting a file into the process.
- Disconnect the hardware keyboard for the leased device with a host-side
  helper; with the hardware keyboard attached, software-keyboard geometry is
  never exercised and keyboard cases pass for the wrong reason.

## Video

```sh
xcrun simctl io "$DEVICE" recordVideo --codec=hevc out/run.mp4     # start
# wait for the "Recording started" line on stderr before the first tap
kill -INT $RECORDER_PID                                            # stop, then check size > 0
```

- Confirm the recorder is live before interacting; a recorder that exits early
  leaves a zero-byte file and an unprovable case.
- Keep the original movie. Derive contact sheets or sampled frames as an index
  for review, never as a replacement for the temporal artifact.
- Simulator movies may be variable frame rate. Treat a requested fps as a
  target and verify actual duration and frame count with `ffprobe`.

## Assertions that survive redesigns

- Assert against a **sibling's frame or the window**, never device coordinates.
- Assert on **identifiers and structure**, not on translated copy — and when the
  claim *is* about copy, read the expected string from the app's shipped
  resource files.
- Prefer a bounded state wait (`wait until identifier X appears/enables`) over a
  fixed sleep; when a sleep is genuinely required (animation settle), make it
  explicit and named in the case.
- For geometry, timing, or animation claims, compile a **Debug-only probe** that
  samples frames and writes JSON; assert on that file, and keep the raw samples
  next to the video. The probe must stop when its view leaves the window.

## What the Simulator cannot prove

Physical-device performance, thermal behavior, energy use, haptics, camera
input, and real network conditions. Say so in the case's limits instead of
implying coverage. Gross stalls are visible in Simulator footage; FPS numbers
from a Simulator Debug build are regression baselines, not user-facing
performance.

## Common driver failures and their real cause

| Symptom | Likely cause |
| --- | --- |
| Element missing though it is on screen | Offscreen rows are not in the AX tree — scroll first, or raise `maxDepth` |
| Typed text not committed | Non-Latin IME holding composition; switch keyboard, re-type |
| Keyboard covers the input | Hardware keyboard still attached to the device |
| Tap reported success, nothing happened | HID dispatch is fire-and-forget — assert the postcondition |
| Screenshot is black | Display asleep, or an OS-capture path without the needed permission |
| Ready marker never appears | The scene launched into the wrong mode; check the launch arguments and the pid |
