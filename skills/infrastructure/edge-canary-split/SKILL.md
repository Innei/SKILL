---
name: edge-canary-split
description: >
  Use when rolling out a rewritten site (new framework, new Vercel project)
  behind an existing production domain gradually — cookie-sticky percentage
  split between two origins via a Cloudflare Worker on the zone route, with
  hashed build assets offloaded to R2 so asset traffic never invokes the
  worker. Covers why middleware-based canaries break CDN caching, the
  same-zone-subrequest HTTP trap, cross-bucket cache poisoning, and an R2
  layout that survives many concurrent versions.
metadata:
  author: innei
  version: "1.0.0"
---

# edge-canary-split

Route a fraction of production traffic to a parallel rewrite of the same site
without touching DNS or the stable deployment. A ~130-line Cloudflare Worker
mounted on `<zone>/*` assigns each visitor a sticky bucket cookie, proxies
documents to one of two Vercel origins, and falls back to stable on canary
5xx. Static assets are removed from the equation entirely: both builds upload
hashed assets to one R2 bucket behind a cookie-less CDN hostname, so ~98% of
per-pageview requests never reach the worker (its request-count billing) and
old HTML can never 404 on purged chunks.

The worker exists because the obvious alternative fails: a Vercel-middleware
dice canary runs *behind* the CDN cache, so both variants share one cache key
per URL and the only safe posture is `CDN-Cache-Control: no-store` on
everything — a canary that uncaches your whole site. Workers run *before*
the cache, and their `fetch()` subrequests are cached keyed by the
subrequest URL, which gives each origin its own cache partition for free.

## When to use

- Migrating a production domain to a rewritten app (e.g. Next.js → React
  Router) and you need percentage rollout, stickiness, and instant rollback.
- The zone fronting the domain is Cloudflare; variants are separate origins.
- NOT for per-feature flags inside one app — this splits whole origins.
- NOT needed if the new app ships behind the same deployment (use a
  framework-level rewrite instead).

## Inputs

- Cloudflare zone for the public host; permission to deploy Workers + KV.
- Two Vercel projects: stable (current prod) and canary (rewrite), and their
  canonical `*.vercel.app` production aliases.
- An R2 bucket with a custom domain on the same zone (e.g.
  `web-assets.<zone>`), CORS configured, and a cache rule granting a long
  edge TTL.
- If the domain already runs an older canary mechanism (middleware dice,
  edge-config flags), retire it first — two dice systems re-mix each
  other's buckets and caches.

## Files provided

- `references/worker.example.ts` — the full worker: cookie bucket, KV-driven
  percent, forced `?_canary=1|0` switch, 5xx/error fallback, cache handling.
- `references/wrangler.example.jsonc` — routes, KV binding, origin vars, with
  the load-bearing comments preserved.
- `scripts/upload-static-assets.ts` — zero-dependency Bun script that mirrors
  a build dir into R2; `STATIC_CDN_URL` acts as the master switch.

## Workflow

```text
[1] Assets to R2 (both projects)   vite `base` / next `assetPrefix` ← STATIC_CDN_URL
[2] Worker on a staging hostname   rehearse on a real zone host, never workers.dev
[3] Bucket-side config             CORS (every page origin!), cache rule, lifecycle
[4] Mount worker on the prod route KV percent set BEFORE deploying the route
[5] Verify as a real browser       forced cookie both ways, zero failed CDN loads
[6] Ramp via KV                    percent change is live ≤60s, no deploy
```

### [1] Assets to R2

Key the whole feature off one env var. `STATIC_CDN_URL` unset → build prefix
and upload both no-op (assets stay same-origin); set without S3 credentials →
fail the build, because shipping HTML that references an unpopulated CDN is
worse than either working state. Vite: `base` (build-only). Next:
`assetPrefix` (does not touch `/_next/image` or `public/`). With assets on
the CDN, deployment-skew protection for assets (Vercel `?dpl=` rewriting)
becomes dead weight — gate it off the same variable.

R2 layout: `<project>/<prod|preview>/...` — project × environment only,
**no version directories**. Hashed filenames already content-address
versions; all deployments' assets coexist in one flat namespace and each
HTML references exactly its own set. A version directory would change every
URL every deploy and destroy browser/edge cache reuse. Re-upload everything
on every build (overwrites are content no-ops) so object age means "time
since last referenced by any build" — then R2 lifecycle rules
(`*/preview/` 30d, `*/prod/` 180d) are a correct GC.

### [2] Worker on staging

Rehearse on a real hostname of the zone — workers.dev has no zone, so
subrequest caching never HITs there and the rehearsal proves nothing about
cache behavior. The worker: read `canary_bucket` cookie → else roll percent
(KV `percent` key, `cacheTtl: 60`, env var only as fallback) → rewrite
subrequest host to the chosen origin → append the cookie on first
assignment. Canary GET/HEAD that 5xx or throw are retried against stable
and the user is re-bucketed to stable.

Three non-negotiable details in `fetchOrigin`:

- `originUrl.host = ...`, never `originUrl.hostname` (hostname drops the
  port and breaks local `wrangler dev` origins).
- `originUrl.protocol = 'https:'` — under Flexible SSL the worker sees
  `request.url` as `http://`, and an http subrequest makes Vercel answer an
  infinite 308-to-https loop for every document.
- Origins should be **cross-zone** `*.vercel.app` hosts. Same-zone
  subrequests skip the worker (platform recursion prevention) but can reach
  the origin over plain HTTP — same 308 loop, verified live. Do NOT write
  your own loop guards: the platform already prevents recursion, and a
  host-equality guard silently disables bucketing the day the mounted host
  equals an origin (it did, in production config).

Documents need cache eligibility on the subrequest. Zone cache rules DO
evaluate worker subrequests (verified live: a rule keyed on the origin's
`full_uri` turns MISS→HIT with no cf options), but rules written against
the public hostname never match the subrequest's origin host — so either
add rules keyed on each origin URL, or ship `cf: { cacheEverything: true }`
so the worker is self-contained and independent of dashboard state. Prefer
the latter. TTL still comes from the origin's
`Cloudflare-CDN-Cache-Control`. And force browser
`cache-control` on canary HTML/`.data` to `public, max-age=0,
must-revalidate`: the zone's Browser Cache TTL otherwise stamps ~4h of
browser cache on documents and percent changes take hours to reach
returning visitors.

### [3] Bucket-side config

- CORS: allow every origin pages are served from — production apex, www,
  staging host, and `*.vercel.app` (previews live there). Vite emits
  `crossorigin` module scripts: one missing origin means a blank page the
  moment canary reaches that host.
- Cache rule: R2 custom domains are NOT edge-cached by default; add a rule
  (hostname match → eligible, long edge TTL, consider overriding browser
  TTL — objects uploaded via S3 API may carry no `Cache-Control`; Bun's S3
  client cannot set it).

### [4] Mount on production

Set KV `percent` BEFORE deploying the route change, or the env-var fallback
takes the first minutes of traffic. Keep the staging route mounted as a
permanent rehearsal surface; staging vs prod then differ by route pattern
only.

### [5] Verify as a real browser

curl lies here — see pitfalls. Drive a real browser: force `?_canary=1`,
assert the canary DOM is the new app, count CDN asset loads and failures
via `performance.getEntriesByType('resource')`, check the console, then
`?_canary=0` back. Measure worker load as requests-per-pageview grouped by
host — documents only, single digits.

### [6] Ramp

`wrangler kv key put percent <n> --namespace-id <id> --remote`. Sticky
cookies mean existing users don't flap; only fresh rolls see the new
percent. `percent=0` stops new assignments but existing canary cookies
stick for their lifetime — full rollback also means swapping CANARY_ORIGIN
or removing the route. Structural changes (origins, routes) stay
config-on-deploy deliberately: they deserve a deployment record.

## Common pitfalls

| Mistake | Fix |
| ------- | --- |
| Canary via Vercel middleware | Runs behind the CDN cache; needs `no-store` on everything to avoid variant mixing. Split before the cache (Worker) instead. |
| Worker subrequest to a same-zone hostname | Can arrive at the origin over plain HTTP → Vercel 308-to-https infinite loop. Use cross-zone `*.vercel.app` origins. |
| Inheriting the eyeball scheme from `request.url` | Under Flexible SSL the worker sees `http://` — force `originUrl.protocol = 'https:'`. |
| Hand-written recursion guards | The platform already prevents same-zone worker recursion; a host-equality guard silently passes through 100% of traffic when the mounted host equals an origin. Delete them. |
| `originUrl.hostname = x` | Drops the port; breaks non-443 origins in `wrangler dev`. Set `.host`. |
| Concluding "cache rules don't apply to subrequests" from a curl ablation | They do apply — but host-scoped expressions never match the origin host, and plain-curl probes can hit bot-bypass rules (cache:false), poisoning the experiment. Test with GET + browser UA and a rule keyed on the origin `full_uri` before believing any "rules don't work" conclusion. |
| Letting zone Browser Cache TTL reach canary documents | Returning visitors keep old HTML for hours after a percent change. Stamp `max-age=0, must-revalidate` on HTML/`.data` in the worker. |
| Trusting `curl -I` for cache checks | HEAD reports DYNAMIC even for cached objects; plain curl UA may match bot-bypass cache rules. Probe with GET + a browser UA. |
| Version directories in the R2 layout | Every deploy changes every asset URL → total cache bust. Hashes are the version; directories are project × env only. |
| Skip-if-exists uploads + age-based lifecycle | A chunk unchanged for months gets GC'd while still live. Full re-upload every build makes object age = last-referenced. |
| CORS allowlist missing one page origin | Works on staging, blank page on prod (crossorigin module scripts). Enumerate apex + www + staging + `*.vercel.app`, or use `*`. |
| Two canary systems alive at once | The old middleware dice re-buckets worker-assigned users and skews ratios. Retire the old one (revert + flag cleanup) before mounting the route. |
| Rehearsing on workers.dev | No zone → no subrequest cache → the rehearsal proves nothing. Use a staging hostname on the real zone. |
| Judging the split from a browser that visited pre-cutover | Stale local HTML replays (`deliveryType: "cache"`, `transferSize: 0`) and mimics a routing bug. Re-fetch with `cache: 'no-store'` before diagnosing. |
| Asset responses carrying `Set-Cookie` / consuming a roll | Uncacheable and skews stats. Better: move hashed assets off the worker entirely (R2). |
| Reading percent from env only | Every change needs a deploy. KV + `cacheTtl: 60`; env stays as fallback. |
| Deleting a "stray" branch on a transferred GitHub repo | The old-org remote is a redirect to the same repo — the delete kills the PR's head branch. Check remotes before cleanup. |

## Rules

- One env var (`STATIC_CDN_URL`) is the master switch for the CDN path;
  half-configured states must fail the build, not ship.
- Documents through the worker: browser `max-age=0`; edge caching only via
  origin-host-partitioned subrequests.
- The worker never buffers bodies — `new Response(response.body, response)`
  pipes streams; streaming wall-clock costs no CPU billing.
- Watch `canary_5xx_fallback` / `canary_fetch_error_fallback` events before
  every ramp step.

## Verification

- [ ] Fresh visitor gets `set-cookie: canary_bucket=...`; distribution over
      ~30 cookie-less requests matches the KV percent (0 and 100 exact).
- [ ] `?_canary=1` → 302, cookie, new-app DOM on the prod domain;
      `?_canary=0` reverts.
- [ ] Canary documents `MISS → HIT` with growing `age` on repeat GETs;
      assets untouched (`immutable` intact).
- [ ] All CDN asset loads succeed in a real browser on the prod domain
      (zero `performance` entries with `responseStatus >= 400`).
- [ ] CDN objects: `HIT` on second GET (browser UA), correct `Content-Type`
      for `.js` and fonts, ACAO present for every page origin.
- [ ] Canary 5xx (forced or observed) → stable response + re-bucket cookie.
- [ ] KV percent flip reaches fresh visitors without a deploy (≤60s).
- [ ] Per-pageview worker hits in single digits, grouped by host.
