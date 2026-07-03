# Theme SSR recipe

Ship a theme-aware first paint from a URL-only-varying SSR HTML.

**Rule:** SSR CSS is theme-agnostic. Both palettes ship as one
cacheable stylesheet. An inline `<head>` script sets `html[data-theme]`
from localStorage before first paint. All appearance-dependent tokens
resolve to `var(--ant-*)` references inside the SSR-emitted CSS, so
first paint picks up whichever palette the `data-theme` attribute
selected.

## The four moving parts

| Part                          | Where it lives                             | Cost model                       |
| ----------------------------- | ------------------------------------------ | -------------------------------- |
| Palette stylesheet            | Route: `/theme-vars.css?v=<hash>`          | Compile-time; long-lived CDN cache |
| Pre-paint script              | Inline `<head>` script emitted by root loader | Zero runtime; runs before body |
| Theme provider                | `next-themes` mounted client-side          | Zero SSR effect                  |
| SSR CSS emitter               | antd-style / emotion / stitches            | Every token → `var(--ant-*)`     |

## /theme-vars.css structure

The stylesheet contains four blocks:

1. `:root, html[data-theme='light'] [class*='css-var-'], html[data-theme='light'] .ant-app { --... }` — light palette.
2. `html[data-theme='dark'], html[data-theme='dark'] [class*='css-var-'], html[data-theme='dark'] .ant-app { --... }` — dark palette.
3. `html[data-theme='dark'] [class*='css-var-'] { --ant-<comp>-...: <dark-value>; }` — antd v6 component-token overrides for dark mode.
4. Component-specific dark-mode fixups (button primary, checkbox, radio) that antd's cssVar mode does not cover.

Ship it via a vite virtual module baked at build:

```ts
// vite.config.ts
import { themeVarsVirtualModule } from './scripts/viteThemeVarsPlugin';

export default defineConfig({
  plugins: [themeVarsVirtualModule(), ...],
});
```

```ts
// src/app/routes/theme-vars.css/route.ts
import { STATIC_LONG, toHeaderMap } from '@/app/lib/cache-control';

export async function loader() {
  const { css } = await import('virtual:lobehub/theme-vars-css');
  return new Response(css, {
    headers: {
      ...toHeaderMap(STATIC_LONG),
      'Content-Type': 'text/css; charset=utf-8',
    },
  });
}
```

The href is stamped with a short content hash so the URL changes only
when the palette changes. Long CDN TTL, no revalidation.

## The pre-paint script

Root loader emits this inline in `<head>`, before any CSS link:

```html
<script>
  (function () {
    var saved = localStorage.getItem('theme');
    var mode = saved || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', mode);
    document.documentElement.style.colorScheme = mode;
  })();
</script>
```

Then `<link rel="stylesheet" href="/theme-vars.css?v=<hash>">` (render-blocking).

The order is critical: `data-theme` must land on `<html>` before the
palette stylesheet parses, or the light block wins.

## Force-dark routes

Some pages (CLI, Discord landing) are always dark regardless of user
preference. Do this via `forcedTheme` on next-themes' provider on the
matching route, not by writing to localStorage. The user's stored
preference stays intact for other pages.

## antd v6 cssVar gotcha (the big one)

antd v6's `cssVar` mode re-declares every `--ant-*` component token on
any element carrying `.ant-app` or `[class*='css-var-']`, using the
**SSR-light literals**. Naively, your palette blocks on `:root` /
`html[data-theme='dark']` get shadowed on those elements, and only the
top-level page has correct dark colours.

Fix: scope the palette blocks to those exact selectors too:

```css
html[data-theme='dark'],
html[data-theme='dark'] [class*='css-var-'],
html[data-theme='dark'] .ant-app {
  /* ... palette declarations ... */
}
```

Then, for each antd component's dark-mode token overrides, glob
`antd/es/*/style/token.js`, re-run each `prepareComponentToken`
against dark tokens, and emit the diff scoped to
`html[data-theme='dark'] [class*='css-var-']`. This ships inside the
same `/theme-vars.css` — no runtime cost, no client bundle.

## Appearance-dependent SSR tokens → var()

For antd-style's `customToken` hook, rewrite every appearance-dependent
token to its `var(--ant-*)` reference so SSR-emitted CSS is
theme-agnostic:

```ts
export const cssVarTokenOverrides = (() => {
  const overrides: Record<string, string> = {};
  for (const [key, lightValue] of Object.entries(lobeThemeTokens.light)) {
    if (POLISHED_CONSUMED_TOKENS.has(key)) continue;
    if (typeof lightValue !== 'string' || lightValue === lobeThemeTokens.dark[key]) continue;
    const ref = (cssVar as unknown as Record<string, string>)[key];
    if (ref) overrides[key] = ref;
  }
  return overrides;
})();
```

`POLISHED_CONSUMED_TOKENS` (e.g. `colorPrimary`, `colorBgMask`) stay
literal because upstream helpers run `polished`'s `safeReadableColor` /
`rgba` on them, which cannot parse `var()` strings. Mirror those two
literals in a dark-mode override block by hand.

## Verification

- [ ] First paint: `html[data-theme]` attribute is set before the body
      paints. Test via DevTools → Rendering → prefers-color-scheme.
- [ ] `/theme-vars.css?v=<hash>` returns `STATIC_LONG` cache headers.
- [ ] Loading the page in dark mode does not repaint white → dark on
      hydration.
- [ ] Force-dark routes render dark even when the user has `theme=light`
      in localStorage. Switching back to a non-force-dark route
      restores the stored preference.
- [ ] Component-level dark tokens (button hover, checkbox tick,
      radio dot) look correct — these are the ones antd v6 cssVar
      mode would otherwise leave as light literals.
