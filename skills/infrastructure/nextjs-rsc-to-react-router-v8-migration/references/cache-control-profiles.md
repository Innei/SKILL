# Cache-Control profiles

Three-tier header rule and the seven profiles used across the migrated
site. Substitute your own host / domain markers for `<HOST>` and
`<PROJECT>`.

## The 3-tier rule

Every SSR / API / prerender response emits **three** headers:

| Layer      | Header                           | Fallback chain                                                    |
| ---------- | -------------------------------- | ----------------------------------------------------------------- |
| Vercel CDN | `Vercel-CDN-Cache-Control`       | → `CDN-Cache-Control` → `Cache-Control`                           |
| Cloudflare | `Cloudflare-CDN-Cache-Control`   | → `CDN-Cache-Control` → `Cache-Control`                           |
| Browser    | `Cache-Control`                  | (browser only)                                                    |

Policy: **Cloudflare is the designated edge cache** and sits in front
of Vercel. `Vercel-CDN-Cache-Control` is `no-store` for every
function-generated response. Vercel CDN is a pass-through by design.

If your CDN in front is not Cloudflare, swap `Cloudflare-CDN-Cache-Control`
for your provider's header. The idea is the same: **exactly one CDN
tier owns cache**, the other is opted out explicitly.

## The seven profiles

Emit `Cache-Control`, then `Cloudflare-CDN-Cache-Control`, then
`Vercel-CDN-Cache-Control: no-store` (VERCEL_OFF) for every profile.

| Profile       | Route class                                  | Cache-Control (browser)     | Cloudflare-CDN-Cache-Control                                    |
| ------------- | -------------------------------------------- | --------------------------- | --------------------------------------------------------------- |
| `HOME`        | Landing home                                 | `public, max-age=0`         | `public, s-maxage=1800, stale-while-revalidate=3600`            |
| `PAGE`        | Marketing / blog / docs / marketplace pages  | `public, max-age=0`         | `public, s-maxage=3600, stale-while-revalidate=86400`           |
| `SITEMAP`     | Sitemap XML endpoints                        | `public, max-age=0`         | `public, s-maxage=86400, stale-while-revalidate=86400`          |
| `DYNAMIC_OG`  | Runtime-rendered OG images                   | `public, max-age=86400`     | `public, max-age=31536000, immutable`                           |
| `BADGE`       | Star badges, embed images                    | `public, max-age=86400`     | `public, max-age=86400, stale-while-revalidate=86400`           |
| `STATIC_LONG` | Long-lived static assets served by the app   | `public, max-age=86400`     | `public, max-age=86400, stale-while-revalidate=86400`           |
| `FEED`        | RSS / Atom / JSONFeed                        | `public, max-age=7200`      | `public, max-age=43200, stale-while-revalidate=86400`           |
| `NO_STORE`    | Auth-varied / genuinely per-user endpoints   | `private, no-store, max-age=0` | `no-store` (Vercel `no-store` too)                            |

## Apply pattern (RR8)

```ts
import { toHeaderMap, PAGE } from '@/app/lib/cache-control';

export const headers = () => toHeaderMap(PAGE);
```

Every route module MUST export `headers`. Explicit is safer than a
global default — a missing default silently makes a route uncacheable.

## Design decisions

- **Browser TTL is short (or zero) for HTML.** Browsers refetching
  after `max-age=0` still hit Cloudflare and get a HIT. Long browser
  TTL on HTML makes navigating away and back show stale content with
  no way to invalidate.
- **Immutable OG images.** OG URLs embed a content hash; the URL
  changes when the content changes. Cache the URL forever.
- **`stale-while-revalidate` everywhere on Cloudflare.** Under load,
  Cloudflare returns stale HTML while a background revalidation runs.
  Origin gets one request per revalidation window, not per user.
