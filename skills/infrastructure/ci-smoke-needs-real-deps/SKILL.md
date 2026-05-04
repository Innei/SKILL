---
name: ci-smoke-needs-real-deps
description: Use when a CI release/build pipeline runs a smoke test that boots the project's bundled binary against an external dependency stack (PostgreSQL, MySQL, Redis, MongoDB, S3, etc.) and the test fails with connection refused, missing-required-env, or migration errors. The fix is to declare the dep as a CI service container AND inject the matching env vars on the smoke step. Common after a stack migration leaves the release workflow out of sync with the new ci.yml/code reality.
---

# CI Smoke Tests Need Real Dependencies

A smoke test that just runs `node out/main.mjs && curl localhost:PORT/health` is not a smoke test if the binary can't reach a real database. When stacks change (Mongo → Postgres, sqlite → mysql, in-memory → Redis, …), the release pipeline often gets forgotten while `ci.yml` is updated. Symptom: tag push triggers release workflow, build job fails with `connection refused` or missing-env throws.

## When to use

- Release workflow fails at "smoke test" / "test bundle" / "boot test" step
- Error says `Connection refused`, `MONGO_URL is required`, `SNOWFLAKE_WORKER_ID is required`, `cannot connect to ...`, or similar after a recent stack migration
- The same project's `ci.yml` (PR checks) passes but `release.yml` fails — they've diverged
- Adding a new external dependency that the smoke test needs

## When NOT to use

- Smoke test is genuinely failing (real bug in the code) — fix the code, don't paper over it
- The dep would slow CI to the point of being useless — consider whether the smoke is the wrong level of test (use unit tests instead)

## Diagnostic checklist

When `release.yml` smoke fails post-migration, check what `ci.yml` does for its smoke and align:

1. What `services:` does ci.yml declare? (postgres? mysql? redis?)
2. What `env:` does ci.yml inject on the smoke step?
3. Is there a migration runner or `MIGRATIONS_DIR` env that ci.yml passes but release.yml doesn't?
4. Does the bundled binary auto-run migrations on boot, or does it need an explicit migrate step first?

If (1) or (2) differ from release.yml, that's the bug.

## The Pattern

GitHub Actions example (mirror your `ci.yml` smoke job):

```yaml
build:
  runs-on: ubuntu-latest
  services:
    postgres:                       # match the stack the binary actually expects
      image: postgres:16-alpine     # pin major; -alpine is fine for tests
      env:
        POSTGRES_USER: app
        POSTGRES_PASSWORD: app
        POSTGRES_DB: app
      ports:
        - 5432:5432
      options: >-
        --health-cmd "pg_isready -U app -d app"
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
    redis:
      image: redis:7-alpine
      ports:
        - 6379:6379
  steps:
    - uses: actions/checkout@v6
    - uses: ./.github/actions/setup-node
      with: { node-version: '22.x' }
    - run: pnpm bundle
    - name: Smoke test bundle
      env:
        # Every env var the binary requires at boot.
        # Match exactly what ci.yml uses — do not invent new values.
        SNOWFLAKE_WORKER_ID: 1
        PG_HOST: 127.0.0.1
        PG_PORT: 5432
        PG_USER: app
        PG_PASSWORD: app
        PG_DATABASE: app
        REDIS_HOST: 127.0.0.1
        REDIS_PORT: 6379
        JWT_SECRET: smoke-test-only-not-a-real-secret
        # If the binary expects migrations on disk, point at the source tree
        MIGRATIONS_DIR: ${{ github.workspace }}/path/to/migrations
      run: bash scripts/workflow/test-server.sh
```

## Why this matters more than it sounds

A release workflow that **builds + ships** without a real-deps smoke test will publish a Docker image that crashes on first boot in production. The "successful" tag push gives false confidence. The fix is cheap (one health-checked service container + a handful of env vars). The cost of skipping is shipping a broken image.

## Aligning two workflows

Use a quick diff to keep `ci.yml` and `release.yml` in sync on the smoke section:

```bash
diff <(yq '.jobs.test.services' ci.yml) \
     <(yq '.jobs.build.services' release.yml)
diff <(yq '.jobs.test.steps[] | select(.name == "Test Bundle Server")' ci.yml) \
     <(yq '.jobs.build.steps[] | select(.name == "Test Bundle Server")' release.yml)
```

When they drift, fix release.yml — ci.yml runs more often and is usually the more current of the two.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Adding env vars but forgetting the service container | Service container too. The env points at *something*. |
| Using `localhost` from inside the runner with non-default network | `127.0.0.1` is safer; both work on `ubuntu-latest`. |
| Skipping `--health-cmd` on the service | Smoke step starts before DB is ready → flaky CRINGE. Always health-check. |
| Pointing `MIGRATIONS_DIR` at a relative path | Use `${{ github.workspace }}/...` for an absolute path; cwd in CI isn't always repo root. |
| Inventing values that don't match `ci.yml` | Pick one set of test creds and use them everywhere. Divergence creates more confusion than it solves. |
| Setting `NODE_ENV=production` to "match prod" | Your prod likely has `isDev=false` checks that demand real secrets. Either set the secrets or omit `NODE_ENV` so dev fallbacks engage. |
