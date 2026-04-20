---
name: cloudflare-r2-upload
description: Use when uploading one or many files to a Cloudflare R2 bucket and returning public URLs via a bound custom domain. Covers wrangler CLI and the REST API (Cloudflare API token) paths, batched uploads, MIME handling, correct account selection for multi-account setups, and post-upload public-URL verification. Triggers on tasks like "upload these images to R2", "push assets to the uploads bucket", "put files under <prefix>/ on R2".
---

# Cloudflare R2 Upload

Use this skill when the task requires pushing local files to a Cloudflare R2 bucket and producing stable public URLs through a bound custom domain (for example `object.innei.in`).

## Scope

- Target task class: single-file or batched uploads into one R2 bucket under a specified key prefix.
- Supported auth paths:
  - `wrangler` CLI with an existing OAuth session.
  - `wrangler` CLI with `CLOUDFLARE_API_TOKEN` env (from a Cloudflare API token, e.g. stored as `R2_API_KEY`).
- Out of scope: bucket creation, custom-domain binding, CORS / lifecycle config, signed URLs, multipart uploads of files >300 MB.

## Inputs

| Variable | Meaning |
|---|---|
| `R2_API_KEY` | Cloudflare API token with R2 write scope. Optional if `wrangler` already has an OAuth session. |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account that owns the bucket. Required if the authenticated user belongs to multiple accounts. |
| `BUCKET` | Target R2 bucket name (e.g. `uploads`). |
| `KEY_PREFIX` | Object key prefix, e.g. `mx-space/topics/`. Always ends with `/`. |
| `PUBLIC_DOMAIN` | Custom domain bound to the bucket, e.g. `object.innei.in`. |
| `SRC_DIR` | Local directory containing files to upload. |

## Workflow

```text
[1] Identify account + bucket
      -> wrangler whoami to list accounts
      -> wrangler r2 bucket list (per candidate account) to find BUCKET

[2] Upload each file
      -> wrangler r2 object put BUCKET/KEY --file=PATH --content-type=MIME --remote

[3] Verify via public domain
      -> curl -sI https://PUBLIC_DOMAIN/KEY and assert HTTP 200

[4] Report final URLs
      -> https://PUBLIC_DOMAIN/KEY for each uploaded file
```

## Auth Setup

Prefer an existing `wrangler` OAuth session — simplest path:

```bash
wrangler whoami
```

If OAuth is unavailable, use an API token instead:

```bash
export CLOUDFLARE_API_TOKEN="$R2_API_KEY"
```

If the user belongs to multiple accounts, always set `CLOUDFLARE_ACCOUNT_ID` explicitly; otherwise `bucket list` / `object put` may default to the wrong account and fail with `code: 10042 — Please enable R2 through the Cloudflare Dashboard`, which actually means "this account has no R2, try another account".

## Finding the Right Account

`wrangler whoami` prints an account table. For each account id, list buckets until the target bucket is found:

```bash
for acct in <id1> <id2> <id3>; do
  echo "=== $acct ==="
  CLOUDFLARE_ACCOUNT_ID="$acct" wrangler r2 bucket list 2>&1 | grep -E "^name:|ERROR" | head -20
done
```

Cache the resolved `CLOUDFLARE_ACCOUNT_ID` for the remaining commands.

## Single-File Upload

```bash
CLOUDFLARE_ACCOUNT_ID="$ACCOUNT_ID" \
  wrangler r2 object put "$BUCKET/${KEY_PREFIX}<name>.webp" \
    --file="/path/to/local.webp" \
    --content-type="image/webp" \
    --remote
```

Flags that matter:

- `--remote` — **required.** Without it, the write goes to the local simulator, not production.
- `--content-type` — set explicitly. Default guessing is unreliable and bad MIME breaks CDN / browsers.
- Target is a single positional `BUCKET/KEY` string (no space between bucket and key).

## Batch Upload (Directory)

```bash
cd "$SRC_DIR" && for f in *.webp; do
  echo "--- $f ---"
  CLOUDFLARE_ACCOUNT_ID="$ACCOUNT_ID" \
    wrangler r2 object put "$BUCKET/${KEY_PREFIX}${f}" \
      --file="$f" \
      --content-type="image/webp" \
      --remote 2>&1 | grep -E 'Creating|error|ERROR' | head -3
done
```

For mixed MIME types, resolve per-file:

```bash
mime_of() {
  case "$1" in
    *.webp) echo "image/webp" ;;
    *.png)  echo "image/png"  ;;
    *.jpg|*.jpeg) echo "image/jpeg" ;;
    *.svg)  echo "image/svg+xml" ;;
    *.json) echo "application/json" ;;
    *.html) echo "text/html; charset=utf-8" ;;
    *.txt|*.md) echo "text/plain; charset=utf-8" ;;
    *)      echo "application/octet-stream" ;;
  esac
}
```

## Verification

Never claim success based on wrangler output alone. Run an HTTP HEAD against the public domain for every uploaded key:

```bash
for f in "$SRC_DIR"/*.webp; do
  name=$(basename "$f")
  code=$(curl -sI -o /dev/null -w '%{http_code}' \
    "https://${PUBLIC_DOMAIN}/${KEY_PREFIX}${name}")
  printf "%-40s %s\n" "$name" "$code"
done
```

All lines must show `200`. A `404` means the key path or bucket binding is wrong; a `403` means the custom domain is not bound to this bucket.

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Omitting `--remote` | Upload "succeeds" but public URL 404s | Re-upload with `--remote` |
| Wrong account | `Please enable R2 through the Cloudflare Dashboard [code: 10042]` | Set `CLOUDFLARE_ACCOUNT_ID` to the account that actually owns the bucket |
| Missing `--content-type` | Browser downloads instead of rendering; image shows as broken in `<img>` | Always pass explicit MIME |
| Leading slash in key | Creates literal `/prefix/...` (double slash) paths | Ensure `KEY_PREFIX` does not start with `/` |
| Space in `BUCKET/KEY` | CLI parses as two args, errors | Pass as one single unbroken string |
| `npx wrangler` fails on pnpm-only setups | `ERROR Unknown option: 'yes'` | Use `pnpm dlx wrangler@latest` instead |
| Using local `wrangler dev` state | Writes invisible in production bucket | Always `--remote` for production writes |

## Rules

- Prefer OAuth session over API token when both are available.
- Always verify at least one URL per batch through the public domain before reporting completion.
- Do not delete previous-generation objects immediately after updating DB records; keep a rollback window.
- Never paste `R2_API_KEY` or `CLOUDFLARE_API_TOKEN` values into commit logs, commit messages, or PR descriptions.
- Do not mix `--remote` and non-remote calls in the same batch.

## Reporting Output

Preferred structured summary after a batch:

| file | size | key | status |
|---|---:|---|---|
| emo.webp | 18.3 KB | mx-space/topics/emo.webp | 200 |
| ... | ... | ... | ... |

Always list the fully-qualified public URLs at the end so the caller can paste them directly into downstream config or DB updates.
