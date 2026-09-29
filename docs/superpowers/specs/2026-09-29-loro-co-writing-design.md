# Loro co-writing for `mxs author` + `co-write-blog-post` skill

Date: 2026-09-29
Status: approved design, pending implementation plan

## Intent

Start a blog post from a blank page, write it in the browser, and have an
agent edit the same article on request (diagrams, rewrites, images) while the
human keeps typing. Both sides see each other's changes live, the article is
always a local LiteXML file, and the full edit history survives across
sessions so any earlier state can be restored.

Stated by the user:

- A new, separate skill for writing from a blank article.
- Reuse the existing `mxs author` web editor; content syncs to a local file.
- The agent edits the local file directly when asked; the web must reflect it.
- Real CRDT collaboration, built on Loro, with a full Lexical ↔ LoroTree binding.
- Persist Loro binary history locally; on re-entry, browse and restore history.
  No branching in v1.

Success criteria:

- One browser tab stays open from blank page to publish.
- Human edits reach the file within ~300ms without ⌘S; the agent always
  reads current text.
- Agent edits appear in the editor without manual Accept, and never revert
  text the human typed concurrently.
- Reopening a draft restores its history; any past version can be restored
  as a new change.

## Current state (baseline)

- `mx-core/packages/cli/src/cli/author/`: node HTTP server, file watcher,
  SSE `revision` events carrying Lexical JSON.
- `mx-core/apps/admin/src/author/`: `RevisionSyncPlugin` + `merge.ts` do a
  block-level three-way merge in the browser; every agent change becomes a
  diff note needing Accept. Browser writes the file only on ⌘S.
- haklex (`~/git/innei-repo/haklex`), Lexical 0.49; mx-core pins
  `@haklex/*` at `0.43.2`. `rich-headless` gives the node registry for Node,
  `rich-litexml` converts SerializedNode ↔ XML, `rich-diff-core` computes
  structural + character diffs on serialized trees.
- No usable Loro ↔ Lexical binding exists (`@datalayer/lexical-loro` is a
  demo-grade app bundle with pinned React, yjs and a Python server).

## Architecture

| Unit | Location | Responsibility |
| ---- | -------- | -------------- |
| `@haklex/rich-collab-loro` | `haklex/packages/rich-collab-loro` | `LoroBinding`: bidirectional Lexical editor ↔ `LoroDoc`. Pure TS, no React; runs in browser and headless Node. Thin `LoroCollabPlugin` React wrapper. |
| `mxs author` server | `mx-core/packages/cli/src/cli/author/` | Owns the authoritative `LoroDoc` plus a headless Lexical editor (rich-headless nodes) bound via `LoroBinding`. Bridges file ↔ doc, relays updates, persists history. |
| Author frontend | `mx-core/apps/admin/src/author/` | Replaces `RevisionSyncPlugin` + `merge.ts` with `LoroCollabPlugin`; adds history sidebar. `--base` diff notes remain as an independent feature. |
| `co-write-blog-post` skill | `SKILL/skills/writing/co-write-blog-post/` | Agent procedure for blank-page co-writing on top of the above. |

## Data model

- Every Lexical node ↔ one `LoroTree` node; tree parent/child order mirrors
  Lexical children.
- Node props = `exportJSON()` minus `children` / `type` / `version`, stored in
  the tree node's meta `LoroMap`, one last-writer-wins field per prop. `type`
  is stored once at creation.
- `TextNode.text` is a `LoroText` (character-level merge); `format`, `style`,
  `mode`, `detail` are plain fields.
- DecoratorNodes (excalidraw, mermaid, img, dynamic, …) are handled
  generically: LWW per prop. A concurrent edit to the same Excalidraw scene
  resolves to the last writer.
- Any node with `exportJSON` / `importJSON` is supported with no per-node code.

Hard spots the binding must handle:

- Lexical text normalization (adjacent same-format TextNodes merge, splits on
  format change) maps to Loro node delete + `LoroText` edits.
- Selection preservation on remote updates: untouched nodes keep keys; offsets
  inside changed text map through Loro `Cursor`.
- Remote updates are applied inside `editor.update(…, { tag: 'collab' })`; the
  binding ignores `collab`-tagged updates on the way out to prevent echo.

Out of scope for v1: fine-grained merge inside nested-doc (its inner state is
one opaque LWW prop), presence / cursors (`EphemeralStore`), multiple browser
tabs, branching.

## Sync flows

```
Browser (Lexical + Loro replica)   mxs author server (headless Lexical + LoroDoc)   article.xml
   ── POST /api/update (Loro bytes, 100ms batch) ──▶
   ◀── SSE `update` (Loro bytes) ──────────────────   ── 300ms debounce write ──▶
                                                      ◀── watcher: agent write ──
```

1. **Startup.**
   - `<file>.loro` exists and its recorded file hash equals the current file
     hash → load snapshot (history kept).
   - Snapshot exists, hash differs → load snapshot, then apply the file as an
     agent edit (flow 4) against the snapshot's last-written version.
   - No snapshot → parse LiteXML, initialize a fresh doc, commit
     `session <iso time>`.
   - Browser: `GET /api/snapshot` → import → binding builds Lexical from Loro.
2. **Human edit.** Lexical update → binding writes local Loro ops, commit
   message `human` → local updates batched 100ms → `POST /api/update`. Server
   imports; headless editor follows via binding; schedules flow 5.
3. **Server → browser.** Server-originated updates go out as SSE `update`
   (base64). Browser imports; binding applies to Lexical with tag `collab`.
4. **Agent edits the file.**
   - Watcher fires; if content hash equals the server's last self-write, ignore.
   - Base = the version the server last wrote (the content the agent
     overwrote). The server keeps a ring buffer `fileHash → frontiers` of
     recent self-writes.
   - `fork = doc.forkAt(baseFrontiers)`; bind a headless editor to the fork;
     compute `rich-diff-core` diff between the base serialization and the
     parsed agent file; apply it as minimal Lexical mutations (keep node
     identity for unchanged nodes, text diff within TextNodes); commit
     `agent: +a ~m -d blocks`.
   - Import the fork's updates into the main doc. Concurrent human edits are
     preserved by CRDT merge; text the agent did not change is never reverted
     even if it is stale in the agent's copy.
   - stdout: `agent edit merged: +a ~m -d blocks`.
   - Contract for agents: read-modify-write in one step (Claude Code `Edit`,
     Codex `apply_patch`); never hold a stale copy and `Write` it later.
5. **Doc → file.** Any doc change → 300ms debounce → serialize LiteXML
   (envelope meta byte-stable) → write `<file>`, record `hash → frontiers`,
   rewrite `<file>.diff` (current body vs body at process start, unchanged
   contract). ⌘S = flush now.

## History

- `doc.setRecordTimestamp(true)`; commit messages `session <time>`, `human`,
  `agent: …`, `restore <target>`.
- `<file>.loro` = full snapshot including oplog; written every 5s and on exit.
  A crash loses nothing: the file is written every 300ms and startup replays
  it via flow 1.
- Browser sidebar timeline grouped by message kind, newest first, human
  changes coalesced by idle gaps. Selecting an entry shows a read-only preview
  (`doc.fork()` + `checkout(frontiers)`, live editing unaffected).
- **Restore to here**: compute the state at those frontiers and apply it on
  top as a new change (revert semantics); prior history remains restorable.
- Not in v1: branches, agent-facing `mxs author history|restore` CLI.

## Error handling

| Condition | Behavior |
| --------- | -------- |
| Agent writes unparseable XML or an unknown node type | stdout `agent edit rejected: <reason>`; doc untouched; **file writes pause** so the agent can fix its copy in place; browser header shows 文件无效，暂停写盘; writes resume once the file parses. |
| Browser disconnects | Keeps editing locally; on reconnect both sides exchange `oplogVersion()` and export missing updates. |
| No browser connected | Server keeps merging agent edits; the next page load fetches the snapshot. |
| Snapshot corrupt | stdout warning, move it to `<file>.loro.bak`, start fresh from the file. |

## Testing

| Layer | Test | Proves |
| ----- | ---- | ------ |
| haklex binding (vitest, headless, no network) | Two editors + two docs, seeded random concurrent ops, sync, `exportJSON()` equal | Convergence |
| | Every rich-headless builtin + ext node: Lexical → Loro → Lexical round-trip equal | Generic mapping covers haklex |
| | Adjacent text merge / split; `Cursor` selection mapping | Hard spots |
| mx-core server | Human edits block A after base, agent file changes B → both present; agent file carrying stale A → A not reverted | Flow 4 three-way |
| | Bad XML → rejected + writes paused → recovered after fix; self-write ignored; snapshot resume and hash mismatch | Error handling |
| | History persists across restart; restore yields target content with history intact | History |
| Manual E2E | `mxs author` open; human types while agent `Edit`s the same file | Real experience |

## Delivery order

1. **haklex**: `rich-collab-loro` + tests; publish via `bumpp -r`.
2. **mx-core**: server + frontend rewrite, history sidebar, bump `@haklex/*`,
   delete `merge.ts` / `RevisionSyncPlugin.tsx` and their tests, update the
   bundled `commands-author` skill doc. Develop against local haklex via
   `pnpm link`.
3. **SKILL repo**: `co-write-blog-post` skill; update the agent loop in
   `session-to-skill-and-blog/references/publish-flow.md`.

## `co-write-blog-post` skill

Location `skills/writing/co-write-blog-post/`, README row in the Writing
table, flat symlinks in `.agent/skills/` and `.claude/skills/`. Written in
English. Reuses `session-to-skill-and-blog` references and scripts through
the same `$S` search loop; copies nothing.

Workflow:

1. **Intake** (one interactive question call, Chinese): narrator persona
   (`agent` / `site-owner` / `neutral` / `defer`, same mapping as
   session-to-skill-and-blog) and article language. Topic comes from the
   trigger message.
2. **Envelope**: `<drafts>/<slug>/article.xml` from
   `references/envelope.template.xml`, title and slug filled, empty
   `<content>`. `<drafts>` = `blog_drafts_dir` in
   `~/.config/innei-skills/config.json`, default `~/blog-drafts`. Existing
   slug → resume, do not recreate.
3. **Open**: `mxs author <file>` in the background, give the URL, stop.
4. **Loop**, one request per turn: read the current file → locate target by
   quoting heading / paragraph text → load only the needed reference
   (diagram → `visuals.md`, prose → `writing-style.md`, image →
   `mxs file upload` + `image-meta.mjs`) → apply with one `Edit` → check
   stdout for `agent edit merged` / `agent edit rejected` (fix and retry on
   rejected) → stop.
5. **Finish** on "写完了": no-ai-slop detect sweep, report candidates in chat
   without rewriting; the human edits in the browser; then follow
   `publish-flow.md`.

Failure boundaries:

- Edit only blocks the human asked about; never reformat or `Write` the whole
  file.
- Never write the human's prose unprompted; suggestions go to chat.
- Re-read before every edit; a long read-to-write gap is a stale base.
- Requires `mxs` with Loro-based `mxs author`; check `mxs author --help`
  before starting and stop with an upgrade instruction if missing.
