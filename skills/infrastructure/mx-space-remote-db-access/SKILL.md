---
name: mx-space-remote-db-access
description: Access the remote mx-space PostgreSQL through ssh to the swarm host, then docker exec into the Postgres container and run psql inside the container. Use for inspecting tables, sampling rows, validating topic assignments, and performing guarded updates in the specific mx-space deployment pattern where direct host-level Postgres access is unreliable.
---

# mx-space Remote DB Access

Use this skill when inspecting or updating the remote `mx-space` PostgreSQL via the swarm host.

> This deployment **migrated MongoDB → PostgreSQL**. Older notes referencing `mongosh`, collections, or camelCase fields are stale.

## Deployment-specific facts

| Fact | Value |
|---|---|
| Database | `mx_core` |
| Role | `mx` — `postgres` role does **not** exist |
| Container name pattern | `mx-space-pg-*` (dynamic swarm task suffix; resolve via `grep '^mx-space-pg-'`) |
| In-container env | `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` already set, so `psql -U mx -d mx_core` works without `PGPASSWORD` |
| Host port forwarding | unreliable in this deployment — stay inside `docker exec` |

## Quick start

```bash
PG_CONTAINER=$(ssh -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" \
  "docker ps --format '{{.Names}}' | grep '^mx-space-pg-' | head -1")

ssh -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" \
  "docker exec '$PG_CONTAINER' psql -U mx -d mx_core -c 'SELECT 1;'"
```

For multi-statement queries pipe through `docker exec -i ... psql <<'EOF' ... EOF`.

## Table of Contents

| Topic | Reference |
|---|---|
| Full table catalog grouped by domain (content / ai / auth / ops / migration) | [`references/tables.md`](references/tables.md) |
| Topic / notes relation, guarded `UPDATE` template | [`references/topic-workflow.md`](references/topic-workflow.md) |

## Schema conventions worth remembering

- All id-shaped columns (`id`, `topic_id`, `ref_id`, `category_id`) are `text` (snowflake / cuid) — quote them.
- Column names are snake_case. Don't paste old camelCase Mongo fields into SQL.
- Polymorphic refs use the `(ref_type, ref_id)` pair (see `comments`, `recentlies`, `drafts`, `ai_translations`, `search_documents`).

## Update rules

Writes only after explicit user approval. Filter every write with both a null guard (e.g. `topic_id IS NULL`) **and** an explicit id list, wrap in a transaction, and verify immediately after.
