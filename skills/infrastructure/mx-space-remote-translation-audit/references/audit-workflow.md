# Audit Workflow

```text
[1] Identify scope
      -> translation_entries  |  ai_translations  |  specific API route

[2] Confirm raw storage
      -> row counts, language distribution, sample rows

[3] Reproduce mx-core semantics
      -> computeContentHash (see hash-semantics.md)
      -> source_lang selection
      -> source_modified_at / created_at freshness rules

[4] Classify findings
      -> missing | strict hash mismatch | runtime valid | runtime stale | unknown

[5] Verify user-facing behavior
      -> direct API call inside core container
      -> compare route output against DB state
```

## `translation_entries` checklist

| Check | Goal |
|---|---|
| `COUNT(*)` per `(key_path, lang)` | populated and balanced across locales |
| `translated_text IS NULL OR = ''` | obvious untranslated rows |
| `array_agg(lang) GROUP BY (key_path, lookup_key)` | per-entity locale coverage |
| reverse-check source tables (`topics`, `categories`, `notes`) | source rows that never produced an entry |

```sql
SELECT key_path, lookup_key, array_agg(lang ORDER BY lang) AS langs
FROM translation_entries
GROUP BY key_path, lookup_key
ORDER BY key_path, lookup_key;
```

## `ai_translations` checklist

| Check | Goal |
|---|---|
| `GROUP BY ref_type, lang` | overall coverage |
| compare source row count vs translation count per `ref_type` | missing article-language rows |
| inspect `source_modified_at` and `created_at` | reproduce runtime freshness |
| compare stored `hash` vs recomputed hash | strict drift |
| route output in core container | user-visible behavior |

Missing-language detection (posts → en):

```sql
SELECT p.id, p.title
FROM posts p
LEFT JOIN ai_translations t
  ON t.ref_id = p.id AND t.ref_type = 'post' AND t.lang = 'en'
WHERE t.id IS NULL
ORDER BY p.created_at DESC
LIMIT 50;
```

Coverage breakdown:

```sql
SELECT ref_type, lang, COUNT(*) AS n
FROM ai_translations
GROUP BY ref_type, lang
ORDER BY ref_type, lang;
```
