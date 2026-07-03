# Loader triage

RR8 loaders re-run on client navigation as `.data` requests. Every
`.data` round-trip is a **CDN miss** for that route on that user's
next click — the CDN cannot cache per-user `.data` responses. Loader
composition, not framework choice, decides whether your CDN win holds
after hydration.

## The three buckets

Classify every legacy `getServerSideProps` / RSC fetch into one bucket.

| Bucket | Where it runs | When to use | CDN behaviour |
| ------ | ------------- | ----------- | ------------- |
| **SSR-critical, prerender-safe** | Loader + build-time prerender | Locale metadata, static blog frontmatter, default-locale page shells | Prerendered HTML on disk; permanent CDN HIT after first fetch |
| **SSR-critical, dynamic** | Loader (SSR only) | Fresh market/API data required for correct first paint (SEO, OG), URL fully identifies the result | HTML cached by CDN under the URL; `.data` fetch on nav is a miss but tolerable if navigation cost is low |
| **Post-hydration** | Client fetch after mount | Star counts, recommendation lists, changelog tails, marketplace grids, any list that changes between requests | Loader-free route; `.data` disappears; CDN cache holds indefinitely |

## Decision matrix

For every legacy fetch, ask in order:

1. **Does first paint break without this data?** If no → **Post-hydration**.
2. **Does the URL fully identify the result?** If no → **Post-hydration**.
   (e.g. per-user recommendations vary by cookie → SSR would need to
   `Vary` on that cookie → CDN cannot cache HTML → move to CSR.)
3. **Does the data change between requests within the CDN TTL window?**
   If no → **SSR-critical, prerender-safe** → prerender it.
   If yes → **SSR-critical, dynamic** → keep in loader; watch the
   client-nav cost.

## Client-fetch pattern

For a **Post-hydration** move, the pattern is:

- Remove the fetch from the loader.
- On mount, fire it via SWR / react-query / your fetch primitive with
  a stable cache key (usually the URL).
- Render a skeleton until the client fetch resolves.

The route now serves as pure cacheable HTML at SSR time, and every
subsequent nav to the same URL is a CDN HIT with a client-side data
refresh.

## What we moved on this migration

The concrete triage on the source project — take as reference, adapt
to your surface.

| Route class | Before (Next RSC) | After (RR8) | Rationale |
| ----------- | ----------------- | ----------- | --------- |
| Blog post pages | RSC render + `getStaticProps` fallback | Loader + prerender (default locale) | Static frontmatter + long TTL; permanent HIT |
| Marketplace list (agents / MCP / skills) | RSC render, per-request market API call | No loader; client SWR fetch on mount | Data varies per hour; not needed for first paint SEO shell |
| Docs pages | RSC render | Loader + prerender | Same reasoning as blog |
| Home | RSC render | Loader (dynamic, HOME profile) + prerender for shell | Star counts move to CSR |
| Changelog list | RSC fetch on every render | Loader for latest N (SEO-relevant), client fetch for the tail | Split by scroll position |
| Sitemap XML | Route handler | Route handler + SITEMAP profile | Long TTL, no client nav involved |

## Rules

- **Never** put per-user or per-cookie data in a loader on a public
  route. That single loader breaks CDN caching for the whole page.
- **Prefer** deleting a loader over shrinking it. The `.data`
  round-trip is the tax you pay for keeping any loader at all on that
  route.
- **Always** verify: `curl -I` the route twice — second call must
  return `cf-cache-status: HIT`. If not, a loader or a header is
  still varying.
