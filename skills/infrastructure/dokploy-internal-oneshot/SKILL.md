---
name: dokploy-internal-oneshot
description: Use when running an ephemeral one-shot task (data migration, batch job, schema setup, ad-hoc psql script) that must reach other services in a Dokploy project's internal network without exposing those services to the public internet. The task should join the project's docker overlay network, run to completion, and exit. Pairs with dokploy-api-cli.
---

# Dokploy One-Shot Internal Task

When you need to run something *inside* a Dokploy project's network — to reach `postgres`, `mongo`, `redis`, etc. by their internal hostnames without temporarily exposing host ports — create a short-lived `compose` service with `sourceType: "raw"` and an inline YAML.

## When to use

- Running a one-time data migration script that needs the project's database
- Triggering a batch job (cleanup, recompute, reindex) inside the same network
- Quick `psql` / `redis-cli` ad-hoc scripts when a log API isn't needed
- Anything where exposing `externalPort` on a database is undesirable

## When NOT to use

- Long-running services (use a normal `application` or `compose` with persistent intent)
- Tasks that need only the public-facing API (just `curl` it)
- Tasks where you have SSH on the host and prefer `docker run --network <net>` directly

## Compose template

```yaml
services:
  runner:
    image: <base-image-with-the-runtime-you-need>   # e.g. node:22-bookworm, python:3.12-slim
    working_dir: /app
    restart: "no"          # one-shot — must not auto-restart
    environment:
      # Internal service hostnames are the auto-generated `appName` of each service.
      # Discover via `GET /api/<svc>.one`.
      DB_URL: "postgres://user:pwd@<pg-appName>:5432/dbname"
      MODE: "dry-run"
    command:
      - bash
      - -c
      - |
        set -e
        # apt-get -q install whatever you need
        # git clone --depth 1 -b master https://github.com/<owner>/<repo>.git /app
        # corepack enable && pnpm install --frozen-lockfile
        echo "==== task start (mode=$$MODE) ===="
        # actual work goes here, e.g.
        #   pnpm exec tsx scripts/migrate.ts --mode "$$MODE"
        echo "==== task end ===="
networks:
  default:
    name: dokploy-network    # Dokploy's default project overlay
    external: true
```

## Critical: escape `$` as `$$`

Docker Compose performs variable interpolation on the `command:` block before bash sees it. Any `$VAR` will be substituted from the **compose process's** env, not the container's, and `${ARRAY[idx]}` produces the dreaded:

```
invalid interpolation format for services.<svc>.command.[].
You may need to escape any $ with another $.
```

Rule: **every `$` that bash should see must be written `$$` in the YAML.** Validate locally with `docker compose -f compose.yml config` before uploading.

| YAML you write | What bash sees | Use case |
|---|---|---|
| `$$VAR` | `$VAR` | env var |
| `$$(cmd)` | `$(cmd)` | command substitution |
| `$${arr[0]}` | `${arr[0]}` | array index, `PIPESTATUS` |

## Driving it

Use the dokploy-api-cli skill for `compose.create` → `compose.update` (with the YAML) → `compose.deploy`. Then poll the container, not the deployment status:

```bash
curl -sS -H "x-api-key: $TOKEN" \
  "https://$HOST/api/docker.getContainersByAppNameMatch?appName=$APP_NAME" \
  | jq '.[0] | "\(.state)|\(.status)"'
# wait for state to flip from running → exited
```

When the container exits, the exit code is in the `status` text (`Exited (0)` / `Exited (1) …`).

## Reading output

The compose YAML you uploaded is the source of truth for the run. There is **no public log API** on Dokploy. Three options to retrieve output:

1. **Sidechannel-write into a database the runner can reach.** See the `capture-output-via-sidechannel` skill. This is usually the cleanest for migrations because you'll have a database open anyway.
2. **SSH to the swarm host** and `docker logs <container>` (works for the agent if SSH is available; not for users without host access).
3. **Have the runner POST a summary to a public webhook** (webhook.site, ntfy.sh, your own endpoint). Useful when neither DB nor SSH is available.

## Cleanup

After the task finishes:

1. `compose.delete` removes the service AND its containers (no leftover exited container).
2. If you want to re-run with updated YAML in the same `composeId`, first `ssh host docker rm -f <appName>-<service>-1` because Dokploy's internal `docker compose up` won't recreate an existing exited container by default.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Writing `$VAR` in `command:` | Use `$$VAR`. Validate with `docker compose config`. |
| Using `${PIPESTATUS[0]}` directly | Write `$${PIPESTATUS[0]}`. |
| Leaving exited container in place between runs | `docker rm -f <name>` (via SSH) or `compose.delete` + `compose.create` again. |
| Counting on `restart: "no"` to mean "no retry on Dokploy redeploy" | Dokploy will still re-create the container on each `compose.deploy`. The flag only stops Docker itself from restarting after exit. |
| Hostname uses friendly name | Use the auto-generated `appName` (e.g. `mx-space-pg-7pacdz`); friendly `name` doesn't resolve. |
