---
name: mx-space-remote-translation-audit
description: Audit remote mx-space translation data through ssh to the swarm host, then docker exec into the Mongo container and run mongosh inside the container. Use for checking translation_entries coverage, ai_translations gaps, strict computeContentHash mismatches, and runtime freshness semantics in deployments where direct Mongo access is unreliable.
---

# mx-space Remote Translation Audit

Use this skill when the task requires validating the remote `mx-space` translation state for `translation_entries` or `ai_translations`, especially when the user asks which records are missing, stale, or not being returned by the API.

## Scope

- Target topology: `local -> ssh -> swarm host -> docker exec -> mongosh`
- Primary use cases:
  - inspect `translation_entries` completeness
  - inspect `ai_translations` language coverage
  - verify whether `mx-core` currently stores a translation for a specific article
  - distinguish strict hash mismatch from runtime freshness
  - reproduce API-facing translation behavior for a specific route such as article detail or timeline
- Do not assume that a host-level Mongo port is reachable or trustworthy.

## Preconditions

Collect or derive the following values before running queries.

| Variable | Meaning |
|---|---|
| `SSH_USER` | remote login user, typically `root` |
| `SSH_HOST` | remote host address |
| `SSH_PORT` | remote SSH port |
| `MONGO_CONTAINER` | running Mongo container name |
| `CORE_CONTAINER` | running core container name when API verification is needed |
| `MONGO_USER` | Mongo username |
| `MONGO_PASSWORD` | Mongo password |
| `MONGO_DB` | target database, typically `mx-space` |

## Access Topology

```text
[Local shell]
      |
      v
ssh -p $SSH_PORT $SSH_USER@$SSH_HOST
      |
      +-> docker exec $MONGO_CONTAINER mongosh
      |
      +-> docker exec $CORE_CONTAINER curl/node
```

## Baseline Verification

Run these checks in order.

1. Verify SSH connectivity.
2. Verify the Mongo container name.
3. Verify the core container name if API behavior must be reproduced.
4. Confirm Mongo access with `db.adminCommand({ ping: 1 })`.

Minimal examples:

```bash
ssh -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" "docker ps --format '{{.Names}}'"
```

```bash
ssh -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" \
  "docker exec '$MONGO_CONTAINER' mongosh 'mongodb://$MONGO_USER:$MONGO_PASSWORD@127.0.0.1:27017/$MONGO_DB?authSource=admin' --quiet --eval 'db.adminCommand({ ping: 1 })'"
```

## Preferred Audit Script

When the local `mx-core` repository is available, prefer the built-in audit script over ad hoc shell code.

| Path | Purpose |
|---|---|
| `/Users/innei/git/innei-repo/mx-core/apps/core/scripts/check-ai-translation-hash.mjs` | Batch audit `ai_translations` against current `mx-core` hash and runtime freshness semantics |

Use the package entrypoint:

```bash
cd /Users/innei/git/innei-repo/mx-core

pnpm check:ai-translation-hash \
  --uri '<mongo-uri>' \
  --langs auto \
  --visibility all
```

For machine-readable output:

```bash
cd /Users/innei/git/innei-repo/mx-core

pnpm check:ai-translation-hash \
  --uri '<mongo-uri>' \
  --langs auto \
  --visibility all \
  --json
```

## Script Output Semantics

Do not misread the script output.

| Output section | Meaning |
|---|---|
| `missing` | language rows that do not exist in `ai_translations` |
| `runtimeStale` | rows that `mx-core` would currently treat as stale |
| `strictHashMismatch` | rows whose stored hash differs from a fresh recomputation, even if runtime still treats them as valid |
| `taskPayloads` | actionable objects to regenerate, derived from `missing + runtimeStale` only |

Interpret the summary with this rule:

```text
strictHashMismatch
    !=
runtimeStale
```

The script is intended to reflect both:

- operational truth for remediation
- strict hash drift for diagnosis

## Query Strategy

Use `--eval` only for simple reads that do not contain Mongo operators beginning with `$`.

Use stdin scripts or `--file` whenever the query includes aggregation or multi-step JavaScript.

Reason:

- remote shell quoting can corrupt `$group`, `$match`, `$project`, or template strings
- `mongosh` interactive mode can pollute stdout unless `--quiet --norc --file` is used

## Audit Workflow

```text
[1] Identify target scope
      -> translation_entries
      -> ai_translations
      -> specific API route

[2] Confirm raw storage
      -> collection counts
      -> sample documents
      -> language distribution

[3] Reproduce mx-core semantics
      -> computeContentHash
      -> sourceLang selection
      -> sourceModified / created freshness rules

[4] Classify findings
      -> missing
      -> strict hash mismatch
      -> runtime-valid
      -> runtime-stale

[5] Verify user-facing behavior
      -> direct API call inside core container
      -> compare route output with database state
```

## translation_entries Checklist

Use this sequence when auditing field-level dictionary translations.

| Check | Goal |
|---|---|
| record count | verify the collection is populated |
| `translatedText` null or empty | detect obvious untranslated rows |
| group by `keyPath + lookupKey` | check entity coverage |
| distinct `lang` per group | detect missing locale coverage |
| reverse-check source collections | detect source entities that never generated entries |

Typical key paths observed in this deployment:

- `category.name`
- `note.mood`
- `note.weather`
- `topic.name`
- `topic.introduce`

## ai_translations Checklist

Use this sequence when auditing article translations.

| Check | Goal |
|---|---|
| count by `refType` and `lang` | establish overall coverage |
| compare source object count vs translation count | detect missing article-language rows |
| inspect `sourceModified` and `created` | reproduce runtime freshness |
| compare stored `hash` vs current hash | detect strict hash mismatch |
| inspect route output in core container | confirm user-visible behavior |

## Critical Semantics

Do not collapse these into one status.

| Status | Meaning |
|---|---|
| `missing` | no translation document exists for the requested language |
| `strict hash mismatch` | `translation.hash !== computeContentHash(current source)` |
| `runtime valid` | `sourceModified >= article.modified`, or `created >= article.modified` when `sourceModified` is absent, or hash matches |
| `runtime stale` | runtime freshness check explicitly concludes the translation is stale |
| `unknown` | the current snapshot lacks enough source fields for hash comparison |

## Important Interpretation Rule

```text
strict hash mismatch
    !=
runtime stale
```

If the runtime freshness rule is timestamp-short-circuited, a translation can be user-visible and valid even when a strict hash recomputation does not match.

## Reproducing mx-core Hash Logic

When the user asks whether hashes are correct, reproduce the current `mx-core` behavior:

1. `sourceLang` is chosen from article metadata when available; otherwise use stored `translation.sourceLang`.
2. For markdown articles, hash `text`.
3. For lexical articles, canonicalize `content`:
   - recursively sort object keys
   - remove `blockId` from the `$` state object
4. Hash the JSON object containing:
   - `title`
   - `subtitle`
   - canonicalized content or markdown text
   - `summary`
   - `tags`
   - `sourceLang`

## API Verification Pattern

When the user reports that a page still shows untranslated content, verify the route directly inside the core container instead of inferring from database state.

```text
[Database says translation exists]
      |
      v
[Core route with lang=en still returns original text?]
      |
      +-- yes -> inspect controller/list translation path
      |
      +-- no  -> issue is likely in frontend request language propagation
```

Example approach:

```bash
ssh -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" \
  "docker exec '$CORE_CONTAINER' curl -sS 'http://127.0.0.1:2333/api/v2/posts/<category>/<slug>?lang=en'"
```

## Known Failure Pattern

Watch for this list-translation bug class:

- detail route uses a full article snapshot and returns translation correctly
- list route passes only `id/title/created/modified`
- runtime freshness becomes `unknown`
- batch path drops the translation and falls back to source language

When this pattern appears, inspect the batch validation logic before blaming the database.

## Output Requirements

Prefer compact tables.

### Use tables for:

- missing article list
- stale vs valid counts
- `refType` breakdown
- route behavior summary

### Use ASCII flow for:

- access topology
- freshness decision path
- database-to-API investigation sequence

## Operational Notes

- Prefer container-local Mongo access over SSH port forwarding in this deployment pattern.
- Keep credentials out of repository files.
- When exporting large result sets, write them to a temporary JSON file and summarize counts in the response.
- Always state whether a result is a strict hash conclusion or a runtime freshness conclusion.
