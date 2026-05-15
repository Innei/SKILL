# Table Catalog

Source: `mx-core/packages/db-schema/src/schema/`. Grouped by domain. All `id` columns are `text` (snowflake / cuid) unless stated.

## Content (`content.ts`)

| Table | Purpose | Key columns / notes |
|---|---|---|
| `categories` | Post categories | `name` uniq, `slug` uniq, `type` int |
| `topics` | Note topic groupings | `name` uniq, `slug` uniq, `description`, `introduce`, `icon` |
| `posts` | Blog posts | `slug` uniq, `category_id` fk → `categories(id)` (RESTRICT), `tags text[]`, `content_format`, `summary`, `is_published`, `pin_at`, `pin_order`, `read_count`, `like_count`, `modified_at` |
| `post_related_posts` | Many-to-many post → post | `(post_id, related_post_id)` uniq, `position` |
| `notes` | Diary entries | `nid` integer uniq (public id), `slug` uniq when set, `topic_id` fk → `topics(id)` (SET NULL), `mood`, `weather`, `coordinates jsonb`, `location`, `password`, `public_at`, `bookmark`, `is_published`, `read_count`, `like_count`, `modified_at` |
| `pages` | Static pages | `slug` uniq, `subtitle`, `order`, `modified_at` |
| `recentlies` | Short status updates ("近况") | polymorphic `(ref_type, ref_id)`, `content`, `type`, `comments_index`, `up`/`down`, `enrichment_provider`/`enrichment_external_id` |
| `drafts` | Draft snapshots | polymorphic `(ref_type, ref_id)`, `version`, `published_version`, `history jsonb`, `type_specific_data jsonb` |
| `draft_histories` | Externalized draft history rows | `draft_id` fk (CASCADE), `(draft_id, version)` uniq, `is_full_snapshot`, `saved_at` |
| `comments` | Threaded comments | polymorphic `(ref_type, ref_id)`, `parent_comment_id` / `root_comment_id` self-fk (CASCADE), `reader_id` fk → `readers(id)` (SET NULL), `state`, `pin`, `is_whispers`, `is_deleted`, `reply_count`, `latest_reply_at`, `anchor jsonb` |

## AI (`ai.ts`)

| Table | Purpose | Key columns / notes |
|---|---|---|
| `ai_translations` | Article translations cache | uniq `(ref_id, ref_type, lang)`, `hash`, `source_lang`, `source_modified_at`, `ai_model`, `ai_provider`, `content_format`, `content`, `source_block_snapshots jsonb`, `source_meta_hashes jsonb` |
| `translation_entries` | Field-level translation dictionary | uniq `(key_path, lang, key_type, lookup_key)`; common `key_path` values: `category.name`, `topic.name`, `topic.introduce`, `note.mood`, `note.weather` |
| `ai_summaries` | AI summary cache | `hash`, `summary`, `ref_id`, `lang` |
| `ai_insights` | AI insights | uniq `(ref_id, lang)`, `hash`, `content`, `is_translation`, `source_insights_id` self-fk (SET NULL), `source_lang`, `model_info jsonb` |
| `ai_agent_conversations` | AI agent chat history per content ref | `(ref_id, ref_type)` indexed, `messages jsonb`, `model`, `provider_id`, `review_state`, `diff_state`, `message_count`, `updated_at` |
| `search_documents` | Denormalized search index | uniq `(ref_type, ref_id)`, `terms text[]`, `title_term_freq jsonb`, `body_term_freq jsonb`, `is_published`, `public_at`, `has_password`, `slug`, `nid` |

## Auth (`auth.ts`)

| Table | Purpose | Key columns / notes |
|---|---|---|
| `readers` | User / reader accounts | `email` uniq when set, `username` uniq when set, `handle`, `display_username`, `image`, `role` (`reader` default; owners have elevated role) |
| `owner_profiles` | Site owner profile | `reader_id` uniq fk (CASCADE), `mail`, `url`, `introduce`, `last_login_ip`, `last_login_time`, `social_ids jsonb` |
| `accounts` | better-auth provider links | uniq `(provider_id, provider_account_id)`, `user_id` fk → readers (CASCADE), `password`, `access_token`, `refresh_token`, `id_token`, `raw jsonb` |
| `sessions` | Active sessions | `token` uniq, `user_id` fk (CASCADE), `expires_at`, `ip_address`, `user_agent`, `provider` |
| `api_keys` | API keys with rate-limit | `key` uniq, `user_id` fk (CASCADE), `reference_id` fk, `prefix`, `enabled`, `rate_limit_*`, `request_count`, `remaining`, `refill_*`, `permissions jsonb`, `metadata jsonb` |
| `passkeys` | WebAuthn credentials | `credential_id` uniq, `user_id` fk (CASCADE), `public_key`, `counter`, `device_type`, `backed_up`, `transports`, `aaguid` |
| `verifications` | Email/phone verification codes | `identifier` indexed, `value`, `expires_at` |

## Ops (`ops.ts`)

| Table | Purpose | Key columns / notes |
|---|---|---|
| `options` | Global key/value site options | `name` uniq, `value jsonb` |
| `meta_presets` | Reusable meta-field schemas | `name` uniq, `content_type`, `description`, `fields jsonb` |
| `activities` | Generic activity log | `type int`, `payload jsonb`, indexed by `created_at` |
| `analyzes` | Request / visit analytics | `timestamp`, `ip`, `ua jsonb`, `country`, `path`, `referer` (multiple compound indexes on timestamp) |
| `links` | Friend links / blogroll | `name` uniq, `url` uniq, `type`, `state`, `email`, `avatar`, `description` |
| `projects` | Projects showcase | `name` uniq, `preview_url`, `doc_url`, `project_url`, `images text[]`, `description`, `avatar`, `text` |
| `says` | Short quotes / sayings | `text` notnull, `source`, `author` |
| `snippets` | Serverless function definitions | `(name, reference)` indexed; `custom_path` uniq when set; `type`, `private`, `raw`, `metatype`, `schema`, `method`, `secret`, `enable`, `built_in`, `compiled_code` |
| `subscribes` | Email subscriptions | `email` uniq, `cancel_token` uniq, `subscribe int`, `verified` |
| `file_references` | Uploaded file references | `file_url` indexed, `(ref_id, ref_type)` indexed, `status` (multiple status indexes), `s3_object_key`, `mime_type`, `byte_size bigint`, `reader_id` fk (SET NULL), `detached_at` |
| `poll_votes` | Poll votes | `(poll_id, voter_fingerprint)` uniq |
| `poll_vote_options` | Vote → option many-to-many | `(vote_id, option_id)` uniq, `vote_id` fk → `poll_votes` (CASCADE) |
| `slug_trackers` | Historical slug → entity tracking (redirects) | `(type, target_id)` indexed, `(slug, type)` indexed |
| `serverless_storages` | KV store for serverless functions | uniq `(namespace, key)`, `value jsonb` |
| `serverless_logs` | Execution logs for serverless | `function_id`, `reference + name`, `status`, `execution_time`, `logs jsonb`, `error jsonb` |
| `webhooks` | Outbound webhook configs | `payload_url`, `events text[]`, `enabled`, `secret`, `scope` |
| `webhook_events` | Webhook delivery records | `hook_id` fk → `webhooks` (CASCADE), `event`, `payload jsonb`, `response jsonb`, `success`, `status`, `timestamp` |

## Enrichment (`enrichment.ts`)

| Table | Purpose | Key columns / notes |
|---|---|---|
| `enrichment_cache` | Third-party enrichment cache (Douban / Spotify / etc.) | uniq `(provider, external_id, locale)`, `url`, `normalized jsonb`, `raw jsonb`, `fetched_at`, `expires_at`, `failure_count`, `last_error` |

## Migration (`migration.ts`)

> These are migration-bookkeeping tables. Business runtime code must not query them.

| Table | Purpose |
|---|---|
| `_app_migrations` | Runtime app-data migration ledger (idempotent backfills); `id` pk, `applied_at`, `duration_ms` |
| `schema_migrations` | One-time data-migration ledger (Mongo → PG importer); `name` pk, `applied_at` |
| `data_migration_runs` | Audit log of one-time data-migration runs; `name`, `started_at`, `finished_at`, `status`, `error` |
| `mongo_id_map` | Historical Mongo `ObjectId` → snowflake mapping; uniq `(collection, mongo_id)` and `snowflake_id` uniq. Read-only audit table — do not query at runtime |
| `auth_id_map` | Historical auth-id mapping (Mongo → PG); uniq `(collection, mongo_id)` and `(collection, pg_id)` |

## Quick lookups by use case

| Want to … | Look at |
|---|---|
| List all blog posts of a category | `posts` join `categories` |
| List all notes of a topic | `notes` join `topics` on `notes.topic_id = topics.id` |
| Find unassigned notes | `notes WHERE topic_id IS NULL` |
| Audit translation coverage for posts | `posts` left join `ai_translations` on `(ref_id, ref_type='post', lang)` |
| Inspect site options | `options` (json `value` per `name`) |
| Threaded comment for a content | `comments WHERE ref_type=? AND ref_id=? ORDER BY pin DESC, created_at` |
| Drafts attached to an article | `drafts WHERE ref_type=? AND ref_id=?` |
| Identify a user by email | `readers WHERE email=?` |
| Friend-link list | `links` |
| Search index entries | `search_documents WHERE ref_type=?` |
| Webhook delivery failures | `webhook_events WHERE success = false` |
| Visitor analytics for a path | `analyzes WHERE path=?` (use timestamp index) |
