---
name: dokploy-traefik-traffic-split
description: Use when you need to canary-deploy two HTTP backends on the same Dokploy-managed domain with a percentage split (e.g. migrating an SPA from one framework to another). Covers the critical SPA-asset trap that breaks naive sticky-cookie splits, a path-aware Traefik config that solves it, and a four-phase workflow (backup → dry-run on a canary host → roll to prod → quick rollback).
---

# Dokploy Traefik Traffic Split for SPA Migrations

Canary two HTTP backends (e.g. an old Next.js app and a new Remix app) under one domain with a weighted split that survives SPAs with different build-output paths.

## When to use

- Migrating a frontend between frameworks where build outputs live on different URL prefixes (`/_next/*` vs `/assets/*`, `/build/*`, etc.)
- Running A/B between two long-running services already deployed in Dokploy
- Any percentage-based traffic split on Dokploy's bundled Traefik where you also need session stickiness

If both backends are byte-identical builds behind the same image, a plain Dokploy "Replicas" bump is enough — this skill is overkill.

## Core insight: the SPA asset trap

A naive sticky-cookie weighted split breaks SPAs with divergent asset paths.

1. Browser hits `/`, no cookie, Traefik weighted picks lane A → returns HTML referencing `/assets/<hash>.js` plus a `Set-Cookie`.
2. Browser's **preload scanner** fires 30+ asset requests in parallel. Some land at Traefik before the cookie is reliably attached (HTTP/2 stream ordering, request coalescing, or the browser hasn't committed the cookie yet).
3. Cookieless asset requests get re-rolled by Traefik's weight → some land at lane B.
4. Lane B has no `/assets/<hash>.js` → 404 storm, blank page.

`sticky.cookie` alone cannot fix this — the race is structural.

**Fix:** add path-prefix routers at higher priority. Any request whose path uniquely belongs to one backend bypasses the weighted service entirely and goes straight to that backend. Only document-class requests (HTML, feeds, API, shared paths) run through the weighted+sticky service.

## Architecture

```
Host(`yourdomain.com`)
│
├─ priority 200: PathPrefix(`/_next/`)    → next-backend     (always)
├─ priority 200: PathPrefix(`/assets/`)   → remix-backend    (always)
└─ priority 100: (no path filter)         → weighted+sticky  (50/50, 90/10, ...)
                                            ├─ next-backend
                                            └─ remix-backend
```

The weighted service writes the sticky cookie on its responses (typically HTML). Path-forced routers never touch the weighted service, so they neither read nor write the cookie — and their responses don't depend on it, by design.

## Why SSH-scp the file instead of Dokploy's API

`POST /api/settings.updateTraefikFile` is the documented path but has bitten us twice:

- It does not accept an empty string when you want to disable a file (Zod rejects `traefikConfig` of length 0).
- A YAML that parses but fails Traefik's schema validation (e.g. `http: {}` as a "neutral" placeholder) makes Traefik's file provider refuse to build **any** dynamic config — every router on the host disappears, including the Dokploy panel itself. The panel is then unreachable to fix it. You need SSH access to recover.

Push files with `scp` and delete with `rm`. Traefik watches the directory and reloads in seconds.

## Procedure

### Phase 0 — prerequisites and backup

```bash
# Discover the two backends' internal hostnames and ports
curl -sS -H "x-api-key: $TOKEN" "https://<dokploy>/api/environment.one?environmentId=$ENV_ID" \
  | jq '.applications[] | {name, appName, port:(.domains[0].port // null)}'

# Backup everything you might touch
BAK=/tmp/traefik-backup-$(date +%Y%m%d-%H%M%S)
mkdir -p $BAK
ssh root@$HOST 'cat /etc/dokploy/traefik/dynamic/*.yml' > $BAK/all-dynamic.txt
ssh root@$HOST 'tar c /etc/dokploy/traefik/dynamic' > $BAK/dynamic.tar
```

Backend internal hostnames are the Dokploy `appName` (auto-generated, e.g. `mxspace-shiroi-jpdr7k`). They resolve inside Dokploy's docker network.

### Phase 1 — dry-run on a canary host

**Never test on the production hostname.** Use a sibling subdomain that nothing depends on.

1. Add `canary.yourdomain.com` as a DNS record pointing at the Dokploy server (proxied via CDN is fine).
2. Write a dynamic file with `Host(\`canary.yourdomain.com\`)`:

```yaml
# /etc/dokploy/traefik/dynamic/canary-host.yml
http:
  routers:
    canary-next-static:
      rule: "Host(`canary.yourdomain.com`) && PathPrefix(`/_next/`)"
      service: canary-next-backend
      entryPoints: [websecure]
      tls: { certResolver: letsencrypt }
      priority: 200
    canary-remix-assets:
      rule: "Host(`canary.yourdomain.com`) && PathPrefix(`/assets/`)"
      service: canary-remix-backend
      entryPoints: [websecure]
      tls: { certResolver: letsencrypt }
      priority: 200
    canary-secure:
      rule: "Host(`canary.yourdomain.com`)"
      service: canary-weighted
      entryPoints: [websecure]
      tls: { certResolver: letsencrypt }
      priority: 100
    canary-web:
      rule: "Host(`canary.yourdomain.com`)"
      service: canary-weighted
      middlewares: [redirect-to-https]
      entryPoints: [web]
      priority: 100
  services:
    canary-weighted:
      weighted:
        sticky:
          cookie:
            name: canary_lane
            secure: true
            httpOnly: true
            sameSite: lax
        services:
          - { name: canary-next-backend,  weight: 50 }
          - { name: canary-remix-backend, weight: 50 }
    canary-next-backend:
      loadBalancer:
        passHostHeader: true
        servers: [{ url: "http://<next-appName>:<port>" }]
    canary-remix-backend:
      loadBalancer:
        passHostHeader: true
        servers: [{ url: "http://<remix-appName>:<port>" }]
```

3. Push and watch logs:

```bash
scp canary-host.yml root@$HOST:/etc/dokploy/traefik/dynamic/
ssh root@$HOST 'docker logs --since 30s dokploy-traefik 2>&1 | grep -iE "error|canary"'
# Expect: no errors. If you see "http cannot be a standalone element"
# or schema errors, fix the YAML and re-scp — Traefik will retry on its own.
```

4. Verify three things:

```bash
# (a) Cookieless distribution matches weights
for i in $(seq 1 20); do
  curl -sS "https://canary.yourdomain.com/?cb=$RANDOM" \
    | grep -oE "<distinguishing marker per backend>" | head -1
done | sort | uniq -c

# (b) Path-forced override: cross-cookie should still hit the right backend
curl -sS -o /dev/null -w "%{http_code}\n" \
  -H "cookie: canary_lane=<lane-A-hash>" \
  "https://canary.yourdomain.com/assets/<real-remix-file>.js"
# → 200 even though cookie says lane A

# (c) Sticky on document paths
COOKIE=$(curl -sS -i "https://canary.yourdomain.com/" \
  | grep -i "^set-cookie: canary_lane" | grep -oE "canary_lane=[a-f0-9]+")
for i in 1 2 3 4 5; do
  curl -sS -H "cookie: $COOKIE" "https://canary.yourdomain.com/" \
    | grep -oE "<distinguishing marker>"
done
# → 5/5 same backend
```

5. **Open the canary URL in a real browser**, DevTools Network panel open, hard-refresh, navigate a few internal routes. Watch for any `/some-path/*.js → 404`. If anything 404s, your asset prefix list is incomplete — add another path-forced router.

### Phase 2 — promote to production

Once canary passes for at least a few hours of organic traffic:

1. Copy the canary file, rename, change the host:

```bash
sed 's|canary.yourdomain.com|yourdomain.com|g; s|canary-|prod-|g; s|canary_lane|prod_lane|g' \
  canary-host.yml > prod-host.yml
```

2. Start with a **conservative weight** — 90/10 stable side first.

3. Push:

```bash
scp prod-host.yml root@$HOST:/etc/dokploy/traefik/dynamic/
```

4. Leave the old Dokploy-managed Application domain in place as a fallback. The new file's `priority: 100` outranks the default (Traefik priority defaults to rule length, ~17 for a Host-only rule), so the weighted router wins. If your weighted file ever breaks, Traefik silently falls back to the lower-priority Dokploy router → 100% old backend. This is the kind of safety net you want during a migration.

5. Verify externally (via CDN):

```bash
bash -c '
a=0; b=0
for i in $(seq 1 20); do
  m=$(curl -sS "https://yourdomain.com/?cb=$RANDOM-$i" \
        | grep -oE "<marker A>|<marker B>" | head -1)
  case "$m" in
    "<marker A>") a=$((a+1));;
    "<marker B>") b=$((b+1));;
  esac
done
echo "A=$a B=$b"
'
```

6. **Purge the CDN cache** for the host (Cloudflare: dashboard → Caching → Purge → `https://yourdomain.com/*`). Otherwise the CDN may serve stale HTML from before the split, hiding the change for hours.

### Phase 3 — adjust weight

Either edit on the server (fastest) or scp a new file:

```bash
ssh root@$HOST 'sed -i \
  "s/weight: 90$/weight: 70/; s/weight: 10$/weight: 30/" \
  /etc/dokploy/traefik/dynamic/prod-host.yml'
```

Traefik picks the change up within ~5 seconds. No restart required.

Cadence rule of thumb: 90/10 → observe a day → 70/30 → observe a day → 50/50 → observe → 10/90 → 100/0 then delete the file.

### Phase 4 — rollback (instant)

```bash
ssh root@$HOST 'rm /etc/dokploy/traefik/dynamic/prod-host.yml'
```

Traefik immediately falls back to the Dokploy-managed Application router (100% the original backend). No data lost, no certs to re-issue. If you also need to clear in-flight stickied users, purge the CDN cache and tell users to clear their cookie for the host.

## Critical gotchas (paid for in incidents)

| Gotcha | What happens | Avoid by |
|---|---|---|
| Disabling via `http: {}` placeholder | Traefik schema rejects the file → entire dynamic config build fails → all routers (including Dokploy panel) return 404 → panel becomes unreachable to fix it via UI/API. Requires SSH recovery. | Disable by deleting the file (`rm`), never by writing a "neutral" placeholder. |
| Empty string sent to `settings.updateTraefikFile` API | Zod rejects `traefikConfig` of length 0. | Same as above — manage files via `scp` + `rm`. |
| Reading from Cloudflare cache during canary verification | A `cf-cache-status: HIT, age: 7m` response can convince you the split works perfectly when actually all traffic is the cached HTML from one backend. | Always send `?cb=$RANDOM` cache buster and confirm `cf-cache-status: DYNAMIC` (or test from inside the server bypassing CDN). |
| Backing service deleted from a `@file` reference | If `weighted.services[].name: foo@file` and `foo`'s file gets rewritten or deleted (e.g. when you remove a Dokploy domain), the weighted service references a non-existent backend → 502. | Inline backend `loadBalancer` definitions in your own canary file. Don't depend on Dokploy-managed files. |
| Removing the Dokploy Application domain "to keep things clean" | Triggers Dokploy to rewrite/delete that app's dynamic file. If your weighted file references it via `@file`, broken. Even if you inlined, you lose the priority-default fallback router. | Leave the Dokploy-managed domain. Your weighted router at priority 100 will outrank it; it's a free safety net. |
| Same cookie name across canary host and prod host | Browser sends one cookie to both, possibly steering users into wrong lane on whichever host they hit second. | Use distinct cookie names (`canary_lane`, `prod_lane`). |
| Asset path collision between backends (`/favicon.ico`, `/manifest.json`, `/robots.txt`) | Both backends serve these paths with different bytes. Sticky cookie keeps each user consistent within a session, but anonymous CDN hits may flap. | Either tolerate it (a tiny percentage of cached responses), or set `Cache-Control: private` on those routes in both apps, or add a `PathPrefix` for the shared file mapped to a deterministic backend. |
| Reload via Dokploy `settings.reloadTraefik` API | Sometimes restarts the Traefik container, causing a 5–10 s window where every host (including the Dokploy panel) 521s through Cloudflare. | The file watcher already reloads automatically on file change. Don't call the reload endpoint unless the watcher is genuinely stuck. |

## File reference (canonical template)

```yaml
# /etc/dokploy/traefik/dynamic/<host>-canary.yml
http:
  routers:
    <host>-prefix-A:
      rule: "Host(`<host>`) && PathPrefix(`/<unique-prefix-A>/`)"
      service: <host>-backend-A
      entryPoints: [websecure]
      tls: { certResolver: letsencrypt }
      priority: 200
    <host>-prefix-B:
      rule: "Host(`<host>`) && PathPrefix(`/<unique-prefix-B>/`)"
      service: <host>-backend-B
      entryPoints: [websecure]
      tls: { certResolver: letsencrypt }
      priority: 200
    <host>-secure:
      rule: "Host(`<host>`)"
      service: <host>-weighted
      entryPoints: [websecure]
      tls: { certResolver: letsencrypt }
      priority: 100
    <host>-web:
      rule: "Host(`<host>`)"
      service: <host>-weighted
      middlewares: [redirect-to-https]
      entryPoints: [web]
      priority: 100
  services:
    <host>-weighted:
      weighted:
        sticky:
          cookie:
            name: <host>_lane
            secure: true
            httpOnly: true
            sameSite: lax
        services:
          - { name: <host>-backend-A, weight: 90 }
          - { name: <host>-backend-B, weight: 10 }
    <host>-backend-A:
      loadBalancer:
        passHostHeader: true
        servers: [{ url: "http://<appName-A>:<port>" }]
    <host>-backend-B:
      loadBalancer:
        passHostHeader: true
        servers: [{ url: "http://<appName-B>:<port>" }]
```

## Quick verification commands

```bash
# Live weight distribution (20 hits, no cookie)
bash -c '
a=0; b=0
for i in $(seq 1 20); do
  m=$(curl -sS "https://<host>/?cb=$RANDOM-$i" \
        | grep -oE "<marker A>|<marker B>" | head -1)
  case "$m" in "<marker A>") a=$((a+1));; "<marker B>") b=$((b+1));; esac
done
echo "A=$a B=$b"
'

# Sticky verification — same cookie 5x → same backend 5x
COOKIE=$(curl -sS -i "https://<host>/" | grep -i "^set-cookie: <host>_lane" \
         | grep -oE "<host>_lane=[a-f0-9]+")
for i in 1 2 3 4 5; do
  curl -sS -H "cookie: $COOKIE" "https://<host>/" \
    | grep -oE "<marker A>|<marker B>"
done

# Traefik error scan
ssh root@$HOST 'docker logs --since 5m dokploy-traefik 2>&1 \
  | grep -iE "error|invalid|cannot"'
```
