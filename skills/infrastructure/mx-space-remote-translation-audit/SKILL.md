---
name: mx-space-remote-translation-audit
description: Audit remote mx-space translation data through ssh to the swarm host, then docker exec into the Postgres container and run psql inside the container. Use for checking translation_entries coverage, ai_translations gaps, strict computeContentHash mismatches, and runtime freshness semantics in deployments where direct Postgres access is unreliable.
---

# mx-space Remote Translation Audit

Use this skill when validating remote `mx-space` translation state in `translation_entries` or `ai_translations` — coverage, freshness, hash drift, or route-level behavior.

> This deployment **migrated MongoDB → PostgreSQL**. Older notes referencing `mongosh`, `refType`/`sourceModified`, or other camelCase fields are stale.

For connection mechanics see the sibling skill **`mx-space-remote-db-access`**: `mx_core` database, `mx` role, `mx-space-pg-*` container, container env auto-sets credentials.

## Critical semantics (must not collapse)

```
strict hash mismatch  !=  runtime stale
```

| Status | Meaning |
|---|---|
| `missing` | no translation row exists for the requested language |
| `strict hash mismatch` | `translation.hash !== computeContentHash(current source)` |
| `runtime valid` | `source_modified_at >= article.modified_at`, or `created_at >= article.modified_at` when `source_modified_at` is absent, or hash matches |
| `runtime stale` | runtime freshness check explicitly concludes the translation is stale |
| `unknown` | snapshot lacks enough source fields to compute a hash |

Always state which conclusion the result represents — strict-hash or runtime — they can disagree, and a runtime-valid translation may legitimately ship with a drifted hash.

## Table of Contents

| Topic | Reference |
|---|---|
| `ai_translations` and `translation_entries` column reference (post-migration field names) | [`references/schema.md`](references/schema.md) |
| Audit workflow: scope → coverage → semantics → user-visible verification | [`references/audit-workflow.md`](references/audit-workflow.md) |
| Reproducing `computeContentHash` and the list-translation bug pattern | [`references/hash-semantics.md`](references/hash-semantics.md) |

## Preferred audit script

When the local `mx-core` repo is available, prefer the built-in script:

```bash
cd /Users/innei/git/innei-repo/mx-core
pnpm check:ai-translation-hash --help
```

The flag set may have changed post-migration (Postgres URI rather than Mongo URI). Read `--help` first; fall back to manual SQL if the script is absent or pre-migration.

Output sections: `missing`, `runtimeStale`, `strictHashMismatch`, `taskPayloads` (the regenerate set = `missing + runtimeStale`).

## API verification

When the user reports a page still shows untranslated content, hit the route inside the core container instead of inferring from DB state:

```bash
ssh -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" \
  "docker exec '$CORE_CONTAINER' curl -sS 'http://127.0.0.1:2333/api/v2/posts/<category>/<slug>?lang=en'"
```

If the database has the row but the route still returns source language, the bug is on the read path — see [`references/hash-semantics.md`](references/hash-semantics.md) for the known list-route failure pattern.
