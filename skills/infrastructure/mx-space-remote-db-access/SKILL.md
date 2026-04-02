---
name: mx-space-remote-db-access
description: Access the remote mx-space MongoDB through ssh to the swarm host, then docker exec into the Mongo container and run mongosh inside the container. Use for inspecting collections, sampling documents, validating topic assignments, and performing guarded updates in the specific mx-space deployment pattern where direct host-level port forwarding is unreliable.
---

# mx-space Remote DB Access

Use this skill when the task requires inspecting or updating the remote `mx-space` MongoDB that is reachable only through the application host and container runtime, not through a stable host-level Mongo endpoint.

## Scope

- Target topology: `local -> ssh -> swarm host -> docker exec -> mongosh`
- Primary use cases:
  - inspect databases and collections
  - sample documents from `posts`, `pages`, `notes`, `topics`, or `options`
  - analyze note/topic assignments
  - perform guarded bulk updates after explicit user approval
- Do not assume direct `mongosh` access from the local machine is available.

## Required Parameters

Prepare the following values from the user request or the active session context:

| Variable | Meaning |
|---|---|
| `SSH_USER` | remote login user, typically `root` |
| `SSH_HOST` | remote host address |
| `SSH_PORT` | remote SSH port |
| `MONGO_CONTAINER` | running Mongo container name |
| `MONGO_USER` | Mongo username |
| `MONGO_PASSWORD` | Mongo password; do not persist it to files unless the user explicitly asks |
| `MONGO_DB` | target database, typically `mx-space` |

## Standard Access Pattern

```text
[Local shell]
      |
      v
ssh -p $SSH_PORT $SSH_USER@$SSH_HOST
      |
      v
docker exec $MONGO_CONTAINER mongosh
      |
      v
mongodb://$MONGO_USER:$MONGO_PASSWORD@127.0.0.1:27017/$MONGO_DB?authSource=admin
```

## Baseline Connectivity Checks

Run these in order.

1. Verify SSH reachability.
2. Verify container existence.
3. Run `mongosh` inside the container.
4. Confirm database access with `db.adminCommand({ ping: 1 })`.

Minimal examples:

```bash
ssh -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" "docker ps --format '{{.Names}}' | grep -F '$MONGO_CONTAINER'"
```

```bash
ssh -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" \
  "docker exec '$MONGO_CONTAINER' mongosh 'mongodb://$MONGO_USER:$MONGO_PASSWORD@127.0.0.1:27017/$MONGO_DB?authSource=admin' --quiet --eval 'db.adminCommand({ ping: 1 })'"
```

## Preferred Query Strategy

Use `--eval` only for simple expressions that do not contain Mongo operators beginning with `$`.

Use stdin scripts for any query that contains:

- `$match`
- `$group`
- `$lookup`
- `$project`
- `$sort`
- `$exists`
- `$in`
- any aggregation pipeline

Reason:

- Shell quoting on the remote side can swallow `$...` operators before `mongosh` receives them.

## Safe Read Patterns

### Simple collection counts

```bash
ssh -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" \
  "docker exec '$MONGO_CONTAINER' mongosh 'mongodb://$MONGO_USER:$MONGO_PASSWORD@127.0.0.1:27017/$MONGO_DB?authSource=admin' --quiet --eval 'printjson(db.getCollectionNames().sort().map(name => ({ name, count: db.getCollection(name).countDocuments() })))'"
```

### Complex query via stdin

```bash
ssh -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" \
  "docker exec -i '$MONGO_CONTAINER' mongosh 'mongodb://$MONGO_USER:$MONGO_PASSWORD@127.0.0.1:27017/$MONGO_DB?authSource=admin' --quiet" <<'EOF'
const rows = db.notes.find(
  { topicId: null },
  { _id: 0, nid: 1, title: 1, created: 1 }
).toArray();

printjson(rows);
quit();
EOF
```

## Topic Analysis Workflow

Use the following sequence when the user asks about `notes` and `topics`.

```text
[1] Read topics
      -> names, ids, descriptions, slugs

[2] Inspect notes schema
      -> confirm whether relation field is topicId or another field

[3] Count assigned vs unassigned notes
      -> topicId != null vs topicId == null

[4] Sample representative notes per topic
      -> titles, created, modified

[5] For ambiguous notes
      -> read short excerpts first
      -> read longer excerpts only for a small filtered subset
```

## Guarded Update Workflow

Never write immediately after classification. Use this sequence.

```text
[1] Build explicit assignment list
      -> topic name
      -> topic id
      -> target nid list

[2] Precheck
      -> all target nids exist
      -> all target notes still have topicId = null
      -> no already-classified note is about to be overwritten

[3] Update
      -> updateMany({ topicId: null, nid: { $in: ... } }, { $set: { topicId: ObjectId(...) } })

[4] Verify
      -> remaining unassigned count
      -> per-topic counts
      -> sampled nid-to-topic spot checks
```

## Update Rules

- Perform writes only after explicit user approval.
- Filter writes with both `topicId: null` and an explicit `nid` set.
- Never overwrite an existing `topicId` unless the user explicitly asks for reassignment.
- Prefer batched updates grouped by target topic.
- After any successful write, run read-only verification immediately.

## Output Guidelines

Prefer structured summaries.

### Use a table for:

- collection counts
- topic inventories
- proposed note assignments
- post-update verification counts

### Use an ASCII flow for:

- explaining access topology
- showing precheck -> update -> verify sequence

## Example Verification Queries

### Remaining unassigned notes

```bash
ssh -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" \
  "docker exec '$MONGO_CONTAINER' mongosh 'mongodb://$MONGO_USER:$MONGO_PASSWORD@127.0.0.1:27017/$MONGO_DB?authSource=admin' --quiet --eval \"printjson({ withoutTopic: db.notes.countDocuments({ topicId: null }), remaining: db.notes.find({ topicId: null }, { _id: 0, nid: 1, title: 1 }).sort({ nid: 1 }).toArray() })\""
```

### Sampled nid-to-topic check via stdin

```bash
ssh -p "$SSH_PORT" "$SSH_USER@$SSH_HOST" \
  "docker exec -i '$MONGO_CONTAINER' mongosh 'mongodb://$MONGO_USER:$MONGO_PASSWORD@127.0.0.1:27017/$MONGO_DB?authSource=admin' --quiet" <<'EOF'
const sampleNids = [12, 11, 9];
const topicMap = new Map(db.topics.find({}, { _id: 1, name: 1 }).toArray().map((t) => [String(t._id), t.name]));
const rows = db.notes.find({ nid: { $in: sampleNids } }, { _id: 0, nid: 1, title: 1, topicId: 1 })
  .toArray()
  .sort((a, b) => a.nid - b.nid)
  .map((n) => ({ nid: n.nid, title: n.title, topic: topicMap.get(String(n.topicId)) || null }));

printjson(rows);
quit();
EOF
```

## Operational Notes

- If host-level forwarding to the Mongo service fails, do not spend time forcing local tunnel access unless the user explicitly needs it.
- Prefer container-local `127.0.0.1:27017` access through `docker exec`; this was the reliable path in this deployment pattern.
- Keep excerpts short by default. Read more content only when classification confidence is inadequate.
- Do not store credentials into the repository. Use placeholders or session-provided values.
