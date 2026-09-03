---
name: react-rerender-audit
description: >
  Use when a React page re-renders far more than it should — "everything
  re-renders on every tick", live-data dashboards, Electron/Vite apps that
  feel heavy under a 1s push stream. Measures render counts from outside the
  app over CDP (react-scan injected, no source changes), localizes the exact
  hook that fires, fixes it by lowering state to the consumers instead of
  sprinkling memo, and locks the result with a Profiler regression test.
metadata:
  author: innei
  version: "0.1.0"
---

# react-rerender-audit

A page under a live data stream re-renders wholesale: a per-second quote
push repaints a chart, a sidebar, a chat dock, and thirty tooltips that
consume none of it. The instinct is to scatter `memo()` and `useCallback`
until the flashing stops. That treats the symptom — the real cause is
almost always a single `useState` sitting too high in the tree, prop-drilled
through unmemoized intermediates.

This skill measures first, names the exact hook, then moves state down.

## When to use

- In scope: React 18/19 apps with a push stream (WebSocket, SSE, polling,
  `setInterval`), Vite dev server, Electron renderers, browser tabs.
- Out of scope: slow *individual* renders (one component taking 300ms) —
  that is a flamegraph problem, use the DevTools Profiler timeline.
  Production builds — `react-scan` and `<Profiler>` both want dev.

Prerequisites: `react-scan` importable from the app (a devDependency is
enough under Vite), a CDP endpoint, and `agent-browser` (or any CDP client
that can `eval` a string and return it).

## Workflow

```text
[0] Frame           steady-state storm or boot storm? they need different rigs
[1] Attach          launch with a remote-debugging port, confirm the target
[2] Count           arm react-scan, sample, rank BY INSTANCE
[3] Localize        re-run filtered on suspects, dump changed props/contexts
[4] Name the hook   diff fiber.memoizedState vs alternate -> hook index
[5] Fix             lower state to consumers; delete the prop chain
[6] Prove           regression test + re-measure the same page
```

### [0] Frame the question first

Sample the settled page for 10s before anything else. Two different bugs
hide behind "this page re-renders constantly":

- **Steady-state storm** — the idle sample is non-zero. A live stream drives
  the tree. Inject over CDP after load; everything below applies as written.
- **Boot storm** — the idle sample is **zero** and all the churn is in the
  first seconds. Injecting after load measures nothing. You must arm the
  counter *before React mounts*, which the CDP-injection route cannot do.

For a boot storm, look for an arming point the app already has: a
`REACT_SCAN=true` env flag, a devtools dock toggle, a dev-only entry import.
lobe-chat ships `REACT_SCAN` -> `__REACT_SCAN__` -> `scan()` in
`src/initialize.ts`; restarting dev with that flag arms the instrumentation
at boot with zero diff. Failing that, add the collector to the app's entry
module temporarily and revert it when the audit is done — react-scan's
`getReport()` does not backfill what happened before it was armed.

### [1] Attach

```bash
ELECTRON_REMOTE_DEBUGGING_PORT=9222 pnpm dev:desktop   # or: --remote-debugging-port=9222
agent-browser --cdp 9222 get url                       # must be the app URL
agent-browser --cdp 9222 navigate "http://localhost:5173/the/page"
```

`get url` returning `devtools://` means you attached to the auto-opened
DevTools window, not the renderer. Close all targets and reconnect.

### [2] Count

The whole method rests on this one script. `onRender(fiber, renders)` gives
both the render count and react-scan's `unnecessary` flag (props identical
to last render — the component was dragged along, it did not need to run).

```js
// count.js — pipe with: agent-browser --cdp 9222 eval --stdin < count.js
(async () => {
  const { scan } = await import('/@id/react-scan'); // Vite dev id; else 'react-scan'
  const counts = {};
  scan({ enabled: true, showToolbar: false, onRender(fiber, renders) {
    const name = fiber.type?.displayName || fiber.type?.name ||
      (typeof fiber.type === 'string' ? fiber.type : '?');
    for (const r of renders) {
      const c = (counts[name] ??= { total: 0, unnecessary: 0 });
      c.total++; if (r.unnecessary) c.unnecessary++;
    }
  }});
  await new Promise((r) => setTimeout(r, 10000));
  scan({ enabled: true, showToolbar: true, onRender: undefined });
  const rows = Object.entries(counts).sort((a, b) => b[1].total - a[1].total);
  return rows.length + ' components\n' +
    rows.slice(0, 60).map(([n, c]) => `${c.total}\t${c.unnecessary}\t${n}`).join('\n');
})()
```

**Key by instance, not by name.** The snippet above aggregates every
`<ConfigProvider>` in the tree under one row. That is fine for a steady-state
stream and actively misleading for a boot storm: it inflates counts, it makes
a child look like it renders more often than its parent (React cannot do
that), and it hides the most important boot finding of all — the same
component mounted twice. Assign each fiber a stable id and key on it:

```js
const ids = new WeakMap(); let next = 1;
const idOf = (f) => {
  let id = ids.get(f) ?? (f.alternate && ids.get(f.alternate)) ?? next++;
  ids.set(f, id); if (f.alternate) ids.set(f.alternate, id);   // alternates share one id
  return id;
};
const key = nameOf(fiber) + '#' + idOf(fiber);
```

Record `first`/`last` timestamps per instance too — mount waves are visible
in the timestamps long before you understand the cause.

**Reading the table.** Compare each count against `sample seconds × tick
rate`. A 10s sample under a 1Hz push should show ~10 for the handful of
components that display the value, and ~0 for everything else.

| Shape | Meaning |
|---|---|
| A wide band of unrelated components all at the same count | One state owner above them, prop-drilled. Take their common ancestor. |
| One component 10× the tick rate | Its own timer. Look for `setInterval` per instance. |
| High `total`, high `unnecessary` | Dragged along by a parent — a victim, not the cause. |
| High `total`, zero `unnecessary` | Its props really do change every tick — either legitimate, or an object rebuilt upstream. |

Chase the ancestor, never the leaves with the biggest numbers.

**The other failure class: it is not re-rendering, it is remounting.** Group
the instance rows by component name. A provider that should be a singleton
appearing as two instances, with first-render timestamps in two clusters,
means the tree below some point was torn down and rebuilt:

```
inst=2 renders=9  | MarketAuthProvider   | firstMs=72/215
inst=2 renders=7  | LobeThemeProvider    | firstMs=71/215
inst=2 renders=11 | ElectronAppStateSync | firstMs=72/215
```

Memo and state-lowering do nothing here. Walk *up* from the highest
duplicated instance to the first ancestor that is NOT duplicated — the
remount boundary sits between them, and the cause is a **tree-shape change**:
some component conditionally wraps its children, so a falsy-to-truthy flip
inserts a node and React unmounts everything below.

```jsx
if (locale) child = <LocaleProvider locale={locale}>{child}</LocaleProvider>;  // antd ConfigProvider
```

A boot storm hides real costs the render count understates: every provider,
every store init, and every fetch below the boundary runs twice.

### [3] Localize

Re-run filtered to the suspects and dump react-scan's `changes` array —
which prop or hook it believes changed, with before/after values:

```js
scan({ enabled: true, showToolbar: false, onRender(fiber, renders) {
  const name = fiber.type?.displayName || fiber.type?.name;
  if (!['SuspectA', 'SuspectB'].includes(name)) return;
  for (const r of renders) out.push(name + ' ' + JSON.stringify(
    (r.changes || []).map((c) => ({ t: c.type, n: c.name,
      prev: String(c.prevValue).slice(0, 60), next: String(c.nextValue).slice(0, 60) }))));
}});
```

### [4] Name the hook

When the suspect is a large page component (100+ hooks), `changes` is not
enough — ask the fiber directly. Walking `memoizedState` against
`alternate.memoizedState` gives the **hook index** that differs, in
declaration order, so it maps to a line number.

```js
scan({ enabled: true, showToolbar: false, onRender(fiber) {
  if ((fiber.type?.displayName || fiber.type?.name) !== 'SuspectA') return;
  let a = fiber.memoizedState, b = fiber.alternate?.memoizedState, i = 0;
  const diff = [];
  while (a && b) {
    if (a.memoizedState !== b.memoizedState) {
      const isEffect = a.memoizedState && typeof a.memoizedState === 'object' &&
        'tag' in a.memoizedState && 'create' in a.memoizedState;
      if (!isEffect) diff.push(i + ': ' + String(b.memoizedState).slice(0, 40) +
        ' -> ' + String(a.memoizedState).slice(0, 40));
    }
    a = a.next; b = b.next; i++;
  }
  out.push('hooks=' + i + ' changed: ' + diff.join(' | '));
}});
```

**Context reads are not in this list.** `useContext` records into
`fiber.dependencies`, not `memoizedState`, so a component driven entirely by
context shows `hooks=0` and no diff. Walk both:

```js
let da = fiber.dependencies?.firstContext, db = alt.dependencies?.firstContext, j = 0;
while (da && db) {
  if (da.memoizedValue !== db.memoizedValue)
    ctx[j + ':' + (da.context?.displayName || 'ctx')] = (ctx[...] || 0) + 1;
  da = da.next; db = db.next; j++;
}
```

A row like `hooks=0 ctxChg=EmotionThemeContext=18` says it plainly: nothing
this component owns changed, a theme object above it was rebuilt 18 times.

Skip effect hooks (`create`/`tag` shape) — their `memoizedState` churns on
every render by design and drowns the signal. `hooks=122, changed: 0:...`
means: of 122 hooks, only the first one moved. Count 122 `use*` calls down
from the top of the component and read that line.

This is the step that ends the argument. Everything before it is
correlation.

### [5] Fix

Root cause is nearly always **state owned above its consumers**. The fix is
React's own answer, not a memo barrier:

1. Delete the subscription/state from the page component.
2. Each leaf that actually displays the value subscribes itself
   (`useLiveQuote(sym)` inside `TopbarQuote`, not passed in).
3. Delete the whole prop chain. Pass a scalar (`live: boolean`) if the
   leaves need to know whether the stream is on.
4. Derived-value logic that several leaves shared moves into a hook they
   each call (`useLiveBuilt(built, tf, symbol, live)`), not into the parent.
5. Children passed as elements (`dock={<Foo />}`) need nothing — once the
   parent stops re-rendering, React skips them for free.

| Root cause | Fix |
|---|---|
| Page holds `useState` for a stream, drills it down | Subscribe in each consuming leaf |
| Context `value={{ a, b }}` rebuilt every render | Split context, or `useMemo` the value, or move to an external store |
| Per-instance `setInterval` in a widget used N times | One shared subscribable clock, `useSyncExternalStore` |
| Object/array prop rebuilt inline every render | Hoist, or derive inside the child from scalars |
| Conditional wrapper (`if (x) child = <W>{child}</W>`) flips after an async load | Keep the shape stable — always render the wrapper, pass a fallback value |
| One giant component subscribing to N stores to run init hooks | Split per concern; each init hook in its own leaf component |
| Global event subscription in a shared hook (`bindI18nStore`, a store's `subscribe`) fires per batch | Drop the broad binding; emit one refresh after the batch settles |
| A hidden pane (`<Activity mode="hidden">`, a collapsed panel, a `display:none` tab) mounts its full subtree | Thread the existing `enabled` flag all the way to the leaves — including sibling components the flag never reached |

Reach for `memo()` only when a leaf genuinely receives changing props and
is expensive. `memo` on a component whose parent should not have rendered
is a bandage over the real bug.

### [6] Prove

Two artifacts, both required.

**For a remount, count mounts, not commits.** A `<Profiler>` cannot tell a
remount from a re-render; a child with `useEffect(() => { mounts++ }, [])`
can. Assert it stays at 1 across the async transition that used to remount:

```tsx
render(<Locale defaultLang="zh-CN"><MountCounter /></Locale>);
expect(mounts).toBe(1);
resolveLocale({ locale: 'zh-cn' });      // the async load that flipped the wrapper
await waitFor(() => expect(getAntdLocale).toHaveBeenCalled());
expect(mounts).toBe(1);                  // was 2 before the fix
```

**Regression test.** `<Profiler>` around the subtree that must not move.
Mock the transport, push one message, assert zero commits:

```tsx
let dockCommits = 0;
render(<Sidebar live dock={<Profiler id="dock" onRender={() => dockCommits++}><Dock /></Profiler>} />);
dockCommits = 0;                                  // discard mount
act(() => subs[0].onPayload({ quotes: [{ symbol: 'NVDA.US', last: 123.45 }] }));
expect(screen.getByText('$123.45')).toBeTruthy(); // the value did arrive
expect(dockCommits).toBe(0);                      // and nobody else moved
```

Assert both halves. `dockCommits === 0` alone also passes when the feature
is broken.

**Re-measure.** Run `count.js` again on the same page, same sample length,
and report before → after per component. Numbers, not "feels faster".

**Assert the page actually loaded before you trust a sample.** A boot sample
taken from a run that stalled on a skeleton, an error boundary, or a failed
request measures the shell and nothing else — and it looks like a clean,
small number. Return a `loaded` flag alongside the counts and refuse any
sample where it is false:

```js
const loaded = !document.querySelector('[class*=keleton]') && document.body.innerText.length > 500;
```

Cross-check the component names too: if the user can see a sidebar full of
rows and your top-30 is nothing but providers, you measured a different page
than the one they are complaining about.

**Then ask whether the mounted components are even on screen.** Group the
instances by mount timestamp; a late wave is usually one list. Resolve each
one's DOM node and measure it:

```js
const el = domOf(fiber);   // walk fiber.child until stateNode is an Element
const r = el.getBoundingClientRect();
const hidden = r.width === 0 || r.height === 0 || el.offsetParent === null;
```

`72 rows, visible=0` turns a vague "the page is heavy" into a specific bug.
Walk that node's DOM ancestors printing `display` / `visibility` / box size to
find which wrapper hides it, then map that element back to a component
(`el[Object.keys(el).find(k => k.startsWith('__reactFiber$'))]`) to name the
owner. Burned once — a local database
version mismatch held the app on its skeleton, and a 454-render sample got
reported as the fix's before/after when the real boot was 27,000.

## `<Profiler>` vs react-scan

`onRender(id, phase, actualDuration, baseDuration, startTime, commitTime)`
reports **commits of the wrapped subtree** — not per-component counts, not
why. React 19 dropped the old `interactions` argument.

- **Use react-scan** to explore: it enumerates every component and flags
  `unnecessary`, with zero source changes.
- **Use Profiler** to assert: it is a plain React API, works in vitest, and
  survives in the repo as a regression guard.
- **Profiler as a fallback explorer**: no react-scan available → wrap 4-5
  page regions with distinct `id`s, count commits, bisect into the loser.
  Coarse, but it needs no tooling.

Profiler is a no-op in production builds unless you alias
`react-dom/profiling`.

## Traps

- Auto-opened DevTools steals the CDP target. Verify with `get url` first.
- The Vite dev import specifier is `/@id/react-scan`; a bare `'react-scan'`
  fails inside an `eval`'d dynamic import.
- Restore the toolbar and clear `onRender` at the end of every script —
  a live `onRender` closure keeps accumulating and skews the next sample.
- Sample the *same* page state before and after. A page with the stream off
  (`live=false`) still re-renders on every tick when the bug is present;
  that is a diagnosis, not an excuse to switch pages mid-audit.
- HMR after the fix inflates the first sample by a few renders. Reload,
  wait, then sample.
- Effect hooks make step [4] noisy. Filter them, or the real change hides
  among fifty churning effect objects.
- `getReport()` only covers what happened after react-scan was armed. There
  is no way to recover a boot storm you did not instrument in advance.
- Anonymous rows (`?`) are usually context providers, `memo`, or
  `forwardRef`. Stash a sample fiber on the row (`c.f = fiber`) and read
  `fiber.type.toString().slice(0, 200)` afterwards — the first line of source
  identifies it, then grep the repo for that line.
- HMR-triggered reloads inflate a sample. Take the before/after numbers from
  full reloads only, and state which page state you sampled.
- `useTranslation` with react-i18next's `bindI18nStore: 'added'` subscribes
  every consuming component to every resource-bundle load. An app that lazy-
  loads namespaces then calls `reloadResources` re-renders **every translated
  component** once per bundle — dozens of full-tree passes with no state of
  your own changing. The tell: `propsSame` high, own `useState` slots
  unchanged, and the `useTranslation` state slot (`{t,ready,lng,keyPrefix}`)
  changing on nearly every render.
- A `useMemo`/`useCallback` slot (`arr[2]`) changing every render is a
  symptom, not a trigger — it means deps are unstable, but something else
  scheduled the render. Look for the `useState`/store slot that moved, or
  for no moved slot at all (then it is context or an external subscription).
