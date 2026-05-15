# Hash Semantics & Known Failure Pattern

## Reproducing `computeContentHash` (mx-core)

1. **`source_lang`** — taken from article metadata when present; otherwise from the stored `ai_translations.source_lang`.
2. **Markdown articles** — hash the `text` field.
3. **Lexical articles** — canonicalize `content` first:
   - recursively sort object keys
   - remove `blockId` from the `$` state object
4. Hash a JSON object containing:
   - `title`
   - `subtitle`
   - canonicalized content / markdown text
   - `summary`
   - `tags`
   - `source_lang`

A drifted hash on a runtime-valid row usually means a non-content field changed (e.g. `tags` reorder) without bumping `modified_at`. That is real strict drift but not user-facing staleness.

## Runtime freshness short-circuit

```text
if (translation.source_modified_at >= article.modified_at) return valid;
if (!translation.source_modified_at &&
    translation.created_at        >= article.modified_at) return valid;
if (translation.hash === computeContentHash(article))     return valid;
return stale;
```

Implication: a translation can be runtime-valid even when its hash no longer matches.

## Known list-route failure

```text
detail route       -> full article snapshot      -> translation returned correctly
list route         -> only id/title/created/modified passed
                   -> freshness becomes 'unknown'
                   -> batch path drops the translation
                   -> response falls back to source language
```

When a user reports "list shows untranslated, detail shows translated," inspect the batch validation path before blaming the database. The DB is correct in this scenario.
