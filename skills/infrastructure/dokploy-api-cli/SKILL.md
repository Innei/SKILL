---
name: dokploy-api-cli
description: Use when operating a Dokploy-managed deployment via REST API from the shell — creating/updating/deploying postgres/redis/compose/application services, switching an application's source between docker registry and git build, or scripting redeploys. Covers auth, the working endpoint catalog, and a critical gotcha about deployment status semantics.
---

# Dokploy API from the CLI

Operate Dokploy entirely from `curl` when the dashboard isn't practical (scripting, agents, headless ops).

## Auth

Generate an API token in dashboard → Profile → API. Pass on every request:

```
-H "x-api-key: $TOKEN"
```

Other auth headers (`Authorization: Bearer …`) return `401 Unauthorized`. There is no public OpenAPI/swagger endpoint — discover routes by probing.

## Endpoint Catalog (verified)

All endpoints are under `https://<dokploy-host>/api/<router>.<procedure>`. Reads are GET with query params, writes are POST with JSON body.

### Discovery

| Endpoint | Notes |
|---|---|
| `GET /api/project.all` | List projects |
| `GET /api/project.one?projectId=<id>` | Project + nested `environments[].{applications, mongo, postgres, redis, compose}` |
| `GET /api/postgres.one?postgresId=<id>` | Includes `appName` (internal hostname), `databasePassword`, `externalPort` |
| `GET /api/application.one?applicationId=<id>` | Includes `env` (multiline string), `sourceType`, `dockerImage`, `customGitUrl` |
| `GET /api/compose.one?composeId=<id>` | Includes `composeFile`, `sourceType` |
| `GET /api/deployment.all?applicationId=<id>` | Deploy history (most recent first); `composeId` works too |
| `GET /api/docker.getContainersByAppNameMatch?appName=<appName>` | Live container state — use to check actual run status |

### Postgres

| Endpoint | Required body |
|---|---|
| `POST /api/postgres.create` | `{name, appName, databaseName, databaseUser, databasePassword, dockerImage, environmentId}` |
| `POST /api/postgres.update` | `{postgresId, ...fields-to-change}` (e.g. `externalPort: 5433` or `null`) |
| `POST /api/postgres.deploy` | `{postgresId}` — required after `update` to apply port/image changes |

### Compose (one-shot or long-running stacks)

| Endpoint | Required body |
|---|---|
| `POST /api/compose.create` | `{name, appName, environmentId, composeType: "docker-compose"}` |
| `POST /api/compose.update` | `{composeId, name, description, env, composeFile, sourceType: "raw", composeType, autoDeploy, command}` — full replace, all fields required |
| `POST /api/compose.deploy` | `{composeId}` |
| `POST /api/compose.stop` | `{composeId}` |
| `POST /api/compose.delete` | `{composeId}` — also removes containers |

### Application (long-running services)

| Endpoint | Required body |
|---|---|
| `POST /api/application.saveDockerProvider` | `{applicationId, dockerImage, username, password, registryUrl}` (use empty strings for public images) |
| `POST /api/application.saveGitProvider` | `{applicationId, customGitUrl, customGitBranch, customGitBuildPath, watchPaths, customGitSSHKeyId}` |
| `POST /api/application.saveBuildType` | `{applicationId, buildType: "dockerfile"\|"nixpacks"\|"heroku"\|…, dockerfile, dockerContextPath, dockerBuildStage, herokuVersion, railpackVersion}` |
| `POST /api/application.saveEnvironment` | `{applicationId, env, buildArgs, buildSecrets, createEnvFile}` (`env` is the entire multiline `KEY=VALUE` string) |
| `POST /api/application.deploy` | `{applicationId}` |

## Critical Gotcha: deploy status ≠ container status

`deployment.all` returns `status: "done"` as soon as Dokploy's outer compose-up exits successfully. **The actual workload container may still be initializing, building, or even crashed afterwards.**

For a true pass/fail signal, poll `docker.getContainersByAppNameMatch` and watch the container's `state` (`running` → `exited`) and `status` text.

```bash
# Wrong: only watches deploy step
poll deployment.all → done = ❌ may still be building inside

# Right: watch the actual container
poll docker.getContainersByAppNameMatch → state=running → state=exited → check exit code
```

## Switching application source: docker registry ↔ git build

Useful when the registry image is outdated (e.g., you need today's master before tagging a release):

1. `application.saveGitProvider` — point at the repo + branch
2. `application.saveBuildType` — set `buildType: "dockerfile"`, `dockerfile: "<path>"` (e.g. `dockerfile`)
3. `application.deploy` — Dokploy clones, builds, swaps service

To switch back after the image is published:

1. `application.saveDockerProvider` — set `dockerImage: "<repo>:<tag>"`, `registryUrl: "index.docker.io"`
2. `application.deploy` — pulls and swaps

`sourceType` and related fields update automatically based on which `save*Provider` you called last.

## Probing for unknown endpoint shapes

POST with empty body to discover the required fields via the Zod error response:

```bash
curl -sS -X POST -H "x-api-key: $TOKEN" -H "content-type: application/json" \
  "https://<host>/api/postgres.create" -d '{}'
# → {"zodError":{"fieldErrors":{"name":[...],"databaseName":[...],...}}}
```

This is faster than guessing and works for every mutation route.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Trusting `deployment.all` status alone | Cross-check `docker.getContainersByAppNameMatch` |
| Calling `compose.deploy` with stale exited containers from a prior run | `ssh host docker rm -f <appName>-<service>-1` first, or `compose.stop` then `compose.deploy` |
| Hostname mismatch when service names contain hyphens | Use the auto-generated `appName` (e.g. `mx-space-pg-7pacdz`), not the user-friendly `name` |
| Updating compose YAML and expecting current container to reflect it | YAML applies on **next** deploy; running container keeps the YAML it started with |
| Updating `externalPort` without redeploy | Must call `postgres.deploy` (or equivalent) to apply port mapping |
