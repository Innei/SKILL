---
name: electron-native-lib-extraction
description: >
  Use when extracting an in-app Electron native-module integration (N-API
  addon + build scripts + packaging config + release CI) into a standalone,
  source-distributed npm library — or when authoring such a library from
  scratch. Covers the ABI/install-script traps, node-gyp rebuild semantics,
  macOS rpath depth, electron-builder packaging excludes, composite GitHub
  Action hygiene, and the dogfood migration back into the source app.
metadata:
  author: innei
  version: "0.1.0"
---

# electron-native-lib-extraction

An Electron app that grew a native module (N-API addon linking a system
framework, e.g. Sparkle) accumulates four coupled layers: the addon source,
the Electron-ABI build orchestration, the electron-builder packaging config,
and the release CI. Extracting them into a reusable npm package is mostly
mechanical — but most of the failure modes are invisible until a consumer
installs the package or CI runs a real release. This skill encodes the
extraction order and the traps. Reference implementation:
<https://github.com/Innei/electron-sparkle-updater> (Sparkle.framework
bridge + appcast release toolchain, extracted from the Kansoku desktop app).

## When to use

- In scope: source-distributed native npm packages for Electron (consumer
  compiles at build time), macOS framework linking, electron-builder
  integration fragments, composite GitHub Actions for release pipelines,
  migrating the source app onto the extracted library.
- Out of scope: prebuilt binary distribution (prebuildify/node-gyp-build),
  Windows native bridges, ASAR internals beyond asarUnpack.

Inputs: the app's working native integration; a free npm name
(`npm view <name>` → 404 = free); the consumer's Electron version (drives
ABI flags).

## Workflow

```text
[1] Carve the package        addon + scripts verbatim, params for app values
[2] Neutralize npm install   no-op install script, real build = explicit CLI
[3] Runtime loader           null-degrading, path contract for dev/packaged
[4] Rebuild CLI              node-gyp resolved from OWN deps, never npx
[5] Packager fragments       asarUnpack narrow, vendor excluded, sign hook
[6] Release CI as an Action  env-routed inputs, EXIT-trap secrets
[7] Dogfood migration        app consumes the lib; packaged-layout assertion
```

### [1] Carve

Copy the addon source and fetch scripts verbatim (keep their load-bearing
comments — they move with the code). Everything app-specific (repo slug,
feed URL, tag prefix, arch) becomes a parameter. Remove hardcoded `ARCHS`
from binding.gyp; let node-gyp's `--arch` drive it. Parameterize in a
separate, reviewable step after the verbatim copy.

### [2] Neutralize npm install

npm auto-runs `node-gyp rebuild` for ANY package containing a `binding.gyp`,
against the host Node ABI — the wrong target for Electron, and a build the
consumer never asked for. Ship `"install": "node -e \"\""` and put the real
build behind an explicit CLI command. Do not set `gypfile: true` at the
package root. Document why, prominently — the no-op looks like a bug.

### [3] Runtime loader

The loader never throws: non-target-platform → `null` before any path work;
load/shape failure → `null` + log. Two path contracts, both derived from the
package's own `import.meta.url`:

- dev: `<packageRoot>/native/build/Release/<addon>.node`
- packaged: `<resourcesPath>/app.asar.unpacked/node_modules/<pkg>/native/build/Release/<addon>.node`

Provide an `addonPath` override as the escape hatch for exotic layouts.
Import `electron` only lazily inside the one convenience wrapper, so the
core stays loadable (and testable) in plain Node.

### [4] Rebuild CLI

`<pkg> rebuild --electron-version X --arch arm64|x64|universal`:

- node-gyp must be a runtime `dependency`, and the CLI must spawn its bin
  script resolved via `createRequire(import.meta.url)` from the package's
  own install — `npx node-gyp` silently network-fetches an unpinned version
  when the package sits in a consumer's node_modules.
- `node-gyp rebuild` = clean → configure → build, and clean is
  `rm -rf build/`. Any intermediate stashed for a later step (universal
  lipo) must live OUTSIDE `build/` or the second arch pass destroys it.
- Electron ABI: `--dist-url=https://electronjs.org/headers`.
- Auto-detect the consumer's Electron version from their node_modules when
  the flag is omitted.

### [5] Packager fragments

Export a config-fragment function, not documentation alone. The traps:

- electron-builder packs the ENTIRE production dependency. The vendored
  framework (fetched by your build) gets a useless second copy inside
  app.asar unless excluded:
  `files: ["!**/node_modules/<pkg>/native/vendor/**"]`.
- `asarUnpack` must be narrow:
  `**/node_modules/<pkg>/native/build/Release/*.node`, not
  `native/build/**` (which unpacks Makefiles and object files).
- macOS rpath depth is layout-relative. An `@loader_path/../../…/Frameworks`
  entry copied from the app counts from the addon's OLD location; inside
  `node_modules/<pkg>/native/build/Release` the addon sits deeper — recount
  to `Contents/Frameworks` (8 ups for this layout) and verify with
  `otool -l <addon>.node | grep -A2 LC_RPATH`. Electron's own
  `@executable_path/../Frameworks` LC_RPATH can mask a dead entry — the
  framework loading is not proof your rpath is right.
- Ship the afterPack ad-hoc signing hook as an export; consumers wrap it in
  a 3-line file (electron-builder takes a file path). Sign once before dmg
  and zip are packaged so both embed a valid CodeDirectory.
- `prepublishOnly: build` — `dist/` is gitignored; without the guard a clean
  checkout publishes a tarball with no JS and npm omits the dir silently.
- `require()` of your ESM package from a consumer's `.cjs` hook needs Node
  ≥ 20.19 / ≥ 22.12 — set `engines` to match what your samples assume.

### [6] Release CI as a composite Action

- Composite `inputs.*.default` cannot reference other inputs — derive
  composed defaults inside the step body with `${VAR:-default}`.
- Never interpolate `${{ inputs.* }}` inside `run:` bodies (script-injection
  surface). Route every input through the step's `env:` block, reference as
  `"$VAR"`.
- Secrets that touch disk (signing keys): RAM disk + `trap cleanup EXIT`
  with `|| true` guards INSIDE the trap only — `set -e` skips inline cleanup
  when the signing tool fails mid-step.
- An action step that runs `npx <pkg>` executes at the caller's workspace
  ROOT. In a pnpm workspace the bin only exists in the subpackage's
  `node_modules/.bin`, so npx silently falls back to a registry fetch of an
  unpinned version. Caller-side fix: add the package to ROOT devDependencies.
- Pin external tool downloads by version + sha256, verified before extract.

### [7] Dogfood migration

Switch the source app to the library and delete the local copy. The one
assertion that cannot be skipped: run the app's REAL packaging and inspect
the artifact — pnpm's symlinked node_modules is a layout the loader contract
never saw in the lib's own repo:

1. addon at `app.asar.unpacked/node_modules/<pkg>/native/build/Release/`
2. framework at `Contents/Frameworks/`, a real directory
3. `codesign --verify --deep --strict` passes
4. `npx asar list app.asar | grep vendor` comes back empty

If 1 fails, the `addonPath` override is the fix — record the observed
layout. Keep behavior parity explicit: tag prefixes, throttle values,
notification text, and placeholder-injection anchors must survive the
migration byte-for-byte (grep the old constants against the new wiring).

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Install builds the addon against the wrong ABI, wastes minutes | npm auto-runs node-gyp for any package with `binding.gyp` | no-op `install` script; explicit rebuild CLI owns the real build |
| Consumer's rebuild fetches node-gyp from the registry, or fails offline | node-gyp in devDependencies + `npx node-gyp` | move to `dependencies`; spawn its bin via `createRequire` resolution |
| `--arch universal` always fails at lipo | intermediate stored under `build/`; second arch pass's clean removes it | stash intermediates outside `build/` |
| Framework loads in the packaged app but the rpath entry is dead | ups-count copied from the app's shallower addon location; Electron's own LC_RPATH masks it | recount ups for the node_modules layout; verify with `otool -l` |
| Consumer's app.asar carries a full copy of the vendored framework | electron-builder packs the whole dependency | `files` exclusion for `native/vendor/**` |
| Published tarball has no `dist/` | dist gitignored; npm omits missing dirs silently | `prepublishOnly` build script |
| afterPack wrapper throws `ERR_REQUIRE_ESM` on some Node 20.x | require(esm) unflagged only ≥ 20.19 | `engines.node >= 20.19`, noted beside the sample |
| Action step executes an unpinned registry version of your CLI | `npx` at workspace root can't see the subpackage bin | package in caller's ROOT devDependencies |
| Signing key survives on the runner after a failed release | `set -e` aborts before inline scrub | `trap cleanup EXIT`, `\|\| true` only inside the trap |
| Old delta-base archives re-uploaded as the new release's assets | globbing the archive dir after delta bases were fetched into it | record own artifact names BEFORE fetching bases; publish only those |
| Version comparison treats every release as newer after migration | tag prefix not threaded into the generalized compare | prefix is a required parameter; grep every call site |
| Appcast items 404 after a delta rebuild | generator stamps ALL items with the current run's download URL | re-point old enclosures to their own tags (URLs are not signed; safe) |

## Rules

- Extraction is verbatim-first: byte-identical copies, then parameterize in
  a separate reviewable step.
- The library never throws where the app can degrade — `null` contracts on
  every load path.
- One source of truth per pinned value (framework version, placeholder
  string): shell script or exported constant, never both.
- Real-artifact verification beats unit tests for packaging claims: otool,
  codesign, asar list, file-exists on the actual .app.

## Verification

- [ ] `npm pack --dry-run` from a CLEAN clone lists dist/, bin/, native
      sources, scripts — nothing more, nothing missing.
- [ ] Rebuild CLI produces the addon end-to-end on the target Electron
      version; `otool -l` shows the recounted rpath entry.
- [ ] Consumer-side packaging assertions 1–4 (step [7]) all pass on the
      real .app artifact.
- [ ] Action YAML: no `${{ inputs.* }}` inside any `run:` body; secret
      cleanup runs on the failure path.
- [ ] Behavior-parity greps: old constants (URLs, prefixes, notification
      strings) resolve to identical values in the new wiring.
