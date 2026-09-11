---
name: profiling-electron-startup
description: Use when an Electron app feels slow to launch — Dock icon bounces too long, blank or late window, long skeleton before the UI — or when someone hands over a generic "Electron startup optimization" checklist and asks what applies to this app.
---

# Profiling Electron Startup

**Core principle: segment the timeline before touching code.** Most generic advice (bundle main, lazy-load, ASAR, thin preload, defer the updater) is already done in a mature app; the remaining time sits in segments JS cannot reach. Measure first, then only pull levers whose segment is actually big.

## The four segments

```
T0 exec ──A──▶ T1 main.js first line ──B──▶ T2 app `ready` ──C──▶ T3 window shown ──D──▶ T4 UI first frame
```

| Segment | What it is | Who owns it | Typical warm (M-series) |
|---|---|---|---|
| A | dyld, signature checks, Chromium+Node init | macOS / Electron | 90–130ms warm, **1.5–2s** first launch of a new binary (post-update) |
| B | main bundle load + top-level `new App()` | you | 50–70ms; V8 compile ≈ 40% of it |
| C | `whenReady` native tail + `new BrowserWindow` + renderer spawn + first paint | Electron (mostly) | 50ms + 70–80ms + 100–150ms |
| D | module graph eval, React boot | renderer bundle | 300–800ms |

**Dock bounce ends at `ready`** (`applicationDidFinishLaunching`). Nothing in D affects it; nothing in JS can end it earlier than B finishing. There is no native call for it — `app.dock.cancelBounce()` only cancels `dock.bounce()`.

## Recipe

1. **Package first.** Measure the packaged build (`asar`, minified), never `dev`. Run with an isolated `--user-data-dir=<tmp>` — the single-instance lock otherwise exits silently ("Another instance is already running").
2. **Instrument the entry.** Unpack: `npx @electron/asar extract app.asar Resources/app` then **rename `app.asar`** — Electron loads `app.asar` over an `app/` dir. CJS entry: `scripts/instrument-entry.mjs` patches it in place (keeps `.bak`). ESM entry (`.mjs`, `"type": "module"`): imports hoist, so use `scripts/main-probe.mjs` as a wrapper and point `package.json` `main` at it. Both emit `[boot]` lines (uptime at entry / bundle loaded / `ready` / `browser-window-created` / `load-start` / `ready-to-show`) and, with `LOBE_PROF=<file>`, an inspector CPU profile; `LOBE_SCRIPTS=<file>` lists every script V8 parsed before the page loads (find what the boot graph drags in).
3. **Launch N times** with `scripts/launch-timing.sh` — external wall-clock T0 plus the `[boot]` lines. Do one run on a fresh binary to see the A cold cost, then 3 warm.
4. **Split B/C** with the CPU profile → `scripts/cpuprofile-summary.mjs`. Look for: `wrapSafe` / `compileSourceTextModule` (compile), `ModuleJob link` (ESM graph size), native `dlopen`, `View` / `ImageView` (= `new BrowserWindow` native ctor, 60–80ms, not yours — the `icon` option is not what makes it slow).
5. **Split C/D** with `--trace-startup --trace-startup-format=json` → `scripts/trace-summary.mjs`: commit → `firstPaint` → `MarkDOMContent`/`MarkLoad`, resource waterfall, long tasks.
6. Only now pick levers (below). Re-measure after each.

## Levers, with measured payoff

| Lever | Where | Gain | Notes |
|---|---|---|---|
| Show window on loading-screen first paint | preload: MutationObserver for `#loading-screen` → double `rAF` → `ipcRenderer.send`; main: show on that OR `ready-to-show`, idempotent | −230ms to visible window | `ready-to-show` fires at `load`, not first paint; adding `<img>`/text to the loading screen does NOT fix it |
| `module.enableCompileCache()` | rollup/rolldown `output.banner` on the entry chunk | main bundle 55→37ms | banner, not `index.ts`: bundlers hoist chunk `require`s above entry statements |
| Show at creation (`show: true` + `backgroundColor`) | main | −350ms | ~180ms of blank window; users notice — prefer the first-paint lever |
| Lazy `require` native addons at top level | main | 2–3ms each warm, more cold | only if profile shows `dlopen` |
| Lazy-import boot-graph fat (`LOBE_SCRIPTS` list, biggest files first) | app code | 908KB sucrase off the path: −30ms | Only when every caller is already async; a parser/SDK/catalog imported statically by a service is the usual culprit |
| Smaller asar | build | first-launch A only | 100MB+ asars make post-update launches worse |
| Dev: stream Vite transform progress onto the loading screen | serve-only plugin: `transform` hook count → `server.hot.send`; injected client renders it while any boot placeholder exists | dev UX only | placeholder ids: `#loading-screen`, plus React skeleton ids |

## Tried, no gain (don't repeat)

- Creating `BrowserWindow` before an in-process kernel/server boots, gating only `loadURL`: the window is created earlier but the page still waits for the kernel, and its ESM linking competes with window/renderer spawn for the main thread — total unchanged.
- Dropping the macOS `BrowserWindow.icon` option: the 60ms native frame is the ctor itself.
- `enableCompileCache()` inside an ESM entry for its *static* graph: that graph is compiled before any body runs; it only helps dynamic imports after it (still worth it when the big graph is dynamic).

## Common mistakes

- Trusting `process.uptime()` as exec time: its origin is Node init, after segment A. Pair with an external clock.
- `--cpu-prof` is ignored by Electron; use `inspector.Session` from the entry.
- `--trace-startup` default output is protobuf; pass `--trace-startup-format=json`.
- `screencapture` takes ~300ms — useless for catching a 150ms blank frame; prove paint via double `rAF` or the trace.
- Vibrancy/transparent/frame options do not change `new BrowserWindow` cost (tested).
- Reading `app.getPath('userData')` before your own `setPath` pins it.
- Kill leftover Vite on the dev port before restarting `dev` (`lsof -ti :5173 | xargs kill`).
