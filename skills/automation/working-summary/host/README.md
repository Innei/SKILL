# reports.innei.dev — Worker host

Tiny Cloudflare Worker that serves the working-summary HTML reports from
R2 behind Cloudflare Access. Designed as the backend for the
`working-summary` skill's `publish` choice.

## One-time setup

```bash
cd skills/automation/working-summary/host
pnpm install                                                # or npm/yarn
pnpm wrangler r2 bucket create working-summary-reports      # idempotent-ish
pnpm wrangler deploy
```

`wrangler deploy` registers the custom domain `reports.innei.dev`. The
zone must already be on the same Cloudflare account (no extra DNS step
needed — wrangler creates the route).

Then, in the Cloudflare dashboard:

1. **Zero Trust → Access → Applications → Add an application → Self-hosted**
2. Application domain: `reports.innei.dev` (path: `*`)
3. Policy:
   - Action: `Allow`
   - Include: `Emails` → `i@innei.dev`
4. Save.

The Worker itself does no auth — the Access gate sits in front.

## Local dev

```bash
pnpm dev   # wrangler dev with remote R2 binding (--remote)
```

`wrangler dev` defaults to a local R2 emulator. Pass `--remote` to hit
the real bucket (read-only-ish during dev — be careful with `put`).

## Update flow

- Code changes (`src/index.js`, `wrangler.jsonc`): `pnpm deploy`.
- New report uploads: handled by the skill's `publish` choice, which
  shells out to `wrangler r2 object put`. No Worker redeploy needed.
- Bucket name and route are pinned in `wrangler.jsonc`. Keep
  `output.publish.bucket` in `~/.config/working-summary/config.yaml`
  in sync with the bucket name here.

## Behavior

| Method + Path        | Behavior                                                                          |
| -------------------- | --------------------------------------------------------------------------------- |
| `GET /`              | List bucket, sort by ISO week descending, render minimal HTML index. `no-store`.  |
| `GET /<name>.html`   | Serve the R2 object with `text/html` and `max-age=300`. 404 if missing.           |
| `GET /favicon.svg`   | Inline SVG, `max-age=86400`.                                                      |
| anything else        | 404 plain text.                                                                   |

Key format expected by the index sort: `YYYY-MM-wNN[-N].html`. Anything
else falls into a "misc" section at the bottom.

## Backfill

After the Worker is live and Access is configured, run from the `host/` dir:

```bash
for f in ~/Documents/Obsidian/Reports/*.html; do
  pnpm wrangler r2 object put working-summary-reports/"$(basename "$f")" \
    --file "$f" --content-type "text/html; charset=utf-8" --remote
done
```

> **`--remote` is required.** Wrangler 4 defaults `r2 object put` to the
> local miniflare emulator (state under `.wrangler/state/v3/r2/`); without
> the flag the uploads silently no-op against production R2. The same
> applies to `r2 object get` and `r2 object delete` — always pass
> `--remote` for real-bucket work. `publish_r2.sh` already does this.
