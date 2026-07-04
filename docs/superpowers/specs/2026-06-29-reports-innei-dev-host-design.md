# reports.innei.dev — Weekly Working-Summary Host

**Date:** 2026-06-29
**Owner:** Innei
**Status:** Spec — awaiting implementation

## 1. Purpose

Publish working-summary weekly HTML reports to a private-but-cloud
addressable URL so they can be opened from any device without needing
the Obsidian vault on hand. Existing reports already render locally
via `render_html.py`; this project adds the publish surface.

Non-goals: no comments, no editing, no markdown source publishing, no
multi-author flow, no auto-summarization, no preview cards.

## 2. Access model

- Cloudflare Access application sits in front of `reports.innei.dev/*`.
- Allow policy: `email = i@innei.dev`. No other identities.
- Upload path bypasses Access entirely — the skill uses `wrangler r2 object put`
  with the user's API token, which talks to R2 directly.
- Access is configured once via the Cloudflare dashboard; the Worker
  is not involved in auth.

## 3. Topology

```
Browser → reports.innei.dev (CF Access gate, email = i@innei.dev)
       → reports-host Worker (custom domain route)
         ├─ GET /            → bucket.list() → minimal HTML index
         ├─ GET /<name>.html → bucket.get(name) → text/html
         └─ GET /favicon.ico → inline data URI
       ↑ wrangler r2 object put (skill `publish` choice)
       R2 bucket: working-summary-reports
```

## 4. R2 bucket

- **Name:** `working-summary-reports`
- **Layout:** flat — every object key is the filename produced by the
  existing `output.filename` placeholder, e.g.
  `2026-06-w26.html`, `2026-05-w20-1.html`.
- **No manifest, no sidecars.** Index is computed at request time
  from `bucket.list()`.
- **Content-Type:** `text/html; charset=utf-8`. Set at upload time via
  `wrangler r2 object put --content-type=text/html`.

## 5. Worker

Single-file JS module, ~70 lines, no dependencies beyond the Workers
runtime + R2 binding.

### 5.1 Routes

| Method + Path        | Behavior                                                                                            |
| -------------------- | --------------------------------------------------------------------------------------------------- |
| `GET /`              | List bucket, sort by parsed ISO week descending, render minimal HTML index                          |
| `GET /<name>.html`   | Fetch object, return body with `Content-Type: text/html`, `Cache-Control: public, max-age=300`      |
| `GET /favicon.ico`   | Inline data URI (or a tiny embedded SVG) — keeps the asset list to zero                             |
| anything else        | 404 with a one-line plain-text body                                                                 |

### 5.2 Index rendering

- Parse each key with regex `^(\d{4})-(\d{2})-w(\d+)(-\d+)?\.html$`.
  Keys that don't match are listed at the bottom under a "misc" section
  (defensive — should be empty in practice).
- Sort matching keys by `(year, week, suffix)` descending so the latest
  week is first.
- Each row: `<a href="/{key}">{key}</a>  <span class="size">{KB}</span>
  <span class="ts">{uploaded YYYY-MM-DD}</span>`.
- Uploaded date comes from `R2Object.uploaded`.
- Minimal CSS inlined: monospace, dark/light auto, two-column-ish.

### 5.3 R2 binding

- Binding name `BUCKET`, type `r2_bucket`, bucket `working-summary-reports`.
- Wrangler config commits the binding; secrets/API tokens are NOT in the
  repo.

### 5.4 Caching

- `Cache-Control: public, max-age=300` on `/<name>.html` responses.
- Index is NOT cached at the edge — `Cache-Control: no-store`. The index
  must reflect a newly uploaded report within seconds.

## 6. Code layout

```
skills/automation/working-summary/host/
├── wrangler.jsonc        # Worker name, custom domain route, R2 binding
├── src/
│   └── index.js          # The Worker
├── package.json          # devDependency: wrangler
└── README.md             # Quickstart + deploy instructions
```

- `wrangler deploy` from the `host/` directory.
- The `host/` directory is part of the skill repo because the Worker
  is tightly coupled to the `publish` choice in the skill itself.

## 7. Skill integration

### 7.1 New end-of-run choice

The end-of-run prompt gains `publish` as a peer choice. Valid forms:

```
no  md  html  both  linear  publish
md+publish  html+publish  both+publish  linear+publish  linear+html+publish
```

Composition rules:

- `publish` implies HTML generation. If the user picks `publish` alone,
  `render_html.py` runs into a tempfile, gets uploaded, and the tempfile
  is left in `$TMPDIR` (same as the bare `html` choice).
- `publish` does NOT imply local persistence. To keep a local copy, pair
  with `html` or `md`.
- `publish` is order-aware in the composite: it runs AFTER `linear` (so
  the Linear issue exists before publishing) but does not block on it.

### 7.2 Config

Add optional `output.publish` block in `config.yaml`:

```yaml
output:
  format: html         # may be set to `publish`, `html+publish`, etc.
  publish:
    bucket: working-summary-reports
    base_url: https://reports.innei.dev
```

- If `output.publish` is absent, the `publish` choice is hidden from the
  end-of-run prompt and any composite containing it is rejected with a
  clear message.

### 7.3 Upload script

New `scripts/publish_r2.sh` (bash, calls `wrangler`):

```
publish_r2.sh <bucket> <local-html> <key>
  → wrangler r2 object head <bucket>/<key>
      → if 200: prompt user [overwrite / suffix / skip]
      → if 404: continue
  → wrangler r2 object put <bucket>/<key> --file <local> \
      --content-type "text/html; charset=utf-8"
  → echo "https://{base_url}/<key>"
```

- Bucket and base_url are passed as arguments (the skill reads them from
  `output.publish` in config).
- The conflict prompt is the skill's existing "ask user" path, not an
  interactive shell prompt inside the script.

## 8. Backfill

One-shot manual step performed by the user after the Worker is live and
Access is configured:

```bash
cd ~/Documents/Obsidian/Reports
for f in *.html; do
  wrangler r2 object put working-summary-reports/"$f" \
    --file "$f" --content-type "text/html; charset=utf-8"
done
```

Five files upload (W14 has only md and is skipped; W20 has two HTMLs,
both upload). User verifies the index lists all five then declares
backfill done.

## 9. Out of scope

- Markdown rendering on the Worker side. The Worker only serves pre-rendered HTML.
- Deletion API. To remove a report the user runs `wrangler r2 object delete` manually.
- Per-report ACL beyond CF Access. The single `email = i@innei.dev`
  policy gates everything.
- Multi-user / team distribution.

## 10. Verification checklist

After deployment:

1. `https://reports.innei.dev/` → CF Access login screen → email
   challenge → index page renders 5 reports.
2. Click `2026-06-w26.html` → opens HTML, same content as the local
   `~/Documents/Obsidian/Reports/2026-06-w26.html`.
3. From skill: end-of-run `publish` choice produces a URL and the index
   shows the new report within one refresh.
4. Conflict path: re-run skill on the same week with the same filename,
   confirm the head check fires and the user is asked.
5. Access policy: log in as a non-`i@innei.dev` Google identity, confirm
   denied.
