# Harness contract

The harness is a plain CLI in the project. It owns devices, processes, capture,
and exit codes — nothing about the product.

Keep it dependency-free (Python 3 standard library, `axe`, `simctl`, and
optionally `ffprobe`). Every added dependency is a reason the suite stops being
runnable a year from now, and none of them make the driver more reliable.

## CLI surface

```sh
verify run   --config .agents/ios-verify/ios-verify.config.json [--case ID] [--batch NAME]
             [--app PATH] [--output DIR] [--language L] [--udid UDID] [--parallel]
verify lease --config ... --name '<current verify>' -- <command>     # build + run under one lease
verify case  --config ... --case ID [--fail-fast]                    # single case, verbose
verify export --config ... --output DIR --claims FILE --title T --requirement R
verify selftest                                                      # drives the bundled sample app
```

Exit codes are part of the contract:

| Code | Meaning |
| --- | --- |
| 0 | Every selected case held its assertion and produced its evidence |
| 1 | At least one case failed, or produced no result, or missed required evidence |
| 2 | Unusable input: config, claims, output directory, or a blocked prerequisite |
| 3 | Blocked: no device, server could not start, driver cannot express the gesture |

`blocked` is not `fail`. A harness timeout, a Metro that never came up, or a
video recorder that never started must be recorded as blocked so a reviewer does
not read a failed product assertion into it.

## Required behaviors

These are not preferences; each one exists because its absence produced a
miscategorized failure or a corrupted run.

1. **Own your server.** Start it, wait for a readiness *log line* **and** an
   open port, and stop it in a `finally`. Never attach to a server you did not
   start.
2. **Refuse an occupied port** instead of reusing whatever is listening.
3. **Own your device.** Lease by name pattern from a disposable pool, lock it,
   shut it down (not erase) after the run.
4. **Never touch another task's device or server.** An untracked booted device
   is occupied, not free.
5. **Explicit destinations.** Always build and install against the leased udid;
   never let a tool pick a personal Simulator.
6. **One process per appearance pass**, with an explicit reset between cases and
   a pid check after every reset.
7. **Verify the recorder started** before the first tap, and treat a zero-byte
   video as a failed case.
8. **Capture per case, not per batch.** A shared screenshot cannot be attributed
   to a behavior.
9. **Write `results.json` incrementally** so a crash keeps every case that
   already finished.
10. **Diagnose the server, not just the app**, on failure: record whether the
    request arrived, whether the response finished, or whether neither happened.
11. **Bound every wait** and report which identifier timed out.
12. **Never erase credentials or app data** to make a case pass; the suite runs
    without an account by design.
13. **Parallel batches share one server but never one device**, and one failing
    batch never cancels a sibling.
14. **Replace a run's output in place** and use a second directory only for an
    A/B comparison; never silently accumulate runs.

## Artifacts

```text
.artifacts/verify/
├── environment.json            # node/xcode/axe/device/app/commit/dirty/language
├── results.json                # one entry per case per appearance
├── metro.log                   # the run's server, owned by this run
├── light/<case>/               # before.png + before.json, after.png + after.json,
│                               # run.mp4, check.log, probe *.json, failure.*
└── dark/<case>/
```

```jsonc
// results.json — one entry per case per appearance
{
  "case": "composer-glass",
  "appearance": "light",
  "language": "en",
  "status": "passed",            // passed | failed
  "error": "…",                  // present when failed
  "seconds": 41.2,
  "appPid": "812",
  "appLifecycle": "launch"       // or "return-to-root"
}
```

`environment.json` is the provenance for every artifact in the run: without the
commit, the dirty flag, the device, and the toolchain versions, a screenshot
cannot be attributed to a revision.

## Failure classification

| Symptom | Status |
| --- | --- |
| Assertion raised by the case | fail |
| Case script timed out (`TimeoutExpired`) | blocked |
| Ready marker never appeared | blocked |
| Required video missing or zero bytes | blocked |
| Server never reached its readiness line | blocked |
| App missing from `launchctl list` | blocked |

Everything else that raises is a product failure until proven otherwise. When
unsure, keep it `fail` — silently reclassifying a real regression as
environmental is the expensive mistake.

## CI wiring

```yaml
strategy:
  fail-fast: false
  matrix: { batch: [pages, send, chat] }
steps:
  - build once, upload the .app as an artifact
  - download the same .app in every UI job        # identical binary, identical evidence
  - run: verify run --config ... --batch ${{ matrix.batch }}
  - upload results.json + the case directories even on failure
```

- Build the app **once**; a per-batch rebuild makes evidence incomparable.
- Every UI job uploads its own artifacts, including failures — an artifact only
  produced on success is useless for exactly the runs you need to inspect.
- Do not mark the suite required until it has been stable for a week of merges;
  a required check that flakes gets bypassed, and then it protects nothing.

## Round export

`verify export` reads a finished output directory and writes a round directory
(`result.json` + `report.md` + `assets/`) for the `acceptance` skill to ingest.
It never re-runs a case, never publishes by itself, and refuses to write a round
when a claimed case produced no result or a declared evidence type is missing.
See `evidence-and-rounds.md`.
