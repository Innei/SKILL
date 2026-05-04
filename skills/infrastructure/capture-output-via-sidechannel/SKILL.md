---
name: capture-output-via-sidechannel
description: Use when a runner, CI step, container, or orchestrator executes a task whose stdout/stderr you cannot retrieve afterwards — no log API, no shell access, output stream not captured, or logs evicted before you can read them. The pattern: have the task itself write its captured output into a data store you CAN read (SQL row, Redis key, mounted file, public webhook).
---

# Sidechannel Output Capture

When the orchestrator's log retrieval is missing, broken, or asynchronous, don't fight it — make the task persist its own output to somewhere you can query.

## When to use

- Running a one-shot container in a system with no log-fetch API (managed PaaS, certain CI systems)
- Job runner that streams logs to a UI but offers no programmatic export
- Long-running batch job where logs roll over before you can grep them
- Headless agent contexts where shell access to the runtime host is unavailable

## When NOT to use

- You can just run `docker logs <id>` or `kubectl logs <pod>` — do that
- The runtime emits a structured exit signal you actually trust (HTTP webhook, exit code only)
- Output contains secrets you must NOT persist beyond the run

## The Pattern

1. Capture stdout+stderr inside the runner with `tee`, preserving the real exit code.
2. Encode the captured file (base64) to dodge SQL-quoting hell.
3. Insert as a single row/key in a data store you already have credentials for.
4. Exit with the original exit code (preserves up-stream pass/fail signaling).
5. Read from the data store afterwards.

### Reference: bash + PostgreSQL

```bash
#!/bin/bash
set -e

# 1. Run the actual work, capture, preserve exit code
set +e
your_real_command 2>&1 | tee /tmp/run.log
EXITCODE=${PIPESTATUS[0]}
set -e

# 2. Ensure target table exists (idempotent)
export PGPASSWORD="$DB_PASSWORD"
psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS _run_log (
  id SERIAL PRIMARY KEY,
  job TEXT,
  exit_code INT,
  output TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
SQL

# 3. Encode + insert (base64 dodges quoting)
B64=$(base64 -w0 /tmp/run.log)
psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 \
  -c "INSERT INTO _run_log(job, exit_code, output)
      VALUES ('$JOB_NAME', $EXITCODE,
              convert_from(decode('$B64', 'base64'), 'UTF8'))"

# 4. Exit with the real code
exit $EXITCODE
```

Read it back later with `SELECT output FROM _run_log ORDER BY id DESC LIMIT 1`.

### Reference: Redis variant (when you don't have SQL)

```bash
B64=$(base64 -w0 /tmp/run.log)
redis-cli -h "$REDIS_HOST" -a "$REDIS_PASSWORD" \
  SET "run-log:$JOB_NAME:$(date +%s)" "exit=$EXITCODE;$B64" EX 86400
```

### Reference: Public webhook (when you have neither)

```bash
curl -sS -X POST "https://ntfy.sh/<your-unique-topic>" \
  -H "Title: $JOB_NAME exit=$EXITCODE" \
  --data-binary @/tmp/run.log
```

Then `curl "https://ntfy.sh/<topic>/json?poll=1"` to retrieve.
**Warning:** ntfy/webhook.site are public — never send secrets, tokens, or PII.

## Why base64 instead of dollar-quoting

```sql
-- Naive: breaks if output contains '$$', single quotes, backticks, etc.
INSERT INTO log VALUES ($$REPORT_PLACEHOLDER$$);
```

Output from real programs contains arbitrary bytes — terminal escape codes, JSON with quotes, stack traces with `$`. Base64 makes the payload opaque to the SQL parser. The `convert_from(decode(..., 'base64'), 'UTF8')` decodes back to text on the server side.

## Critical: preserve the exit code

The whole point of running a task is the pass/fail signal. Naive piping breaks it:

```bash
# WRONG: exit code is from `tee`, always 0
your_command 2>&1 | tee log.txt
# upstream sees success even when your_command failed
```

```bash
# RIGHT: capture exit before tee mangles it
set +e
your_command 2>&1 | tee log.txt
EXITCODE=${PIPESTATUS[0]}
set -e
```

Then `exit $EXITCODE` at the end so the orchestrator can still see failure.

## Common Mistakes

| Mistake | Fix |
|---|---|
| `cmd | tee log` and then `exit $?` | `$?` is `tee`'s exit (0). Use `${PIPESTATUS[0]}`. |
| Embedding `cat /tmp/log` directly into SQL via heredoc | Output containing `$$` or `'` corrupts the statement. Use base64. |
| Forgetting `convert_from(..., 'UTF8')` on read side | Get bytea instead of text; decoding becomes the reader's problem. |
| Running on a PaaS without first verifying the data store is reachable from the runner's network | Sidechannel write fails silently, exit code preserved but report unrecoverable. Smoke-test connectivity first. |
| Posting full logs to a public webhook | Logs often contain auth tokens, hostnames, IDs. Strip or skip the public path. |
| Using `set -e` around the work | Aborts before you capture exit code. Use `set +e` for the work block, restore `set -e` after. |
