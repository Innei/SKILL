---
name: nextjs-rsc-to-react-router-v8-migration
description: >
  Use when migrating a multi-locale Next.js RSC / App-Router site to React
  Router v8 so SSR HTML is CDN-cacheable. RSC payload is uncacheable at
  the edge and locale × page count multiplies the bill. Covers ordered
  cuts: strip UA/geo/cookie SSR variance, split `.data` loaders from
  client fetches, restage theme SSR (next-themes + head script +
  /theme-vars.css), split middleware to Vercel Routing Middleware + root
  loader mirror, prerender static, land 3-tier Cache-Control so Cloudflare
  owns cache.
metadata:
  author: innei
  version: "0.1.0"
---

# nextjs-rsc-to-react-router-v8-migration

Migrate a multi-locale Next.js RSC / App-Router site to React Router v8
so its SSR HTML is CDN-cacheable at the edge. The migration is not a
"framework swap" — it is a **cache-frame swap**. RSC payload is
per-request, per-cookie, per-header, and Vercel-only. RR8 gives you
plain SSR HTML that Cloudflare can hold for hours if the response
varies only by URL. The whole workflow enforces that invariant.

The gain is real only when locale × page multiplies the bill. On a
17-locale marketing surface with dynamic OG, sitemaps, and marketplace
pages, RSC payload cost dominates even under ISR. RR8's plain SSR wins
because the CDN can bypass origin for anonymous traffic.

## When to use

- Multi-locale (≥ 5 locales) SSR site whose RSC payload / ISR bill is a
  measurable cost driver.
- Anonymous traffic dominates — the CDN can serve the same HTML to
  everyone in the same locale.
- Team can absorb a phased cut: leave 3–5 URL groups on the legacy
  Next site behind for later ports (privacy/terms, growth pages, …).
- CDN in front is Cloudflare (or any CDN that honours
  `Cloudflare-CDN-Cache-Control`). Vercel-CDN-only stacks lose the
  point — Vercel CDN cannot cache HTML that varies by cookie.

## When NOT to use

- Small site — RSC payload cost is a rounding error; keep Next.
- Heavy Server Components composition — RR8 has no RSC. If your
  product surface is dashboard-shaped and you rely on RSC boundaries
  for streaming/composition, this trade is a loss.
- SSR that legitimately varies per-user (dashboards, auth-gated pages)
  — CDN caching is moot; the migration only pays for anonymous surfaces.
- Vercel CDN is the only CDN and you cannot bring Cloudflare in front.

## Scope

- Marketing / blog / marketplace-style SSR pages, multi-locale.
- Loader-driven data fetch, most of which can move to client-side after
  hydration.
- CSS-in-JS with SSR extraction (antd-style / emotion / stitches).
- Middleware doing locale redirects, UA detection, geo hints.

## Files

- `references/cache-control-profiles.md` — the seven header profiles
  (HOME, PAGE, SITEMAP, DYNAMIC_OG, BADGE, STATIC_LONG, FEED, NO_STORE)
  and the 3-tier header rule.
- `references/loader-triage.md` — decision matrix for splitting a
  loader between SSR-critical, prerender-safe, and client-fetch.
- `references/theme-ssr-recipe.md` — next-themes + inline head script +
  cacheable /theme-vars.css compile-time recipe, incl. antd v6 cssVar
  override gotcha.

## Workflow

```text
[1]  Frame the migration as an edge-cache swap, not a framework swap
[2]  Stand up RR8 shell alongside legacy site (separate Vercel project)
[3]  Move src/app tree to RR8 route config; keep Next-like FS shape
[4]  Kill UA / geo / cookie-derived SSR variance
[5]  Split loader traffic: SSR-critical vs prerender-safe vs client-fetch
[6]  Restage theme SSR: next-themes + inline head script + /theme-vars.css
[7]  Rebuild middleware: Vercel Routing Middleware + root-loader mirror
[8]  Prerender the static surface (blog, about, docs) at build time
[9]  Decouple route-FS from feature-FS: routes/ = entry only
[10] Compile-time-ify runtime CSS via vite virtual modules
[11] Land 3-tier Cache-Control headers per route profile
[12] Cut traffic; leave the legacy Next site on for un-ported URL groups
```

## Per-step notes

**[1] Frame it as a cache swap.** Before touching code, write down the
per-locale RSC / ISR bill and the target `cf-cache-status: HIT` ratio.
If the answer is "we cannot let CDN cache HTML because we personalise
X", the migration will not pay — either fix X (move to CSR) or stop.

**[3] Route FS shape.** Do not flatten. Keep a Next-like nested tree
(`routes/blog/[slug]/page.tsx`, `routes/api/geo/route.ts`,
`routes/docs/[...slugs]/page.tsx`) even though RR8 uses explicit
`routes.ts`. Every page module registers twice via a `localized()`
helper: locale-less path (`/blog/:slug`, default `en`) and prefixed
path (`/:locale/blog/:slug`). One module, two ids.

**[4] Kill SSR variance.** The single rule: **SSR output must vary only
by URL.** No UA sniffing, no cookie-derived theme, no per-request geo.
Move device detection to CSS media queries (or a `matchMedia`-based
`useIsMobile` hook that agrees with those media queries), theme to
next-themes + inline `<head>` script, geo to a client-side `useGeo`
that calls `/api/geo`. If you leave one cookie-varying loader on a
public route, that route stops caching.

**[5] Loader triage.** RR8 loaders re-run on client navigation as
`.data` requests, which the CDN will not cache. Three buckets:

  - **SSR-critical, prerender-safe** (locale/route info, static blog
    metadata) → loader, and prerender at build.
  - **SSR-critical, dynamic** (fresh market/API data needed for first
    paint) → loader, but keep the SSR HTML cacheable by CDN because
    the URL fully identifies the result.
  - **Post-hydration** (marketplace lists, star counts, changelog
    tails) → strip from the loader; fetch client-side after hydration.
    This is the biggest CDN win — the `.data` round-trip disappears.

See `references/loader-triage.md`.

**[6] Theme SSR.** Ship both palettes (light + dark) as one cacheable
stylesheet `/theme-vars.css?v=<hash>`, linked render-blocking from the
root. An inline `<head>` script sets `html[data-theme]` from
localStorage before first paint. antd v6 in cssVar mode re-declares
`--ant-*` on any element carrying `.ant-app` / `[class*='css-var-']`,
so scope the palette blocks to those selectors too, else the light
literals shadow your dark palette on hydration. SSR CSS must be
theme-agnostic: rewrite every appearance-dependent token to a
`var(--ant-*)` reference so first paint picks the correct colour.

See `references/theme-ssr-recipe.md`.

**[7] Middleware split.** Legacy `middleware.ts` becomes two things:

  - `src/middleware.ts` (Vercel Routing Middleware, web-standard
    `Request`/`Response`, `next()`/`rewrite()` from `@vercel/functions/middleware`)
    — runs in prod before the CDN cache. Handles locale redirects,
    AI-tool redirects, `NEXT_LOCALE` cookie.
  - Root loader mirror — Vercel Routing Middleware **does not run under
    `bun run dev`**. Mirror the same locale / redirect logic in the
    root loader so dev matches prod.
  - Vercel's middleware compiler cannot resolve tsconfig path aliases.
    Pre-bundle `src/middleware.ts` (rolldown via vite's dep tree) into
    a self-contained `/middleware.js` in a `build:middleware` step.

**[8] Prerender.** RR8 supports build-time prerender. Ship the entire
static surface (default-locale blog, docs, about, changelog) as HTML
on disk; the CDN turns every one into a permanent HIT. Non-default
locales stay dynamic if the bill allows; prerendering all 17 locales
adds build minutes and repo weight.

**[9] Route/feature FS.** `routes/` holds only route entry files
(`page.tsx`, `route.ts`, `Client.tsx`, `layout.tsx`, `[param]`
segments, `not-found.tsx`, `pending-loading.tsx`). Every feature
implementation the route imports lives in `src/features/<domain>/`.
Sub-features under `[param]` drop the brackets
(`coding/[agent]` → `features/coding/agent`).

**[10] Compile-time-ify runtime CSS.** Any CSS generated in
`route.ts` at request time (theme vars, antd static rules) becomes a
vite virtual module baked at build. The route serves the module
contents with a hash query and a long-lived `Cache-Control`. Zero
runtime cost, infinite CDN cache.

**[11] 3-tier Cache-Control.** Every response ships three headers:

  - `Cache-Control` (browser)
  - `Cloudflare-CDN-Cache-Control` (Cloudflare)
  - `Vercel-CDN-Cache-Control: no-store` (bypass Vercel CDN — deliberate)

Because Cloudflare owns cache, Vercel CDN is a pass-through. Seven
profiles (HOME, PAGE, SITEMAP, DYNAMIC_OG, BADGE, STATIC_LONG, FEED,
NO_STORE) — see `references/cache-control-profiles.md`. Apply per
route via `export const headers = () => toHeaderMap(PAGE)`.

**[12] Phased cut.** Do not port every URL group at once. Leave
privacy/terms, growth pages, im-landing, icon marketplace on the
legacy Next site behind their existing URLs; port them one PR at a
time using the frozen legacy repo as reference. The traffic split
lives at the DNS / edge layer (see the sibling skill
`dokploy-traefik-traffic-split` for the SPA-asset trap that breaks
naive weighted splits).

## Common pitfalls

| Mistake | Fix |
| ------- | --- |
| Framing the work as "Next → RR migration" | It is a cache-frame swap. If Cloudflare cannot cache the resulting HTML, you gained nothing. |
| Any cookie / UA / geo header on the SSR response's `Vary` | SSR must vary only by URL. Move personalisation to CSR. |
| Cookie-derived theme surviving into loader logic | Cannot pre-paint from a cache-hit HTML. Ship both palettes in cacheable `/theme-vars.css`; use next-themes + inline `<head>` script; set `data-theme` from localStorage before hydration. |
| antd v6 cssVar mode shadowing your palette on hydration | antd re-declares `--ant-*` on every element carrying `.ant-app` / `[class*='css-var-']`. Scope palette blocks to those selectors too, and rewrite appearance-dependent SSR tokens to `var(--ant-*)`. |
| Every loader keeps its Next data-fetch verbatim | Every retained loader becomes a `.data` round-trip on client nav. Triage: keep only SSR-critical; move the rest to client fetch. |
| Vercel-CDN-only stack | Vercel CDN cannot cache HTML that varies by cookie. Bring Cloudflare in front and set `Vercel-CDN-Cache-Control: no-store`. |
| Deleting `middleware.ts` before mirroring its logic in the root loader | Dev has no Vercel Routing Middleware — locale redirects vanish, users hit 404. Mirror first, delete second. |
| tsconfig path alias in the middleware bundle | Vercel's middleware compiler cannot resolve aliases. Pre-bundle to a self-contained `/middleware.js` via rolldown before deploy. |
| Runtime CSS generation for theme vars / antd static rules | Move to a vite virtual module baked at build. Hash the URL, long-lived `Cache-Control`, infinite CDN cache. |
| Skipping prerender because "SSR is fast enough" | Prerender is not about latency, it is about turning first-request MISS into permanent HIT. Blog / about / docs default locale must ship as HTML. |
| Flattening the route FS | Keep a Next-like nested tree even under explicit `routes.ts`. It survives contributor rotation and matches URL 1:1. |
| Mixing feature code into `routes/` | `routes/` holds entry files only. All feature code lives in `src/features/<domain>/`. |
| Porting all 17 locale variants at prerender time | Build minutes explode. Prerender default locale only; other locales dynamic. |
| One-shot cut over all URL groups | Phased cut — leave legacy Next site running for un-ported URL groups. Use the sibling skill for the traffic split. |
| Loader boundary shows no pending UI on client nav | RR8 does not render pending UI by default. Add a `pending-loading.tsx` skeleton per route segment (mirrors Next `loading.tsx`). Do not use antd `Skeleton` — the lobehub-ui variant differs. |
| Emoji-lookalike imports from `@lobehub/ui` where `base-ui` fits | Prefer `@lobehub/ui/base-ui` for headless primitives; keeps the SSR CSS smaller and avoids theme-token surprises. |

## Rules

- **SSR varies only by URL.** No exceptions on public routes. If a
  variance is required (auth, session), that route is `NO_STORE`.
- **Skill first, cut second.** Do not remove the legacy site until the
  new site's `cf-cache-status` HIT ratio matches the target.
- **Every route declares a Cache-Control profile.** No implicit
  defaults; explicit `headers` export per route.
- **Middleware logic mirrors in the root loader.** Two homes, one
  behaviour.

## Verification

- [ ] `bun run build` produces `/middleware.js` with no unresolved
      aliases (grep for `@/` in the emitted bundle → zero hits).
- [ ] `bun run start` serves the production build.
- [ ] `curl -I https://<host>/` twice: second response has
      `cf-cache-status: HIT` and `vercel-cache: MISS` (Vercel is
      pass-through by design).
- [ ] No public route emits `Set-Cookie` in its SSR response.
- [ ] `curl -I https://<host>/blog/<slug>.data` returns a body but is
      not cached at the CDN (`cf-cache-status: BYPASS` or `MISS`);
      that route was demoted to a client fetch instead if it appears
      on hot paths.
- [ ] First paint shows the correct theme (light or dark) with no
      white → dark repaint. Test with `prefers-color-scheme: dark`
      and with `theme=dark` in localStorage.
- [ ] `NEXT_LOCALE=zh` cookie on `/blog/foo` triggers `307` to
      `/zh/blog/foo` — both in dev (root-loader mirror) and prod
      (Vercel Routing Middleware).
- [ ] `build/client/blog/**/*.html` exists for the prerendered default
      locale.
- [ ] Every route module exports `headers` and each profile in
      `references/cache-control-profiles.md` appears at least once in
      the emitted route table.
- [ ] Legacy site still serves the un-ported URL groups; traffic split
      config committed alongside the migration cut.
