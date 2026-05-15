# Translation Tables (post-migration)

Source: `mx-core/packages/db-schema/src/schema/ai.ts`. All ids are `text`. Use these column names verbatim — old Mongo camelCase fields no longer exist.

## `ai_translations`

Article-level translation cache. One row per `(ref_id, ref_type, lang)`.

| Column | Type | Notes |
|---|---|---|
| `id` | text | pk |
| `hash` | text | content hash at translation time; compared against current `computeContentHash` |
| `ref_id` | text | source content id |
| `ref_type` | text | `post`, `note`, `page` |
| `lang` | text | target language |
| `source_lang` | text | language of the source content at translation time |
| `title` | text | translated title |
| `text` | text | translated markdown |
| `subtitle` | text? | translated subtitle |
| `summary` | text? | translated summary |
| `tags` | text[] | translated tags |
| `source_modified_at` | timestamptz? | source `modified_at` snapshot — drives runtime freshness short-circuit |
| `ai_model` / `ai_provider` | text? | provenance |
| `content_format` | text? | `markdown` or `lexical` |
| `content` | text? | translated lexical JSON when `content_format = 'lexical'` |
| `source_block_snapshots` | jsonb? | per-block source snapshots for incremental retranslation |
| `source_meta_hashes` | jsonb? | per-field source hashes |

Unique: `(ref_id, ref_type, lang)`. Index on `ref_id`.

## `translation_entries`

Field-level dictionary translations (entity attributes, not articles).

| Column | Type | Notes |
|---|---|---|
| `id` | text | pk |
| `key_path` | text | dotted path of the translated field |
| `lang` | text | target language |
| `key_type` | text | classifier, e.g. `field`, `enum` |
| `lookup_key` | text | id or value used to look up the source |
| `source_text` | text | source value |
| `translated_text` | text | translated value |
| `source_updated_at` | timestamptz? | source freshness marker |

Unique: `(key_path, lang, key_type, lookup_key)`. Indexed on `(key_path, lang)` and `lookup_key`.

Common `key_path` values seen in this deployment:

- `category.name`
- `topic.name`
- `topic.introduce`
- `note.mood`
- `note.weather`
